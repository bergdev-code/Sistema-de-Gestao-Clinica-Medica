import datetime as dt
import hashlib
import hmac
import importlib
import logging
import os
import re
import secrets
import unicodedata
from decimal import Decimal
from functools import wraps
from urllib.parse import urlencode

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, models, transaction
from django.db.models import Count, ProtectedError, Q, Sum
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

# O login com Google é opcional: se as bibliotecas não estiverem instaladas
# (pip install requests google-auth), só esse recurso fica indisponível e o
# restante do sistema continua funcionando normalmente.
try:
    import requests
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token
except ImportError:
    requests = google_requests = id_token = None

from func_django.models import (
    Agendamento,
    Alergia,
    Especialidade,
    GoogleIdentity,
    HorarioMedico,
    Medico,
    MedicoEspecialidade,
    Pagamento,
    Perfil,
    Prontuario,
    StatusAgendamento,
    StatusPagamento,
    Usuario,
    func_django,
    ChamadoSuporte,
    RespostaSuporte,
)


# ==================================================
# VALIDADORES (os mesmos do terminal, com reserva)
# ==================================================
def _validar_nome_padrao(texto):
    return bool(re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ ]{3,}", (texto or "").strip()))


def _validar_email_padrao(texto):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", (texto or "").strip()))


def _validar_senha_padrao(texto):
    texto = texto or ""
    return len(texto) >= 8 and any(c.isalpha() for c in texto) and any(c.isdigit() for c in texto)


def _validador(nome, padrao):
    """Usa a função de sistema_clinica.funcionalidades.regex (a mesma do terminal).
    Se esse módulo não estiver no projeto, usa uma versão equivalente simples,
    em vez de derrubar o site inteiro com um ImportError."""
    try:
        modulo = importlib.import_module("sistema_clinica.funcionalidades.regex")
    except ImportError:
        return padrao
    return getattr(modulo, nome, padrao)


validar_nome = _validador("validar_nome", _validar_nome_padrao)
validar_email = _validador("validar_email", _validar_email_padrao)
validar_senha = _validador("validar_senha", _validar_senha_padrao)


# ==================================================
# AUDITORIA (quem fez o quê) — vai para o logger "clinica.auditoria"
# ==================================================
auditoria = logging.getLogger("clinica.auditoria")


def registrar_auditoria(request, acao, detalhe=""):
    """Registra ações sensíveis. Nunca coloque senhas nem texto clínico em 'detalhe':
    só identificadores (CPF, número do registro...). Para gravar em arquivo, configure
    o logger "clinica.auditoria" em LOGGING no settings.py."""
    sessao = getattr(request, "session", None) or {}
    auditoria.info(
        "acao=%s usuario=%s perfil=%s ip=%s %s",
        acao, sessao.get("username", "-"), sessao.get("perfil", "-"),
        request.META.get("REMOTE_ADDR", "-"), detalhe,
    )


# ==================================================
# UTILITÁRIOS DE DADOS
# ==================================================
def somente_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def cpf_valido(cpf):
    """CPF com 11 números. Os dígitos verificadores só são conferidos se
    CLINICA_VALIDAR_DIGITO_CPF = True no settings.py (deixe desligado enquanto
    estiver testando com CPFs inventados)."""
    if not re.fullmatch(r"\d{11}", cpf or ""):
        return False
    if not getattr(settings, "CLINICA_VALIDAR_DIGITO_CPF", False):
        return True
    if len(set(cpf)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d) * peso for d, peso in zip(cpf[:tamanho], range(tamanho + 1, 1, -1)))
        if (soma * 10) % 11 % 10 != int(cpf[tamanho]):
            return False
    return True


def hoje_local():
    return timezone.localdate() if settings.USE_TZ else dt.date.today()


POR_PAGINA = 25


def paginar(request, itens, por_pagina=POR_PAGINA):
    """Divide a listagem em páginas (?pagina=2). 'itens' precisa estar ordenado."""
    return Paginator(itens, por_pagina).get_page(request.GET.get("pagina"))


ITERACOES = 600000  # igual ao verificar_usuario.py


def gerar_hash(senha, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt_hex), ITERACOES).hex()


CAMPOS_USUARIO = ["username", "email", "id_perfil", "medico"]
TEM_CAMPO_PACIENTE = any(f.name == "paciente" for f in Usuario._meta.get_fields())


class ContatoMixin:
    """Aceita CPF e telefone digitados com máscara (123.456.789-09, (81) 99999-9999):
    o que vai para o banco são só os números, igual ao cadastro público."""

    def clean_cpf(self):
        cpf = somente_digitos(self.cleaned_data.get("cpf"))
        if cpf and not cpf_valido(cpf):
            raise ValidationError("CPF inválido. Informe os 11 números.")
        return cpf

    def clean_telefone(self):
        telefone = somente_digitos(self.cleaned_data.get("telefone"))
        if telefone and not re.fullmatch(r"\d{10,11}", telefone):
            raise ValidationError("Informe o telefone com DDD (10 ou 11 números).")
        return telefone or None


class UsuarioForm(ContatoMixin, forms.ModelForm):
    """Mesmas regras do cadastro_usuarios.py do terminal. Com o perfil Paciente,
    cadastra também o paciente (CPF, nome...) na mesma tela."""

    senha = forms.CharField(widget=forms.PasswordInput, min_length=8, label="Senha (mínimo 8 caracteres)")
    cpf = forms.CharField(required=False, max_length=14, label="CPF do paciente")
    nome = forms.CharField(required=False, max_length=150, label="Nome do paciente")
    telefone = forms.CharField(required=False, max_length=15, label="Telefone do paciente")
    data_nascimento = forms.DateField(
        required=False, label="Data de nascimento do paciente",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    class Meta:
        model = Usuario
        fields = CAMPOS_USUARIO
        labels = {"username": "Nome de usuário", "id_perfil": "Perfil",
                  "medico": "Médico (obrigatório para o perfil Médico)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._novo_paciente = None
        # só médicos ativos que ainda não têm usuário
        self.fields["medico"].queryset = (
            Medico.objects.filter(ativo=True).order_by("nome")
            .exclude(crm__in=Usuario.objects.filter(medico__isnull=False).values_list("medico_id", flat=True))
        )
        for nome_campo in ("id_perfil", "medico"):
            self.fields[nome_campo].label_from_instance = rotulo
        # a tela só mostra os campos que fazem sentido para o perfil escolhido
        self.fields["medico"].widget.attrs["grupo"] = "medic"
        for nome_campo in ("cpf", "nome", "telefone", "data_nascimento"):
            self.fields[nome_campo].widget.attrs["grupo"] = "pacien"

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not validar_nome(username):
            raise ValidationError("Use apenas letras e espaços (mínimo de 3 caracteres).")
        if Usuario.objects.filter(username__iexact=username).exists():
            raise ValidationError("Nome de usuário já cadastrado.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not validar_email(email):
            raise ValidationError("E-mail inválido.")
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError("E-mail já cadastrado.")
        return email

    def clean(self):
        dados = super().clean()
        perfil = dados.get("id_perfil")
        nome_perfil = chave_perfil(perfil.nome_perfil) if perfil else ""

        if nome_perfil == _n(PERFIL_MEDICO):
            if not dados.get("medico"):
                self.add_error("medico", "Selecione o médico deste usuário (só aparecem médicos ativos sem usuário).")
        else:
            dados["medico"] = None

        if TEM_CAMPO_PACIENTE and nome_perfil == _n(PERFIL_PACIENTE):
            cpf = (dados.get("cpf") or "").strip()
            nome_pac = (dados.get("nome") or "").strip()
            if not (cpf and nome_pac):
                self.add_error("cpf", "Informe o CPF e o nome do paciente.")
            elif func_django.objects.filter(cpf=cpf).exists():
                self.add_error("cpf", "Já existe um paciente cadastrado com esse CPF.")
            else:
                self._novo_paciente = {
                    "cpf": cpf, "nome": nome_pac,
                    "telefone": (dados.get("telefone") or "").strip() or None,
                    "data_nascimento": dados.get("data_nascimento"),
                }
        return dados

    def save(self, commit=True):
        with transaction.atomic():
            usuario = super().save(commit=False)
            if self._novo_paciente:
                usuario.paciente = func_django.objects.create(**self._novo_paciente)
            usuario.salt = secrets.token_hex(16)  # igual a secrets.token_bytes(16).hex() do terminal
            usuario.senha_hash = gerar_hash(self.cleaned_data["senha"], usuario.salt)
            if commit:
                usuario.save()
        return usuario


class PacienteForm(ContatoMixin, forms.ModelForm):
    """Cadastro de paciente. Se usuário, e-mail e senha forem preenchidos,
    cria junto o acesso (login) do paciente, sempre com o perfil Paciente."""

    cpf = forms.CharField(max_length=14, label="CPF")
    telefone = forms.CharField(max_length=15, required=False, label="Telefone")
    username = forms.CharField(
        required=False, max_length=10, label="Nome de usuário (login)",
        help_text="Opcional: preencha usuário, e-mail e senha para criar o acesso do paciente ao sistema.",
    )
    email = forms.EmailField(required=False, max_length=50, label="E-mail de acesso")
    senha = forms.CharField(required=False, widget=forms.PasswordInput, label="Senha de acesso (mínimo 8 caracteres)")

    class Meta:
        model = func_django
        fields = ["cpf", "nome", "telefone", "data_nascimento"]
        widgets = {"data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        labels = {"cpf": "CPF", "nome": "Nome", "telefone": "Telefone",
                  "data_nascimento": "Data de nascimento"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._perfil = None

    def clean_cpf(self):
        cpf = super().clean_cpf()
        if not cpf:
            raise ValidationError("CPF inválido. Informe os 11 números.")
        if func_django.objects.filter(cpf=cpf).exists():
            raise ValidationError("Já existe um paciente cadastrado com esse CPF.")
        return cpf

    def clean(self):
        dados = super().clean()
        username = (dados.get("username") or "").strip()
        email = (dados.get("email") or "").strip().lower()
        senha = dados.get("senha") or ""
        if not (username or email or senha):
            return dados

        if not (username and email and senha):
            self.add_error(None, "Para criar o acesso, preencha usuário, e-mail e senha (ou deixe os três em branco).")
            return dados
        if not validar_nome(username):
            self.add_error("username", "Use apenas letras e espaços (mínimo de 3 caracteres).")
        elif Usuario.objects.filter(username__iexact=username).exists():
            self.add_error("username", "Nome de usuário já cadastrado.")
        if not validar_email(email):
            self.add_error("email", "E-mail inválido.")
        elif Usuario.objects.filter(email__iexact=email).exists():
            self.add_error("email", "E-mail já cadastrado.")
        if len(senha) < 8:
            self.add_error("senha", "A senha deve ter no mínimo 8 caracteres.")

        self._perfil = obter_perfil_paciente()
        if self._perfil is None:
            self.add_error(None, "O perfil Paciente não existe na tabela de perfis. Peça ao administrador para cadastrá-lo.")
        dados["username"], dados["email"] = username, email
        return dados

    def save(self, commit=True):
        with transaction.atomic():
            paciente = super().save(commit=commit)
            dados = self.cleaned_data
            if self._perfil is not None and dados.get("username") and dados.get("email") and dados.get("senha"):
                salt = secrets.token_hex(16)
                Usuario.objects.create(
                    username=dados["username"], email=dados["email"],
                    salt=salt, senha_hash=gerar_hash(dados["senha"], salt),
                    id_perfil=self._perfil, paciente=paciente,
                )
        return paciente


class PacienteEdicaoForm(ContatoMixin, forms.ModelForm):
    """Edição dos dados do paciente. O CPF é a chave do cadastro e não é alterado."""

    telefone = forms.CharField(max_length=15, required=False, label="Telefone")

    class Meta:
        model = func_django
        fields = ["nome", "telefone", "data_nascimento"]
        widgets = {"data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        labels = {"nome": "Nome", "data_nascimento": "Data de nascimento"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome"].required = True

    def clean_data_nascimento(self):
        data = self.cleaned_data.get("data_nascimento")
        if data and data >= hoje_local():
            raise ValidationError("A data de nascimento deve ser anterior à data atual.")
        return data


class ProntuarioForm(forms.ModelForm):
    """Registro clínico. O médico só registra para os SEUS pacientes e sempre em
    seu próprio nome: o campo 'médico' é fixado pelo sistema e não vem da tela."""

    precisa_request = True  # o 'novo'/'editar' entregam o request a este formulário

    class Meta:
        model = Prontuario
        fields = ["paciente", "medico", "agendamento_id", "anamnese", "diagnostico", "prescricao"]
        labels = {"agendamento_id": "Nº da consulta (opcional)", "anamnese": "Anamnese",
                  "diagnostico": "Diagnóstico", "prescricao": "Prescrição"}
        widgets = {campo: forms.Textarea(attrs={"rows": 4}) for campo in ("anamnese", "diagnostico", "prescricao")}

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.fields["paciente"].label_from_instance = rotulo
        self.fields["medico"].label_from_instance = rotulo
        perfil = chave_perfil(request.session.get("perfil")) if request else ""
        editando = bool(self.instance and self.instance.pk)

        if perfil == _n(PERFIL_MEDICO):
            crm = request.session.get("crm") or ""
            self.fields["paciente"].queryset = pacientes_visiveis(request).order_by("nome")
            self.fields["medico"].queryset = Medico.objects.filter(pk=crm)
            self.fields["medico"].disabled = True
            self.initial["medico"] = crm  # campo desabilitado usa o valor inicial, nunca o enviado

        if editando:  # em um prontuário já criado, paciente e médico não mudam
            self.fields["paciente"].queryset = func_django.objects.filter(pk=self.instance.paciente_id)
            self.fields["medico"].queryset = Medico.objects.filter(pk=self.instance.medico_id)
            self.fields["paciente"].disabled = True
            self.fields["medico"].disabled = True

    def clean(self):
        dados = super().clean()
        paciente, medico = dados.get("paciente"), dados.get("medico")
        ag_id = dados.get("agendamento_id")
        if ag_id and paciente and medico:
            if not Agendamento.objects.filter(pk=ag_id, paciente=paciente, medico=medico).exists():
                self.add_error("agendamento_id", "Essa consulta não existe ou não é deste paciente com este médico.")
        return dados


class ChamadoSuporteForm(forms.ModelForm):

    class Meta:
        model = ChamadoSuporte
        fields = ["assunto", "descricao"]

        labels = {
            "assunto": "Assunto",
            "descricao": "Descreva sua solicitação",
        }

        widgets = {
            "assunto": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex.: Problema ao solicitar consulta",
                "maxlength": 150,
            }),
            "descricao": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Explique detalhadamente o que aconteceu...",
                "rows": 5,
            }),
        }

    def clean_assunto(self):
        assunto = self.cleaned_data["assunto"].strip()

        if not assunto:
            raise ValidationError("Informe o assunto do chamado.")

        return assunto

    def clean_descricao(self):
        descricao = self.cleaned_data["descricao"].strip()

        if not descricao:
            raise ValidationError("Informe a descrição do chamado.")

        return descricao


# Cada recurso vira lista + cadastro + exclusão usando os mesmos 3 templates.
# colunas: (campo, rótulo) | busca: campos da pesquisa | criar: libera "Cadastrar"
# esconder: campos que nunca aparecem no formulário | ordem: ordenação da listagem
RECURSOS = {
    "pacientes": {
        "model": func_django, "titulo": "Pacientes", "form": PacienteForm, "escopo": {"medico": "agendamento__medico", "paciente": "cpf"},
        "colunas": [("cpf", "CPF"), ("nome", "Nome"), ("telefone", "Telefone"),
                    ("data_nascimento", "Nascimento")],
        "busca": ["nome", "cpf"],
        "ordem": ["nome", "cpf"],
    },
    "medicos": {
        "model": Medico, "titulo": "Médicos",
        "colunas": [("crm", "CRM"), ("nome", "Nome"), ("telefone", "Telefone"), ("ativo", "Ativo")],
        "busca": ["nome", "crm"],
        "ordem": ["nome"],
    },
    "especialidades": {
        "model": Especialidade, "titulo": "Especialidades",
        "colunas": [("nome", "Nome")],
        "busca": ["nome"],
        "ordem": ["nome"],
    },
    "vinculos": {
        "model": MedicoEspecialidade, "titulo": "Especialidades dos médicos",
        "colunas": [("medico", "Médico"), ("especialidade", "Especialidade")],
        "busca": ["medico__nome", "especialidade__nome"],
        "ordem": ["medico__nome", "especialidade__nome"],
    },
    "horarios": {
        "model": HorarioMedico, "titulo": "Horários dos médicos",
        "colunas": [("medico", "Médico"), ("dia_semana", "Dia"), ("hora_inicio", "Início"), ("hora_fim", "Fim")],
        "busca": ["medico__nome", "dia_semana"],
        "ordem": ["medico__nome", "hora_inicio"],
    },
    "consultas": {
        "model": Agendamento, "titulo": "Consultas", "escopo": {"medico": "medico", "paciente": "paciente"},
        "colunas": [("paciente", "Paciente"), ("tipo", "Tipo"), ("medico", "Médico"), ("data_hora", "Data e hora"), ("status", "Status")],
        "busca": ["paciente__nome", "medico__nome"],
        "ordem": ["-data_hora", "-id_agendamento"],
    },
    "prontuarios": {
        "model": Prontuario, "titulo": "Prontuários", "escopo": {"medico": "medico", "paciente": "paciente"},
        "colunas": [("paciente", "Paciente"), ("medico", "Médico"), ("diagnostico", "Diagnóstico")],
        "busca": ["paciente__nome", "medico__nome"],
        "form": ProntuarioForm,
        "ordem": ["-id_prontuario"],
    },
    "pagamentos": {
        "model": Pagamento, "titulo": "Financeiro",
        "colunas": [("agendamento", "Consulta"), ("descricao", "Descrição"), ("valor", "Valor"),
                    ("forma_pagamento", "Forma"), ("status_pagamento", "Status"), ("data_pagamento", "Data")],
        "busca": ["descricao"],
        "escopo": {"paciente": "agendamento__paciente"},
        "criar": False,
        "ordem": ["-data_pagamento", "-id_pagamento"],
    },
    "usuarios": {
        "model": Usuario, "titulo": "Usuários",
        "colunas": [("username", "Usuário"), ("email", "E-mail"), ("id_perfil", "Perfil"), ("medico", "Médico")],
        "busca": ["username", "email"],
        "form": UsuarioForm,
        "esconder": ["senha_hash", "salt"],
        "ordem": ["username"],
    },
}


# ==================================================
# PERMISSÕES POR PERFIL
# ==================================================
# As chaves devem ser IGUAIS aos valores de Perfil.nome_perfil no banco
# (com acento e maiúsculas). "*" = todos os recursos; a regra de um recurso
# específico tem prioridade sobre o "*".
# Ações: ver, criar, editar, excluir, aceitar (consultas), cancelar (consultas e
# pagamentos), alergia (gerir alergias do paciente), solicitar (consulta) e
# pagar. Chave "pagamentos" = tela Financeiro.
def _n(perfil):
    texto = unicodedata.normalize("NFKD", (perfil or "").strip().casefold())
    return "".join(c for c in texto if not unicodedata.combining(c))


PERFIL_ROOT = "ADMIN GERAL"
PERFIL_RECEPCIONISTA = "Recepcionista"
PERFIL_MEDICO = "Médico"
PERFIL_PACIENTE = "Paciente"

_ACOES_ADMIN = {"ver", "criar", "editar", "excluir", "aceitar", "cancelar", "alergia"}
_PERMISSOES_ADMIN = {
    "*": _ACOES_ADMIN,
    # Prontuário é registro clínico: quem escreve é o médico. O administrador só
    # consulta (e pode excluir); não cria nem altera texto clínico de terceiros.
    "prontuarios": {"ver", "excluir"},
}

PERMISSOES = {
    "Administrador": _PERMISSOES_ADMIN,
    PERFIL_ROOT: _PERMISSOES_ADMIN,  # usuário root
    PERFIL_RECEPCIONISTA: {
        "pacientes": {"ver", "criar", "editar", "excluir", "alergia"},
        "consultas": {"ver", "criar", "excluir", "aceitar", "cancelar"},
        "pagamentos": {"ver", "criar", "excluir", "cancelar"},
        "medicos": {"ver"},
        "especialidades": {"ver"},
        "horarios": {"ver"},
        "vinculos": {"ver"},
        # sem "prontuarios": a recepção não acessa conteúdo clínico
    },
    PERFIL_MEDICO: {
        "pacientes": {"ver", "alergia"},
        "consultas": {"ver"},
        "prontuarios": {"ver", "criar", "editar"},
    },
    # paciente só consulta os próprios dados (o filtro está em aplicar_escopo)
    PERFIL_PACIENTE: {
        "consultas": {"ver", "solicitar", "cancelar"},
        "prontuarios": {"ver"},
        "pagamentos": {"ver", "pagar"},
    },
}


PERMISSOES = {_n(k): v for k, v in PERMISSOES.items()}


# Se o nome do perfil no banco for parecido (ex.: "Recepção", "Admin"), usa a regra certa
PREFIXOS = {"admin": "administrador", "recep": "recepcionista", "medic": "medico", "pacien": "paciente"}


def chave_perfil(perfil):
    n = _n(perfil)
    if n in PERMISSOES:
        return n
    if n.startswith("administrativ"):  # "Administrativo" NÃO é "Administrador"
        return n
    for prefixo, chave in PREFIXOS.items():
        if n.startswith(prefixo):
            return chave
    return n


def acoes_do_perfil(perfil, recurso):
    perms = PERMISSOES.get(chave_perfil(perfil), {})
    if recurso in perms:
        return perms[recurso]
    return perms.get("*", set())


def exigir(request, recurso, acao):
    if acao not in acoes_do_perfil(request.session.get("perfil"), recurso):
        raise PermissionDenied


def cpf_da_sessao(request):
    """CPF do paciente ligado ao usuário. Se a sessão ainda não o tem (login feito
    antes do vínculo), busca no banco, sem precisar sair e entrar de novo."""
    cpf = request.session.get("cpf")
    if not cpf and request.session.get("username"):
        cpf = (Usuario.objects.filter(username=request.session["username"])
               .values_list("paciente_id", flat=True).first()) or ""
        if request.session.get("cpf") != cpf:  # só grava a sessão se algo mudou
            request.session["cpf"] = cpf
    return cpf


def aplicar_escopo(request, cfg, qs):
    """Médico e paciente só enxergam registros ligados a eles."""
    perfil = request.session.get("perfil")
    if chave_perfil(perfil) == _n(PERFIL_MEDICO):
        chave, valor = "medico", request.session.get("crm")
    elif chave_perfil(perfil) == _n(PERFIL_PACIENTE):
        chave, valor = "paciente", cpf_da_sessao(request)
    else:
        return qs
    campo = cfg.get("escopo", {}).get(chave)
    if not campo or not valor:
        return qs.none()  # na dúvida, não mostra nada
    if cfg["model"] is func_django and chave == "medico":
        # o médico enxerga os pacientes que atende (consulta já aceita pela recepção,
        # nunca uma simples solicitação) e aqueles de quem é o médico responsável
        atendidos = (
            Agendamento.objects.filter(medico_id=valor)
            .exclude(filtro_status(NOMES_SOLICITADA)).values("paciente_id")
        )
        return qs.filter(Q(pk__in=atendidos) | Q(medico_id=valor))
    return qs.filter(**{campo: valor})


def queryset_visivel(request, recurso):
    """Registros de um recurso que o perfil logado pode enxergar. É a regra única,
    usada pela listagem, pelo painel e pela ficha do paciente."""
    cfg = RECURSOS[recurso]
    qs = aplicar_escopo(request, cfg, cfg["model"].objects.all())
    if recurso == "consultas" and chave_perfil(request.session.get("perfil")) == _n(PERFIL_MEDICO):
        qs = qs.exclude(filtro_status(NOMES_SOLICITADA))  # médico vê só o que a recepção já aceitou
    return qs


def pacientes_visiveis(request):
    """Pacientes que o perfil logado pode ver (recepção/admin: todos; médico: os dele)."""
    return queryset_visivel(request, "pacientes")


def consultas_visiveis(request):
    return queryset_visivel(request, "consultas")


def get_recurso(recurso):
    if recurso not in RECURSOS:
        raise Http404
    return RECURSOS[recurso]


def login_requerido(view):
    @wraps(view)
    def interno(request, *args, **kwargs):
        if "username" not in request.session:
            destino = reverse("login")
            if request.method == "GET":  # depois do login, volta para onde a pessoa queria ir
                destino += "?" + urlencode({"next": request.get_full_path()})
            return redirect(destino)
        return view(request, *args, **kwargs)
    return interno


# Usuário administrador geral (igual ao do terminal). Em produção, defina estas
# variáveis de ambiente em vez de deixar a senha escrita no código.
SENHA_ROOT_PADRAO = "root@123"
ROOT_USER = os.environ.get("CLINICA_ROOT_USER", "root")
ROOT_SENHA = os.environ.get("CLINICA_ROOT_SENHA", SENHA_ROOT_PADRAO)

if ROOT_SENHA == SENHA_ROOT_PADRAO and not settings.DEBUG:
    logging.getLogger(__name__).warning(
        "SEGURANÇA: o administrador geral está com a senha padrão. "
        "Defina a variável de ambiente CLINICA_ROOT_SENHA."
    )


def senha_confere(usuario, senha):
    try:
        calculado = gerar_hash(senha, usuario.salt)
    except ValueError:  # salt inválido no banco
        return False
    return hmac.compare_digest(calculado, usuario.senha_hash)


def abrir_sessao(request, username, email, perfil, crm="", cpf=""):
    request.session.cycle_key()
    request.session["username"] = username
    request.session["email"] = email
    request.session["perfil"] = perfil
    request.session["crm"] = crm
    request.session["cpf"] = cpf
    if not request.POST.get("lembrar"):
        request.session.set_expiry(0)  # expira ao fechar o navegador


# ---- proteção contra tentativas de adivinhar a senha -------------------------
# Usa o cache do Django (em memória por padrão). Com vários processos/servidores,
# configure um cache compartilhado (Redis/Memcached) em CACHES para valer para todos.
LIMITE_TENTATIVAS = 5
JANELA_TENTATIVAS = 15 * 60  # segundos


def _chave_tentativas(request, ident):
    base = f"{request.META.get('REMOTE_ADDR', '')}|{(ident or '').strip().lower()}"
    return "clinica:login:" + hashlib.sha256(base.encode()).hexdigest()


def login_bloqueado(request, ident):
    return cache.get(_chave_tentativas(request, ident), 0) >= LIMITE_TENTATIVAS


def registrar_falha_login(request, ident):
    chave = _chave_tentativas(request, ident)
    cache.add(chave, 0, JANELA_TENTATIVAS)
    try:
        cache.incr(chave)
    except ValueError:  # a chave expirou entre as duas linhas
        cache.set(chave, 1, JANELA_TENTATIVAS)


def limpar_falhas_login(request, ident):
    cache.delete(_chave_tentativas(request, ident))


def _marca(ident):
    """Identificação curta (hash) para o log: nunca grava o que foi digitado, pois
    muita gente digita a senha no campo de usuário."""
    return hashlib.sha256((ident or "").encode()).hexdigest()[:8]


def destino_pos_login(request, proximo=""):
    """Volta para a página pedida (?next=), mas só se for do próprio site."""
    if proximo and url_has_allowed_host_and_scheme(
        proximo, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return proximo
    return reverse("dashboard")


def login_view(request):
    if request.method == "GET" and "username" in request.session:
        return redirect("dashboard")

    proximo = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST":
        ident = request.POST.get("identificador", "").strip()
        senha = request.POST.get("senha", "")

        if login_bloqueado(request, ident):
            registrar_auditoria(request, "login_bloqueado", f"id={_marca(ident)}")
            messages.error(request, "Muitas tentativas de acesso. Aguarde alguns minutos e tente novamente.")
            return render(request, "login.html", {"proximo": proximo}, status=429)

        # Login do administrador geral
        if (
            ident.lower() == ROOT_USER.lower()
            and hmac.compare_digest(
                senha.encode(),
                ROOT_SENHA.encode()
            )
        ):
            limpar_falhas_login(request, ident)
            abrir_sessao(request, "root", "", PERFIL_ROOT)
            registrar_auditoria(request, "login", "administrador geral")
            return redirect(destino_pos_login(request, proximo))

        # Busca pelo nome de usuário OU pelo e-mail
        usuario = (
            Usuario.objects
            .select_related("paciente", "id_perfil", "medico")
            .filter(
                Q(username__iexact=ident) |
                Q(email__iexact=ident)
            )
            .first()
        )

        # Confere a senha. Se o usuário não existe, faz a mesma conta mesmo assim,
        # para a resposta não demorar menos e revelar que o usuário não existe.
        if usuario is None:
            gerar_hash(senha, "00" * 16)
            confere = False
        else:
            confere = senha_confere(usuario, senha)

        if usuario and confere:
            if usuario.medico is not None and not usuario.medico.ativo:
                registrar_auditoria(request, "login_negado_inativo", f"id={_marca(ident)}")
                messages.error(request, "Seu acesso está desativado. Procure o administrador.")
                return render(request, "login.html", {"proximo": proximo})

            limpar_falhas_login(request, ident)
            abrir_sessao(
                request,
                usuario.username,
                usuario.email,
                usuario.id_perfil.nome_perfil,
                crm=usuario.medico_id or "",
                cpf=usuario.paciente_id or "",
            )
            registrar_auditoria(request, "login")
            return redirect(destino_pos_login(request, proximo))

        registrar_falha_login(request, ident)
        registrar_auditoria(request, "login_falhou", f"id={_marca(ident)}")
        messages.error(request, "E-mail ou senha incorretos.")

    return render(request, "login.html", {"proximo": proximo})


@require_POST
def logout_view(request):
    registrar_auditoria(request, "logout")
    request.session.flush()
    return redirect("login")


# ==================================================
# LOGIN COM GOOGLE
# ==================================================

def gerar_username_google(email):
    """
    Gera um username único de até 10 caracteres,
    respeitando o limite do campo Usuario.username.
    """
    base = email.split("@")[0].lower()
    base = re.sub(r"[^a-z0-9_]", "", base)[:10]

    if len(base) < 3:
        base = "google"

    username = base
    contador = 1

    while Usuario.objects.filter(username__iexact=username).exists():
        sufixo = str(contador)
        username = base[:10 - len(sufixo)] + sufixo
        contador += 1

    return username


def obter_perfil_paciente():
    return next(
        (
            perfil for perfil in Perfil.objects.all()
            if chave_perfil(perfil.nome_perfil) == _n(PERFIL_PACIENTE)
        ),
        None
    )


def google_configurado():
    return bool(
        requests and id_token
        and getattr(settings, "GOOGLE_CLIENT_ID", "")
        and getattr(settings, "GOOGLE_CLIENT_SECRET", "")
    )


def google_redirect_uri(request):
    """Usa GOOGLE_REDIRECT_URI do settings; se não existir, monta a partir da rota."""
    return getattr(settings, "GOOGLE_REDIRECT_URI", "") or request.build_absolute_uri(
        reverse("google_callback")
    )


def google_login(request):
    """
    Inicia o processo de autenticação com o Google.
    """
    if not google_configurado():
        messages.error(request, "A autenticação Google ainda não foi configurada.")
        return redirect("login")

    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state

    parametros = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": google_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }

    url_google = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(parametros)
    )

    return redirect(url_google)


def google_callback(request):
    """
    Recebe a resposta do Google, verifica a identidade
    e cria ou recupera a conta do paciente.
    """
    if not google_configurado():
        messages.error(request, "A autenticação Google ainda não foi configurada.")
        return redirect("login")

    estado_recebido = request.GET.get("state")
    estado_salvo = request.session.pop("google_oauth_state", None)

    if not estado_salvo or estado_recebido != estado_salvo:
        messages.error(request, "Não foi possível validar a autenticação Google.")
        return redirect("login")

    codigo = request.GET.get("code")

    if not codigo:
        messages.error(request, "A autenticação Google foi cancelada.")
        return redirect("login")

    try:
        resposta = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": codigo,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": google_redirect_uri(request),
                "grant_type": "authorization_code",
            },
            timeout=15,
        )

        resposta.raise_for_status()
        tokens = resposta.json()

        token_id = tokens.get("id_token")

        if not token_id:
            raise ValueError("O Google não retornou um ID token.")

        dados_google = id_token.verify_oauth2_token(
            token_id,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )

        if not dados_google.get("email_verified"):
            raise ValueError("O e-mail da conta Google não foi verificado.")

        google_sub = dados_google["sub"]
        email = dados_google["email"].strip().lower()
        nome_google = dados_google.get("name", "").strip()

        if len(email) > 50:
            messages.error(
                request,
                "O e-mail da conta Google ultrapassa o limite aceito pelo sistema."
            )
            return redirect("login")

    except Exception:  # falha de rede, token inválido, resposta inesperada...
        logging.getLogger(__name__).exception("Falha no login com Google")
        messages.error(
            request,
            "Não foi possível validar sua conta Google. Tente novamente."
        )
        return redirect("login")

    # Se essa conta Google já estiver cadastrada, recupera o usuário.
    identidade = (
        GoogleIdentity.objects
        .select_related("usuario__id_perfil", "usuario__paciente", "usuario__medico")
        .filter(google_sub=google_sub)
        .first()
    )

    if identidade:
        usuario = identidade.usuario

    else:
        # Não vincula automaticamente uma conta tradicional
        # apenas porque o e-mail é igual.
        if Usuario.objects.filter(email__iexact=email).exists():
            messages.error(
                request,
                "Já existe uma conta com esse e-mail. Entre pelo login tradicional."
            )
            return redirect("login")

        perfil = obter_perfil_paciente()

        if perfil is None:
            messages.error(
                request,
                "O perfil Paciente não foi encontrado no sistema."
            )
            return redirect("login")

        try:
            with transaction.atomic():
                salt = secrets.token_hex(16)

                # Senha aleatória, não conhecida pelo usuário.
                senha_aleatoria = secrets.token_urlsafe(48)

                usuario = Usuario.objects.create(
                    username=gerar_username_google(email),
                    email=email,
                    salt=salt,
                    senha_hash=gerar_hash(senha_aleatoria, salt),
                    id_perfil=perfil,
                    paciente=None,
                    medico=None,
                )

                GoogleIdentity.objects.create(
                    usuario=usuario,
                    google_sub=google_sub,
                    nome_google=nome_google[:150],
                )

        except IntegrityError:
            messages.error(
                request,
                "Não foi possível criar sua conta. Tente entrar novamente."
            )
            return redirect("login")

    # Usa o mesmo mecanismo de sessão do login tradicional.
    abrir_sessao(
        request,
        usuario.username,
        usuario.email,
        usuario.id_perfil.nome_perfil,
        crm=usuario.medico_id or "",
        cpf=usuario.paciente_id or "",
    )

    registrar_auditoria(request, "login_google")
    return redirect("dashboard")


# ==================================================
# COMPLETAR CADASTRO DO PACIENTE GOOGLE
# ==================================================

@login_requerido
def completar_cadastro_google(request):
    """
    Cria o paciente e vincula ao usuário Google
    depois que os dados obrigatórios forem informados.
    """

    usuario = (
        Usuario.objects
        .select_related("id_perfil", "paciente")
        .filter(username=request.session.get("username"))
        .first()
    )

    if usuario is None:
        messages.error(request, "Não foi possível localizar sua conta.")
        return redirect("login")

    # Somente contas criadas/vinculadas pelo Google podem usar esta tela.
    identidade = GoogleIdentity.objects.filter(usuario=usuario).first()

    if identidade is None:
        messages.error(request, "Esta conta não possui cadastro Google vinculado.")
        return redirect("dashboard")

    if chave_perfil(usuario.id_perfil.nome_perfil) != _n(PERFIL_PACIENTE):
        messages.error(request, "Esta página é exclusiva para pacientes.")
        return redirect("dashboard")

    # Se já existe paciente vinculado, não precisa preencher novamente.
    if usuario.paciente_id:
        request.session["cpf"] = usuario.paciente_id
        return redirect("dashboard")

    erros = {}
    dados = {
        "nome": identidade.nome_google,
        "cpf": "",
        "telefone": "",
        "data_nascimento": "",
    }

    if request.method == "POST":
        dados["nome"] = request.POST.get("nome", "").strip()
        dados["cpf"] = somente_digitos(request.POST.get("cpf", ""))
        dados["telefone"] = re.sub(
            r"\D", "", request.POST.get("telefone", "")
        )
        dados["data_nascimento"] = request.POST.get(
            "data_nascimento", ""
        ).strip()

        if len(dados["nome"]) < 3 or len(dados["nome"]) > 150:
            erros["nome"] = "Informe seu nome completo."

        if not cpf_valido(dados["cpf"]):
            erros["cpf"] = "CPF inválido. Informe os 11 números."
        elif func_django.objects.filter(cpf=dados["cpf"]).exists():
            erros["cpf"] = (
                "Este CPF já está cadastrado. Se você já foi atendido(a) na clínica, "
                "peça à recepção para vincular o seu acesso."
            )

        if not re.fullmatch(r"\d{10,11}", dados["telefone"]):
            erros["telefone"] = "Informe um telefone com DDD."

        data_nascimento = None

        try:
            data_nascimento = dt.date.fromisoformat(
                dados["data_nascimento"]
            )

            if data_nascimento >= hoje_local():
                erros["data_nascimento"] = (
                    "Informe uma data de nascimento válida."
                )

        except (ValueError, TypeError):
            erros["data_nascimento"] = (
                "Informe uma data de nascimento válida."
            )

        if not erros:
            try:
                with transaction.atomic():
                    paciente = func_django.objects.create(
                        cpf=dados["cpf"],
                        nome=dados["nome"],
                        telefone=dados["telefone"],
                        data_nascimento=data_nascimento,
                    )

                    usuario.paciente = paciente
                    usuario.save(update_fields=["paciente"])

                request.session["cpf"] = paciente.cpf

                messages.success(
                    request,
                    "Cadastro concluído! Seus dados foram salvos com sucesso."
                )

                return redirect("dashboard")

            except IntegrityError:
                erros["cpf"] = (
                    "Não foi possível salvar o cadastro. "
                    "Verifique se o CPF já está sendo utilizado."
                )

    return render(
        request,
        "completar_cadastro_google.html",
        {
            "dados": dados,
            "erros": erros,
            "ativo": "conta",
        }
    )


@login_requerido
def conta(request):
    username_sessao = request.session.get("username", "")

    # O administrador geral é definido no servidor (variáveis de ambiente), não no banco.
    if chave_perfil(request.session.get("perfil")) == _n(PERFIL_ROOT) and username_sessao == "root":
        messages.info(
            request,
            "O administrador geral é configurado no servidor e não possui conta para editar aqui."
        )
        return redirect("dashboard")

    usuario = (
        Usuario.objects
        .select_related("id_perfil", "paciente", "medico")
        .filter(username__iexact=username_sessao)
        .first()
    )

    if not usuario:
        messages.error(
            request,
            "Não foi possível localizar sua conta no banco de dados."
        )
        return redirect("dashboard")

    if request.method == "POST":
        acao = request.POST.get("acao")

        # ALTERAR DADOS DA CONTA
        if acao == "dados":
            username = request.POST.get("username", "").strip()
            email = request.POST.get("email", "").strip().lower()

            if not username or not email:
                messages.error(request, "Preencha todos os campos.")
                return redirect("conta")

            if len(username) > 10:
                messages.error(request, "O nome de usuário deve ter no máximo 10 caracteres.")
                return redirect("conta")

            # só confere o formato se o nome mudou (contas criadas pelo Google têm números)
            if username != usuario.username and not validar_nome(username):
                messages.error(request, "Use apenas letras e espaços no nome de usuário (mínimo de 3 caracteres).")
                return redirect("conta")

            if len(email) > 50 or not validar_email(email):
                messages.error(request, "Informe um e-mail válido.")
                return redirect("conta")

            if Usuario.objects.exclude(pk=usuario.pk).filter(
                username__iexact=username
            ).exists():
                messages.error(request, "Esse nome de usuário já está sendo utilizado.")
                return redirect("conta")

            if Usuario.objects.exclude(pk=usuario.pk).filter(
                email__iexact=email
            ).exists():
                messages.error(request, "Esse e-mail já está cadastrado.")
                return redirect("conta")

            usuario.username = username
            usuario.email = email
            usuario.save(update_fields=["username", "email"])

            request.session["username"] = username
            request.session["email"] = email
            registrar_auditoria(request, "conta_dados_alterados")

            messages.success(request, "Dados da conta atualizados com sucesso!")
            return redirect("conta")

        # ALTERAR SENHA
        elif acao == "senha":
            senha_atual = request.POST.get("senha_atual", "")
            senha_nova = request.POST.get("senha_nova", "")
            confirmar_senha = request.POST.get("confirmar_senha", "")

            if not senha_atual or not senha_nova or not confirmar_senha:
                messages.error(request, "Preencha todos os campos.")
                return redirect("conta")

            if not senha_confere(usuario, senha_atual):
                messages.error(request, "A senha atual está incorreta.")
                return redirect("conta")

            if len(senha_nova) < 8:
                messages.error(request, "A nova senha deve ter pelo menos 8 caracteres.")
                return redirect("conta")

            # mesma regra de senha do cadastro público
            if not validar_senha(senha_nova):
                messages.error(request, "Senha fraca! Verifique os requisitos mínimos de senha.")
                return redirect("conta")

            if senha_nova != confirmar_senha:
                messages.error(request, "A confirmação da senha não corresponde.")
                return redirect("conta")

            if senha_atual == senha_nova:
                messages.error(request, "A nova senha deve ser diferente da atual.")
                return redirect("conta")

            salt = secrets.token_bytes(16)

            usuario.salt = salt.hex()
            usuario.senha_hash = hashlib.pbkdf2_hmac(
                "sha256",
                senha_nova.encode("utf-8"),
                salt,
                ITERACOES
            ).hex()

            usuario.save(update_fields=["salt", "senha_hash"])
            registrar_auditoria(request, "senha_alterada")

            messages.success(request, "Sua senha foi alterada com sucesso!")
            return redirect("conta")

    return render(request, "conta.html", {
        "ativo": "conta",
        "usuario": usuario,
    })


def rotulo(obj):
    """Texto legível de um registro (usado nas tabelas e nas listas de seleção)."""
    if isinstance(obj, Agendamento):
        return f"{obj.paciente.nome or obj.paciente.cpf} - {formatar(obj.data_hora)}"
    if isinstance(obj, Medico):
        return f"{obj.nome} (CRM {obj.crm})"
    if isinstance(obj, func_django):
        return f"{obj.nome or 'Sem nome'} ({obj.cpf})"
    for attr in ("nome", "descricao", "nome_perfil", "username"):
        valor = getattr(obj, attr, None)
        if valor:
            return str(valor)
    return str(obj)


def valor_da_celula(obj, campo, recurso):
    valor = getattr(obj, campo)
    if recurso == "consultas" and campo == "data_hora" and eh_status(obj, NOMES_SOLICITADA):
        return f"{data_local(valor):%d/%m/%Y} (horário a definir)"
    return formatar(valor)


def formatar(valor):
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if valor is None:
        return ""
    if isinstance(valor, dt.datetime):
        if timezone.is_aware(valor):
            valor = timezone.localtime(valor)
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, dt.date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, dt.time):
        return valor.strftime("%H:%M")
    if isinstance(valor, models.Model):
        return rotulo(valor)
    return valor


class ConflitoDeHorario(Exception):
    """O médico já tem atendimento marcado no horário pedido."""


# Recursos que podem ser editados e o formulário de cada um (None = formulário
# automático, sem a chave primária). Usuários não entram aqui: cada pessoa altera
# os próprios dados em "Minha conta". Consultas e pagamentos têm telas próprias.
EDITAVEIS = {
    "pacientes": PacienteEdicaoForm,
    "prontuarios": ProntuarioForm,
    "medicos": None,
    "especialidades": None,
    "vinculos": None,
    "horarios": None,  # definido mais abaixo (HorarioForm)
}


@login_requerido
def lista(request, recurso):
    cfg = get_recurso(recurso)
    exigir(request, recurso, "ver")
    perfil_atual = request.session.get("perfil")
    acoes = acoes_do_perfil(perfil_atual, recurso)

    qs = queryset_visivel(request, recurso)
    relacionados = [c for c, _ in cfg["colunas"] if cfg["model"]._meta.get_field(c).is_relation]
    if relacionados:
        qs = qs.select_related(*relacionados)
    if recurso == "pagamentos":
        qs = qs.select_related("agendamento__paciente")  # o rótulo da consulta usa o paciente

    q = request.GET.get("q", "").strip()
    if q and cfg["busca"]:
        filtro = Q()
        for campo in cfg["busca"]:
            filtro |= Q(**{f"{campo}__icontains": q})
        qs = qs.filter(filtro)

    if cfg.get("ordem"):
        qs = qs.order_by(*cfg["ordem"])

    pagina = paginar(request, qs)
    objetos = list(pagina.object_list)
    campos = [c for c, _ in cfg["colunas"]]

    eh_recepcionista = chave_perfil(perfil_atual) == _n(PERFIL_RECEPCIONISTA)
    pode_registrar_dinheiro = (
        recurso == "consultas"
        and eh_recepcionista
        and "criar" in acoes_do_perfil(perfil_atual, "pagamentos")
    )
    pagamentos_existentes = set()
    if pode_registrar_dinheiro and objetos:
        pagamentos_existentes = set(
            Pagamento.objects.filter(agendamento__in=[o.pk for o in objetos])
            .exclude(filtro_status_pagamento(NOMES_PGTO_CANCELADO))
            .values_list("agendamento_id", flat=True)
        )

    pode_cancelar = recurso == "consultas" and "cancelar" in acoes
    pode_editar = recurso in EDITAVEIS and "editar" in acoes
    hoje = hoje_local()

    linhas = []
    for obj in objetos:
        pendente = recurso == "consultas" and eh_status(obj, NOMES_SOLICITADA)
        cancelada = recurso == "consultas" and eh_status(obj, NOMES_CANCELADA)
        linhas.append({
            "pk": obj.pk,
            "valores": [valor_da_celula(obj, c, recurso) for c in campos],
            "pendente": pendente,
            "pode_registrar_dinheiro": (
                pode_registrar_dinheiro
                and _n(obj.tipo) == _n("Consulta")
                and not pendente and not cancelada
                and obj.pk not in pagamentos_existentes
            ),
            "pode_cancelar": (
                pode_cancelar and not cancelada and data_local(obj.data_hora) >= hoje
            ),
        })

    return render(request, "lista.html", {
        "recurso": recurso,
        "titulo": cfg["titulo"],
        "ativo": recurso,
        "colunas": [r for _, r in cfg["colunas"]],
        "linhas": linhas,
        "pagina": pagina,
        "q": q,
        "pode_criar": cfg.get("criar", True) and "criar" in acoes,
        "pode_editar": pode_editar,
        "pode_excluir": "excluir" in acoes,
        "pode_aceitar": recurso == "consultas" and "aceitar" in acoes,
        "pode_cancelar": pode_cancelar,
        "pode_solicitar": recurso == "consultas" and "solicitar" in acoes,
        "pode_registrar_dinheiro": pode_registrar_dinheiro,
        "pendentes": (
            Agendamento.objects.filter(
                filtro_status(NOMES_SOLICITADA)
            ).count()
            if recurso == "consultas" and "aceitar" in acoes
            else 0
        ),
    })


def _campo_form(campo, **kwargs):
    f = campo.formfield(**kwargs)
    if f is None:
        return None
    if isinstance(campo, models.ForeignKey):
        f.label_from_instance = rotulo
    if isinstance(campo, models.DateTimeField):
        f.widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
    elif isinstance(campo, models.DateField):
        f.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    elif isinstance(campo, models.TimeField):
        f.widget = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
    return f



def _montar_form(request, Form, **extra):
    """Cria o formulário; os que precisam saber quem está logado recebem o request."""
    if getattr(Form, "precisa_request", False):
        extra["request"] = request
    dados = request.POST if request.method == "POST" else None
    return Form(dados, **extra)


@login_requerido
def novo(request, recurso):
    cfg = get_recurso(recurso)
    exigir(request, recurso, "criar")
    if not cfg.get("criar", True):
        raise Http404
    Form = cfg.get("form") or modelform_factory(
        cfg["model"], fields="__all__",
        exclude=cfg.get("esconder", []), formfield_callback=_campo_form,
    )
    form = _montar_form(request, Form)
    if request.method == "POST" and form.is_valid():
        try:
            objeto = form.save()
        except IntegrityError as erro:
            detalhe = erro.args[-1] if erro.args else erro
            form.add_error(None, f"O banco de dados recusou o cadastro: {detalhe}")
        except ConflitoDeHorario as erro:
            form.add_error(None, str(erro))
        else:
            registrar_auditoria(request, "criar", f"recurso={recurso} id={getattr(objeto, 'pk', '-')}")
            messages.success(request, "Cadastro salvo com sucesso.")
            return redirect("lista", recurso=recurso)
    return render(request, "form.html", {
        "form": form, "recurso": recurso, "ativo": recurso,
        "titulo": f"Cadastrar em {cfg['titulo'].lower()}",
        "voltar": reverse("lista", args=[recurso]),
    })


@login_requerido
def editar(request, recurso, pk):
    cfg = get_recurso(recurso)
    if recurso not in EDITAVEIS:
        raise Http404
    exigir(request, recurso, "editar")

    # só edita o que o perfil também pode ver (o médico, apenas os próprios prontuários)
    try:
        obj = get_object_or_404(queryset_visivel(request, recurso), pk=pk)
    except (ValueError, TypeError):
        raise Http404

    Form = EDITAVEIS[recurso] or modelform_factory(
        cfg["model"], fields="__all__",
        exclude=[cfg["model"]._meta.pk.name] + list(cfg.get("esconder", [])),
        formfield_callback=_campo_form,
    )
    form = _montar_form(request, Form, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError as erro:
            detalhe = erro.args[-1] if erro.args else erro
            form.add_error(None, f"O banco de dados recusou a alteração: {detalhe}")
        else:
            registrar_auditoria(request, "editar", f"recurso={recurso} id={obj.pk}")
            messages.success(request, "Alterações salvas com sucesso.")
            return redirect("lista", recurso=recurso)
    return render(request, "form.html", {
        "form": form, "recurso": recurso, "ativo": recurso,
        "titulo": f"Editar em {cfg['titulo'].lower()}", "botao": "Salvar alterações",
        "voltar": reverse("lista", args=[recurso]),
    })


@login_requerido
@require_POST
def excluir(request, recurso, pk):
    cfg = get_recurso(recurso)
    exigir(request, recurso, "excluir")
    try:
        obj = get_object_or_404(queryset_visivel(request, recurso), pk=pk)
    except (ValueError, TypeError):
        raise Http404

    if recurso == "usuarios" and obj.username.lower() == (request.session.get("username") or "").lower():
        messages.error(request, "Você não pode excluir o seu próprio usuário.")
        return redirect("lista", recurso=recurso)

    try:
        obj.delete()
        registrar_auditoria(request, "excluir", f"recurso={recurso} id={pk}")
        messages.success(request, "Registro excluído.")
    except ProtectedError:
        messages.error(request, "Não foi possível excluir: existem outros registros vinculados a este.")
    if recurso == "pagamentos":
        return redirect("financeiro")
    return redirect("lista", recurso=recurso)


# ==================================================
# SOLICITAÇÃO E ACEITE DE CONSULTAS
# ==================================================
# Nomes aceitos na tabela status_agendamento (se não existir, o primeiro é criado)
NOMES_SOLICITADA = ("Solicitada", "Solicitado")
NOMES_CONFIRMADA = ("Agendada", "Agendado", "Confirmada", "Confirmado")
NOMES_CANCELADA = ("Cancelada", "Cancelado", "Recusada", "Recusado")
TIPOS_ATENDIMENTO = [("Consulta", "Consulta"), ("Exame", "Exame")]


def filtro_status(nomes):
    filtro = Q()
    for nome in nomes:
        filtro |= Q(status__descricao__iexact=nome)
    return filtro


def eh_status(agendamento, nomes):
    return _n(agendamento.status.descricao) in {_n(n) for n in nomes}


def obter_status(nomes):
    return (
        StatusAgendamento.objects.filter(descricao__iexact=nomes[0]).first()
        or next((st for st in (StatusAgendamento.objects.filter(descricao__iexact=n).first() for n in nomes[1:]) if st), None)
        or StatusAgendamento.objects.create(descricao=nomes[0])
    )


def agora_como(data):
    return timezone.now() if timezone.is_aware(data) else dt.datetime.now()


def combinar(data, hora):
    quando = dt.datetime.combine(data, hora)
    return timezone.make_aware(quando) if settings.USE_TZ else quando


def inicio_do_dia(data):
    return combinar(data, dt.time.min)


def data_local(valor):
    if timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return valor.date()


# ==================================================
# FINANCEIRO (resumo + pagamentos)
# ==================================================

FORMAS = ["Dinheiro", "Pix", "Cartão", "Convênio"]

# Formas oferecidas ao paciente. "Pix" escrito igual ao da recepção, para os
# relatórios não separarem "PIX" e "Pix" como se fossem formas diferentes.
FORMAS_PAGAMENTO_PACIENTE = [
    "Pix",
    "Cartão de crédito",
    "Cartão de débito",
]

STATUS = ["Concluído", "Pendente", "Cancelado"]

VALOR_CONSULTA = Decimal("60.00")

# Nomes aceitos na tabela status_pagamento (o primeiro é o criado se não existir)
NOMES_PGTO_CONCLUIDO = ("Concluído", "Concluido", "Pago")
NOMES_PGTO_PENDENTE = ("Pendente",)
NOMES_PGTO_CANCELADO = ("Cancelado", "Cancelada")


def filtro_status_pagamento(nomes):
    filtro = Q()
    for nome in nomes:
        filtro |= Q(status_pagamento__descricao__iexact=nome)
    return filtro


def eh_status_pagamento(pagamento, nomes):
    return _n(pagamento.status_pagamento.descricao) in {_n(n) for n in nomes}


def obter_status_pagamento(nome):
    return (
        StatusPagamento.objects.filter(descricao__iexact=nome).first()
        or StatusPagamento.objects.create(descricao=nome)
    )


def pagamento_ativo_existe(agendamento):
    """Já existe pagamento (pendente ou concluído) para este atendimento?"""
    return (
        Pagamento.objects.filter(agendamento=agendamento)
        .exclude(filtro_status_pagamento(NOMES_PGTO_CANCELADO))
        .exists()
    )


def classe_status_pagamento(pagamento):
    if eh_status_pagamento(pagamento, NOMES_PGTO_CONCLUIDO):
        return "badge-ok"
    if eh_status_pagamento(pagamento, NOMES_PGTO_PENDENTE):
        return "badge-warn"
    return "badge-off"


@login_requerido
def financeiro(request):
    exigir(request, "pagamentos", "ver")
    acoes = acoes_do_perfil(request.session.get("perfil"), "pagamentos")
    base = queryset_visivel(request, "pagamentos").select_related(
        "agendamento__paciente", "status_pagamento"
    )

    q = request.GET.get("q", "").strip()
    pagamentos = base
    if q:
        pagamentos = base.filter(
            Q(agendamento__paciente__nome__icontains=q)
            | Q(agendamento__paciente__cpf__icontains=q)
            | Q(descricao__icontains=q)
        )

    def soma(nomes):
        return Sum("valor", filter=filtro_status_pagamento(nomes))

    # o resumo considera todos os pagamentos, mesmo com a busca ativa
    resumo = base.aggregate(
        recebido=soma(NOMES_PGTO_CONCLUIDO), pendente=soma(NOMES_PGTO_PENDENTE),
        cancelado=soma(NOMES_PGTO_CANCELADO), quantidade=Count("pk"),
    )
    for chave in ("recebido", "pendente", "cancelado"):
        resumo[chave] = resumo[chave] or Decimal("0")
    resumo["total"] = resumo["recebido"] + resumo["pendente"] + resumo["cancelado"]

    pagina = paginar(request, pagamentos.order_by("-data_pagamento", "-id_pagamento"))
    itens = list(pagina.object_list)
    for p in itens:
        p.classe_status = classe_status_pagamento(p)
        p.esta_pendente = eh_status_pagamento(p, NOMES_PGTO_PENDENTE)
        p.esta_cancelado = eh_status_pagamento(p, NOMES_PGTO_CANCELADO)

    return render(request, "financeiro.html", {
        "ativo": "pagamentos", "resumo": resumo, "q": q,
        "pode_criar": "criar" in acoes, "pode_excluir": "excluir" in acoes,
        "pode_cancelar": "cancelar" in acoes,
        "pode_pagar": "pagar" in acoes,
        "eh_paciente": chave_perfil(request.session.get("perfil")) == _n(PERFIL_PACIENTE),
        "pagamentos": itens,
        "pagina": pagina,
    })


class AgendamentoChoice(forms.ModelChoiceField):
    def label_from_instance(self, ag):
        # formatar() converte para o horário local (um f-string direto mostraria UTC)
        return f"{ag.tipo} - {ag.paciente.nome or ag.paciente.cpf} ({ag.paciente.cpf}) - {descrever_data_hora(ag)}"


def descrever_data_hora(ag):
    """Solicitações ainda não têm horário: só a data pedida."""
    if eh_status(ag, NOMES_SOLICITADA):
        return f"{data_local(ag.data_hora):%d/%m/%Y} (horário a definir)"
    return formatar(ag.data_hora)


class PagamentoForm(forms.ModelForm):
    # só atendimentos que podem ser cobrados (nem solicitação pendente, nem cancelado)
    agendamento = AgendamentoChoice(
        queryset=(
            Agendamento.objects.select_related("paciente", "status")
            .exclude(filtro_status(NOMES_CANCELADA)).exclude(filtro_status(NOMES_SOLICITADA))
            .order_by("-data_hora")
        ),
        label="Consulta do paciente",
    )
    valor = forms.DecimalField(
        min_value=Decimal("0.01"), max_digits=10, decimal_places=2,
        localize=True, label="Valor (R$)",
        error_messages={"min_value": "O valor deve ser maior que zero."},
    )
    forma_pagamento = forms.ChoiceField(choices=[(f, f) for f in FORMAS], label="Forma de pagamento")
    status_pagamento = forms.ModelChoiceField(
        queryset=StatusPagamento.objects.filter(descricao__in=STATUS), label="Status",
    )
    data_pagamento = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), label="Data do pagamento",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # garante que "Concluído", "Pendente" e "Cancelado" existam para escolher
        if StatusPagamento.objects.filter(descricao__in=STATUS).count() < len(STATUS):
            for nome in STATUS:
                obter_status_pagamento(nome)
        self.fields["status_pagamento"].label_from_instance = rotulo

    def clean(self):
        dados = super().clean()
        ag, status = dados.get("agendamento"), dados.get("status_pagamento")
        cancelando = status is not None and _n(status.descricao) in {_n(n) for n in NOMES_PGTO_CANCELADO}
        if ag and not cancelando and pagamento_ativo_existe(ag):
            self.add_error("agendamento", "Esta consulta já possui um pagamento registrado.")
        return dados

    class Meta:
        model = Pagamento
        fields = ["agendamento", "descricao", "valor", "forma_pagamento", "status_pagamento", "data_pagamento"]
        labels = {"descricao": "Descrição (consulta, exame, etc.)"}


@login_requerido
def novo_pagamento(request):
    exigir(request, "pagamentos", "criar")
    form = PagamentoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        pagamento = form.save()
        registrar_auditoria(request, "pagamento_registrado", f"id={pagamento.pk}")
        messages.success(request, "Pagamento registrado com sucesso.")
        return redirect("financeiro")
    return render(request, "form.html", {
        "form": form, "recurso": "pagamentos", "ativo": "pagamentos",
        "titulo": "Registrar pagamento", "voltar": reverse("financeiro"),
    })


@login_requerido
@require_POST
def confirmar_pagamento(request, pk):
    exigir(request, "pagamentos", "criar")
    pag = get_object_or_404(Pagamento.objects.select_related("status_pagamento"), pk=pk)
    if eh_status_pagamento(pag, NOMES_PGTO_PENDENTE):
        pag.status_pagamento = obter_status_pagamento("Concluído")
        pag.save(update_fields=["status_pagamento"])
        registrar_auditoria(request, "pagamento_confirmado", f"id={pag.pk}")
        messages.success(request, "Pagamento confirmado.")
    else:
        messages.warning(request, "Este pagamento não está pendente.")
    return redirect("financeiro")


@login_requerido
@require_POST
def cancelar_pagamento(request, pk):
    """Cancela sem apagar: o registro continua no histórico financeiro."""
    exigir(request, "pagamentos", "cancelar")
    pag = get_object_or_404(Pagamento.objects.select_related("status_pagamento"), pk=pk)
    if eh_status_pagamento(pag, NOMES_PGTO_CANCELADO):
        messages.warning(request, "Este pagamento já está cancelado.")
    else:
        pag.status_pagamento = obter_status_pagamento("Cancelado")
        pag.save(update_fields=["status_pagamento"])
        registrar_auditoria(request, "pagamento_cancelado", f"id={pag.pk}")
        messages.success(request, "Pagamento cancelado.")
    return redirect("financeiro")




# ---- agenda dos médicos (tabela horarios_medicos) ---------------------------
DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
               "Sexta-feira", "Sábado", "Domingo"]
_INDICE_DIA = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "dom": 6}


def indice_dia_semana(texto):
    """'Segunda', 'segunda-feira', 'SEG'... -> 0 (segunda) a 6 (domingo)."""
    return _INDICE_DIA.get(_n(texto)[:3])


def medico_atende_em(medico, quando):
    """O horário está dentro da agenda cadastrada do médico? Se o médico ainda
    não tem nenhum horário cadastrado, não há restrição (comportamento antigo)."""
    horarios = list(HorarioMedico.objects.filter(medico=medico))
    if not horarios:
        return True
    local = timezone.localtime(quando) if timezone.is_aware(quando) else quando
    return any(
        indice_dia_semana(h.dia_semana) == local.weekday()
        and h.hora_inicio <= local.time() < h.hora_fim
        for h in horarios
    )


def medico_ocupado(medico, quando, ignorar_pk=None):
    ocupados = (
        Agendamento.objects.filter(medico=medico, data_hora=quando)
        .exclude(filtro_status(NOMES_CANCELADA)).exclude(filtro_status(NOMES_SOLICITADA))
    )
    if ignorar_pk:
        ocupados = ocupados.exclude(pk=ignorar_pk)
    return ocupados.exists()


class HorarioForm(forms.ModelForm):
    """Horário de atendimento de um médico (alimenta a validação ao agendar)."""

    dia_semana = forms.ChoiceField(choices=[(d, d) for d in DIAS_SEMANA], label="Dia da semana")
    hora_inicio = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"), label="Início")
    hora_fim = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"), label="Fim")

    class Meta:
        model = HorarioMedico
        fields = ["medico", "dia_semana", "hora_inicio", "hora_fim"]
        labels = {"medico": "Médico"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medico"].label_from_instance = rotulo
        # registros antigos podem ter outra grafia ("Segunda"): mostra o dia certo na lista
        indice = indice_dia_semana(self.initial.get("dia_semana"))
        if indice is not None:
            self.initial["dia_semana"] = DIAS_SEMANA[indice]

    def clean(self):
        dados = super().clean()
        medico, dia = dados.get("medico"), dados.get("dia_semana")
        inicio, fim = dados.get("hora_inicio"), dados.get("hora_fim")
        if inicio and fim:
            if fim <= inicio:
                self.add_error("hora_fim", "O fim precisa ser depois do início.")
            elif medico and dia:
                outros = HorarioMedico.objects.filter(medico=medico)
                if self.instance and self.instance.pk:
                    outros = outros.exclude(pk=self.instance.pk)
                for h in outros:
                    if indice_dia_semana(h.dia_semana) == indice_dia_semana(dia) and h.hora_inicio < fim and inicio < h.hora_fim:
                        self.add_error(None, "Esse horário se sobrepõe a outro já cadastrado para o médico nesse dia.")
                        break
        return dados


RECURSOS["horarios"]["form"] = HorarioForm
EDITAVEIS["horarios"] = HorarioForm


class EscolhaEspecialidadeForm(forms.Form):
    tipo = forms.ChoiceField(choices=TIPOS_ATENDIMENTO, label="Tipo de atendimento")
    especialidade = forms.ModelChoiceField(
        queryset=Especialidade.objects.filter(medicoespecialidade__medico__ativo=True).distinct().order_by("nome"),
        label="Especialidade",
    )
    data_hora = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        label="Data e hora desejadas",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["especialidade"].label_from_instance = lambda e: e.nome

    def clean(self):
        dados = super().clean()
        esp, quando = dados.get("especialidade"), dados.get("data_hora")
        if esp and quando:
            if quando <= agora_como(quando):
                self.add_error("data_hora", "Escolha uma data e hora futuras.")
            else:
                # primeiro médico ativo da especialidade que esteja livre e em horário de atendimento
                candidatos = (Medico.objects.filter(ativo=True, medicoespecialidade__especialidade=esp)
                              .distinct().order_by("nome"))
                medico = next(
                    (m for m in candidatos if not medico_ocupado(m, quando) and medico_atende_em(m, quando)),
                    None,
                )
                if medico is None:
                    self.add_error("data_hora", f"Nenhum médico de {esp.nome} disponível nesse horário. Escolha outro.")
                else:
                    dados["medico"] = medico
        return dados


class SolicitarConsultaForm(forms.Form):
    """O paciente pede só a especialidade e o dia; a recepção define médico e horário."""

    tipo = forms.ChoiceField(choices=TIPOS_ATENDIMENTO, label="Tipo de atendimento")
    especialidade = forms.ModelChoiceField(
        queryset=Especialidade.objects.filter(medicoespecialidade__medico__ativo=True).distinct().order_by("nome"),
        label="Especialidade",
    )
    data = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), label="Data desejada")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["especialidade"].label_from_instance = lambda e: e.nome

    def clean(self):
        dados = super().clean()
        esp, data = dados.get("especialidade"), dados.get("data")
        if esp and data:
            if data < hoje_local():
                self.add_error("data", "Escolha uma data de hoje em diante.")
            else:
                # médico provisório da especialidade; a recepção pode trocá-lo ao aceitar
                medico = Medico.objects.filter(ativo=True, medicoespecialidade__especialidade=esp).order_by("nome").first()
                if medico is None:
                    self.add_error("especialidade", "Não há médico ativo nessa especialidade.")
                else:
                    dados["medico"] = medico
        return dados


@login_requerido
def solicitar_consulta(request):
    exigir(request, "consultas", "solicitar")

    # Busca diretamente o usuário autenticado e seu paciente vinculado.
    usuario = (
        Usuario.objects
        .select_related("paciente")
        .filter(username=request.session.get("username"))
        .first()
    )

    paciente = (
        usuario.paciente
        if usuario and usuario.paciente_id
        else None
    )

    if paciente is None:
        messages.error(request, "Seu usuário não está vinculado a um paciente. Procure a recepção.")
        return redirect("lista", recurso="consultas")

    form = SolicitarConsultaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        dados = form.cleaned_data
        # evita o mesmo pedido repetido (duplo clique, reenvio da página...)
        repetida = (
            Agendamento.objects.filter(
                paciente=paciente, tipo=dados["tipo"],
                medico__medicoespecialidade__especialidade=dados["especialidade"],
                data_hora__gte=inicio_do_dia(dados["data"]),
                data_hora__lt=inicio_do_dia(dados["data"] + dt.timedelta(days=1)),
            ).exclude(filtro_status(NOMES_CANCELADA)).exists()
        )
        if repetida:
            messages.warning(request, "Você já tem uma solicitação ou consulta desse tipo, nessa especialidade e data.")
            return redirect("lista", recurso="consultas")

        ag = Agendamento.objects.create(
            paciente=paciente, medico=dados["medico"],
            data_hora=inicio_do_dia(dados["data"]), status=obter_status(NOMES_SOLICITADA),
            tipo=dados["tipo"],
        )
        registrar_auditoria(request, "consulta_solicitada", f"id={ag.pk}")
        messages.success(request, f"Solicitação de {dados['tipo'].lower()} enviada para {dados['especialidade'].nome} em {dados['data']:%d/%m/%Y}. A recepção vai definir o horário e confirmar.")
        return redirect("lista", recurso="consultas")
    return render(request, "form.html", {
        "form": form, "recurso": "consultas", "ativo": "consultas",
        "titulo": "Solicitar consulta ou exame", "botao": "Enviar solicitação",
        "voltar": reverse("lista", args=["consultas"]),
    })


@login_requerido
@require_POST
def responder_consulta(request, pk, acao):
    exigir(request, "consultas", "aceitar")
    ag = get_object_or_404(Agendamento.objects.select_related("status", "medico"), pk=pk)

    if not eh_status(ag, NOMES_SOLICITADA):
        messages.warning(request, "Esta solicitação já foi respondida.")
    elif acao == "aceitar":
        if medico_ocupado(ag.medico, ag.data_hora, ignorar_pk=ag.pk):
            messages.error(request, "Não foi possível aceitar: o médico já tem consulta marcada nesse horário.")
        else:
            ag.status = obter_status(NOMES_CONFIRMADA)
            ag.save(update_fields=["status"])
            registrar_auditoria(request, "consulta_aceita", f"id={ag.pk}")
            messages.success(request, "Consulta aceita e agendada.")
    else:
        ag.status = obter_status(NOMES_CANCELADA)
        ag.save(update_fields=["status"])
        registrar_auditoria(request, "consulta_recusada", f"id={ag.pk}")
        messages.success(request, "Solicitação recusada.")
    return redirect("lista", recurso="consultas")


@login_requerido
@require_POST
def cancelar_consulta(request, pk):
    """Cancela uma consulta/exame. O paciente cancela só os seus; a recepção, qualquer um."""
    exigir(request, "consultas", "cancelar")
    ag = get_object_or_404(
        queryset_visivel(request, "consultas").select_related("status", "paciente"), pk=pk
    )

    if eh_status(ag, NOMES_CANCELADA):
        messages.warning(request, "Este atendimento já está cancelado.")
    elif data_local(ag.data_hora) < hoje_local():
        messages.error(request, "Não é possível cancelar um atendimento que já passou.")
    else:
        pagamentos = list(
            Pagamento.objects.filter(agendamento=ag)
            .exclude(filtro_status_pagamento(NOMES_PGTO_CANCELADO))
            .select_related("status_pagamento")
        )
        if any(eh_status_pagamento(p, NOMES_PGTO_CONCLUIDO) for p in pagamentos):
            messages.error(
                request,
                "Há pagamento concluído para este atendimento. Cancele o pagamento no Financeiro "
                "(a recepção faz isso) antes de cancelar o atendimento."
            )
        else:
            with transaction.atomic():
                for p in pagamentos:  # pagamentos ainda pendentes deixam de valer
                    p.status_pagamento = obter_status_pagamento("Cancelado")
                    p.save(update_fields=["status_pagamento"])
                ag.status = obter_status(NOMES_CANCELADA)
                ag.save(update_fields=["status"])
            registrar_auditoria(request, "consulta_cancelada", f"id={ag.pk}")
            messages.success(request, "Atendimento cancelado.")
    return redirect("lista", recurso="consultas")


# ==================================================
# PAGAMENTO PELO PACIENTE
# ==================================================

class PagamentoPacienteForm(forms.Form):
    agendamento = AgendamentoChoice(
        queryset=Agendamento.objects.none(),
        label="Consulta a pagar"
    )

    valor = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
        initial=VALOR_CONSULTA,
        label="Valor (R$)",
        widget=forms.NumberInput(attrs={
            "readonly": "readonly",
            "step": "0.01",
        }),
        error_messages={
            "min_value": "O valor deve ser maior que zero."
        },
    )

    forma_pagamento = forms.ChoiceField(
        choices=[(f, f) for f in FORMAS_PAGAMENTO_PACIENTE],
        label="Forma de pagamento"
    )

    def __init__(self, *args, cpf=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["agendamento"].queryset = (
            Agendamento.objects.select_related(
                "paciente", "status"
            )
            .filter(paciente=cpf)
            .exclude(filtro_status(NOMES_CANCELADA))
            .exclude(filtro_status(NOMES_SOLICITADA))
            .order_by("-data_hora")
        )

    def clean_agendamento(self):
        ag = self.cleaned_data["agendamento"]
        if pagamento_ativo_existe(ag):
            raise ValidationError("Esta consulta já possui um pagamento registrado.")
        return ag


@login_requerido
def pagar(request):
    exigir(request, "pagamentos", "pagar")
    cpf = cpf_da_sessao(request) or None
    form = PagamentoPacienteForm(request.POST or None, cpf=cpf)
    if request.method == "POST" and form.is_valid():
        ag = form.cleaned_data["agendamento"]
        pagamento = Pagamento.objects.create(
            agendamento=ag, descricao=f"{ag.tipo} de {formatar(ag.data_hora)}",
            valor=VALOR_CONSULTA, forma_pagamento=form.cleaned_data["forma_pagamento"],
            status_pagamento=obter_status_pagamento("Pendente"), data_pagamento=hoje_local(),
        )
        registrar_auditoria(request, "pagamento_enviado", f"id={pagamento.pk}")
        messages.success(request, "Pagamento enviado! A recepção irá confirmar o recebimento.")
        return redirect("financeiro")
    return render(request, "form.html", {
        "form": form, "recurso": "pagamentos", "ativo": "pagamentos",
        "titulo": "Realizar pagamento", "botao": "Enviar pagamento", "voltar": reverse("financeiro"),
    })


@login_requerido
def pagar_consulta(request):
    """
    Versão em cartões da tela de pagamento: o paciente escolhe a forma de
    pagamento em cada consulta. O pagamento fica pendente até a recepção
    confirmar o recebimento.
    """
    exigir(request, "pagamentos", "pagar")

    cpf = cpf_da_sessao(request)
    if not cpf:
        messages.error(request, "Paciente não identificado.")
        return redirect("dashboard")

    if request.method == "POST":
        forma = request.POST.get("forma_pagamento")

        if forma not in FORMAS_PAGAMENTO_PACIENTE:
            messages.error(request, "Forma de pagamento inválida.")
            return redirect("pagar_consulta")

        try:
            agendamento = get_object_or_404(
                Agendamento.objects.select_related("status"),
                pk=int(request.POST.get("agendamento_id", "")),
                paciente_id=cpf,
            )
        except (TypeError, ValueError):
            raise Http404

        if eh_status(agendamento, NOMES_SOLICITADA) or eh_status(agendamento, NOMES_CANCELADA):
            messages.error(request, "Não é possível pagar um atendimento ainda não confirmado ou cancelado.")
            return redirect("pagar_consulta")

        if pagamento_ativo_existe(agendamento):
            messages.warning(request, "Esta consulta já possui um pagamento registrado.")
            return redirect("pagar_consulta")

        pagamento = Pagamento.objects.create(
            agendamento=agendamento,
            descricao="Pagamento de consulta médica",
            valor=VALOR_CONSULTA,
            forma_pagamento=forma,
            status_pagamento=obter_status_pagamento("Pendente"),
            data_pagamento=hoje_local(),
        )
        registrar_auditoria(request, "pagamento_enviado", f"id={pagamento.pk}")

        messages.success(
            request,
            "Solicitação de pagamento registrada. "
            "Aguardando confirmação da transação."
        )
        return redirect("pagar_consulta")

    agendamentos = list(
        Agendamento.objects.filter(paciente_id=cpf)
        .exclude(filtro_status(NOMES_CANCELADA))
        .exclude(filtro_status(NOMES_SOLICITADA))
        .select_related("medico", "status")
        .order_by("-data_hora")
    )
    ja_pagos = set(
        Pagamento.objects.filter(agendamento__in=[a.pk for a in agendamentos])
        .exclude(filtro_status_pagamento(NOMES_PGTO_CANCELADO))
        .values_list("agendamento_id", flat=True)
    )
    for a in agendamentos:
        a.ja_pago = a.pk in ja_pagos

    pagamentos = (
        Pagamento.objects.filter(agendamento__paciente_id=cpf)
        .select_related("agendamento", "status_pagamento")
        .order_by("-data_pagamento")
    )

    return render(
        request,
        "pagamento.html",
        {
            "ativo": "pagamentos",
            "agendamentos": agendamentos,
            "pagamentos": pagamentos,
            "valor_consulta": VALOR_CONSULTA,
            "formas_pagamento": FORMAS_PAGAMENTO_PACIENTE,
        }
    )


class AgendarConsultaForm(EscolhaEspecialidadeForm):
    """Cadastro de consulta pela recepção: paciente + especialidade + data.
    O médico livre da especialidade é escolhido automaticamente."""

    paciente = forms.ModelChoiceField(queryset=func_django.objects.order_by("nome"), label="Paciente")
    field_order = ["paciente", "tipo", "especialidade", "data_hora"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["paciente"].label_from_instance = rotulo

    def save(self):
        dados = self.cleaned_data
        with transaction.atomic():
            # trava a linha do médico: duas recepcionistas não marcam o mesmo horário ao mesmo tempo
            list(Medico.objects.select_for_update().filter(pk=dados["medico"].pk))
            if medico_ocupado(dados["medico"], dados["data_hora"]):
                raise ConflitoDeHorario("Esse horário acabou de ser preenchido. Escolha outro horário.")
            return Agendamento.objects.create(
                paciente=dados["paciente"], medico=dados["medico"],
                data_hora=dados["data_hora"], status=obter_status(NOMES_CONFIRMADA), tipo=dados["tipo"],
            )


RECURSOS["consultas"]["form"] = AgendarConsultaForm


class AceitarConsultaForm(forms.Form):
    """A recepção confere a disponibilidade e define médico e horário."""

    medico = forms.ModelChoiceField(queryset=Medico.objects.none(), label="Médico")
    horario = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"), label="Horário da consulta")

    def __init__(self, *args, agendamento, **kwargs):
        super().__init__(*args, **kwargs)
        self.agendamento = agendamento
        especialidades = MedicoEspecialidade.objects.filter(medico=agendamento.medico).values("especialidade_id")
        self.fields["medico"].queryset = Medico.objects.filter(
            Q(pk=agendamento.medico_id) | Q(ativo=True, medicoespecialidade__especialidade__in=especialidades)
        ).distinct().order_by("nome")
        self.fields["medico"].label_from_instance = rotulo
        self.fields["medico"].initial = agendamento.medico_id

    def clean(self):
        dados = super().clean()
        medico, hora = dados.get("medico"), dados.get("horario")
        if medico and hora:
            quando = combinar(data_local(self.agendamento.data_hora), hora)
            if quando <= agora_como(quando):
                self.add_error("horario", "Esse horário já passou.")
            elif medico_ocupado(medico, quando, ignorar_pk=self.agendamento.pk):
                self.add_error("horario", "Esse médico já tem consulta nesse horário. Escolha outro horário ou outro médico.")
            elif not medico_atende_em(medico, quando):
                self.add_error("horario", "Esse médico não atende nesse dia/horário (veja \"Horários dos médicos\"). Escolha outro horário ou outro médico.")
            else:
                dados["quando"] = quando
        return dados


@login_requerido
def aceitar_consulta(request, pk):
    exigir(request, "consultas", "aceitar")
    ag = get_object_or_404(Agendamento.objects.select_related("status", "medico", "paciente"), pk=pk)
    if not eh_status(ag, NOMES_SOLICITADA):
        messages.warning(request, "Esta solicitação já foi respondida.")
        return redirect("lista", recurso="consultas")

    form = AceitarConsultaForm(request.POST or None, agendamento=ag)
    if request.method == "POST" and form.is_valid():
        medico, quando = form.cleaned_data["medico"], form.cleaned_data["quando"]
        with transaction.atomic():
            list(Medico.objects.select_for_update().filter(pk=medico.pk))
            if medico_ocupado(medico, quando, ignorar_pk=ag.pk):
                messages.error(request, "Esse horário acabou de ser preenchido. Escolha outro horário.")
                return redirect("aceitar_consulta", pk=ag.pk)
            ag.medico = medico
            ag.data_hora = quando
            ag.status = obter_status(NOMES_CONFIRMADA)
            ag.save(update_fields=["medico", "data_hora", "status"])
        registrar_auditoria(request, "consulta_aceita", f"id={ag.pk}")
        messages.success(request, "Consulta confirmada com horário e médico definidos.")
        return redirect("lista", recurso="consultas")

    dia = data_local(ag.data_hora)
    return render(request, "form.html", {
        "form": form, "recurso": "consultas", "ativo": "consultas",
        "titulo": f"Aceitar {ag.tipo.lower()} de {ag.paciente.nome or ag.paciente.cpf} em {dia:%d/%m/%Y}",
        "botao": "Confirmar consulta", "voltar": reverse("lista", args=["consultas"]),
    })


def cadastro_publico(request):
    if request.session.get("username"):
        return redirect("dashboard")

    if request.method == "GET":
        return render(request, "cadastro.html")

    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip().lower()
    senha = request.POST.get("senha", "")
    confirmar_senha = request.POST.get("confirmar_senha", "")

    cpf = somente_digitos(request.POST.get("cpf", ""))
    nome = request.POST.get("nome", "").strip()
    telefone = somente_digitos(request.POST.get("telefone", ""))
    nascimento = request.POST.get("data_nascimento", "").strip()

    dados = {
        "username": username,
        "email": email,
        "cpf": cpf,
        "nome": nome,
        "telefone": telefone,
        "data_nascimento": nascimento,
    }

    def retornar_erro(texto):
        messages.error(request, texto)
        return render(request, "cadastro.html", {"dados": dados})

    # Username
    if not validar_nome(username):
        return retornar_erro("Nome de usuário inválido!")

    if len(username) > 10:
        return retornar_erro("O usuário deve possuir no máximo 10 caracteres!")

    if Usuario.objects.filter(username__iexact=username).exists():
        return retornar_erro("Nome de usuário já cadastrado!")

    # E-mail
    if not validar_email(email):
        return retornar_erro("E-mail inválido!")

    if len(email) > 50:
        return retornar_erro("O e-mail deve possuir no máximo 50 caracteres!")

    if Usuario.objects.filter(email__iexact=email).exists():
        return retornar_erro("E-mail já cadastrado!")

    # Senha
    if not validar_senha(senha):
        return retornar_erro("Senha inválida! Verifique os requisitos mínimos.")

    if senha != confirmar_senha:
        return retornar_erro("As senhas não coincidem!")

    # Dados do paciente
    if not cpf_valido(cpf):
        return retornar_erro("Informe um CPF válido com 11 números!")

    if not validar_nome(nome):
        return retornar_erro("Nome completo inválido!")

    if len(telefone) not in (10, 11):
        return retornar_erro("Informe um telefone válido com DDD!")

    if func_django.objects.filter(cpf=cpf).exists():
        return retornar_erro(
            "Este CPF já está cadastrado! Se você já foi atendido(a) na clínica, "
            "peça à recepção para criar o seu acesso."
        )

    try:
        data_nascimento = dt.date.fromisoformat(nascimento)
    except ValueError:
        return retornar_erro("Data de nascimento inválida!")

    if data_nascimento >= hoje_local():
        return retornar_erro("A data de nascimento deve ser anterior à data atual!")

    # Perfil fixo para cadastros públicos
    perfil = obter_perfil_paciente()

    if not perfil:
        return retornar_erro("Perfil Paciente não encontrado no banco de dados!")

    # Hash da senha
    salt = secrets.token_bytes(16)

    senha_hash = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt,
        ITERACOES
    ).hex()

    try:
        with transaction.atomic():

            # Cria os dados pessoais do paciente.
            paciente = func_django.objects.create(
                cpf=cpf,
                nome=nome,
                telefone=telefone,
                data_nascimento=data_nascimento,
            )

            # Cria a conta vinculada ao paciente.
            Usuario.objects.create(
                username=username,
                email=email,
                senha_hash=senha_hash,
                salt=salt.hex(),
                id_perfil=perfil,
                paciente=paciente,
                medico=None,
            )

    except IntegrityError:
        return retornar_erro(
            "Não foi possível cadastrar. Verifique se os dados já existem."
        )

    except Exception:
        logging.getLogger(__name__).exception("Falha no cadastro público")
        return retornar_erro(
            "Ocorreu um erro ao criar sua conta. Tente novamente."
        )

    registrar_auditoria(request, "cadastro_publico", f"cpf={cpf}")
    messages.success(
        request,
        "Conta criada com sucesso! Agora você pode entrar."
    )

    return redirect("login")


@login_requerido
def detalhe_paciente(request, cpf):

    perfil = request.session.get("perfil")
    perfil_chave = chave_perfil(perfil)

    # Paciente só pode acessar a própria ficha
    if perfil_chave == _n(PERFIL_PACIENTE):

        cpf_usuario = cpf_da_sessao(request)

        if not cpf_usuario or cpf_usuario != cpf:
            raise PermissionDenied

    else:
        exigir(request, "pacientes", "ver")

    paciente = get_object_or_404(
        pacientes_visiveis(request).select_related("medico"),
        cpf=cpf
    )

    # Cada seção segue a mesma regra de visibilidade das listagens: a recepção vê
    # agenda e financeiro, mas NÃO o conteúdo clínico; o médico vê só o que é dele.
    agendamentos = list(
        consultas_visiveis(request).filter(paciente_id=cpf)
        .select_related("medico", "status").order_by("-data_hora")
    )
    for a in agendamentos:
        a.horario_a_definir = eh_status(a, NOMES_SOLICITADA)

    pode_ver_prontuarios = "ver" in acoes_do_perfil(perfil, "prontuarios")
    prontuarios = []
    if pode_ver_prontuarios:
        prontuarios = list(
            queryset_visivel(request, "prontuarios").filter(paciente_id=cpf)
            .select_related("medico").order_by("-id_prontuario")
        )
    alergias = list(Alergia.objects.filter(paciente_id=cpf).order_by("descricao"))

    pode_ver_financeiro = "ver" in acoes_do_perfil(perfil, "pagamentos")
    pagamentos = []
    if pode_ver_financeiro:
        pagamentos = list(
            Pagamento.objects.filter(agendamento__paciente_id=cpf)
            .select_related("agendamento", "status_pagamento").order_by("-data_pagamento")
        )

    registrar_auditoria(request, "ver_paciente", f"cpf={cpf}")

    return render(request, "paciente_detalhe.html", {
        "paciente": paciente,
        "agendamentos": agendamentos,
        "prontuarios": prontuarios,
        "alergias": alergias,
        "pagamentos": pagamentos,
        "pode_ver_financeiro": pode_ver_financeiro,
        "pode_ver_prontuarios": pode_ver_prontuarios,
        "pode_gerir_alergia": "alergia" in acoes_do_perfil(perfil, "pacientes"),
        "pode_editar": "editar" in acoes_do_perfil(perfil, "pacientes"),
        "total_consultas": sum(1 for a in agendamentos if (a.tipo or "").lower() == "consulta"),
        "total_exames": sum(1 for a in agendamentos if (a.tipo or "").lower() == "exame"),
        "total_prontuarios": len(prontuarios),
        "total_alergias": len(alergias),
    })


@login_requerido
@require_POST
@login_requerido
@require_POST
def adicionar_alergia(request, cpf):

    perfil = chave_perfil(request.session.get("perfil"))

    # PACIENTE: só pode cadastrar alergias no próprio CPF
    if perfil == _n(PERFIL_PACIENTE):

        cpf_usuario = cpf_da_sessao(request)

        if not cpf_usuario or cpf_usuario != cpf:
            raise PermissionDenied

        paciente = get_object_or_404(
            func_django,
            cpf=cpf_usuario
        )

    # DEMAIS PERFIS: continuam usando as permissões existentes
    else:
        exigir(request, "pacientes", "alergia")

        paciente = get_object_or_404(
            pacientes_visiveis(request),
            cpf=cpf
        )

    descricao = request.POST.get("descricao", "").strip()

    if not descricao:
        messages.error(request, "Informe a descrição da alergia.")

    elif len(descricao) > 300:
        messages.error(
            request,
            "A descrição deve ter no máximo 300 caracteres."
        )

    elif Alergia.objects.filter(
        paciente=paciente,
        descricao__iexact=descricao
    ).exists():
        messages.warning(
            request,
            "Essa alergia já está cadastrada para o paciente."
        )

    else:
        alergia = Alergia.objects.create(
            paciente=paciente,
            descricao=descricao
        )

        registrar_auditoria(
            request,
            "alergia_adicionada",
            f"cpf={cpf} id={alergia.pk}"
        )

        messages.success(
            request,
            "Alergia cadastrada com sucesso."
        )

    return redirect("detalhe_paciente", cpf=cpf)


@login_requerido
@require_POST
def excluir_alergia(request, cpf, pk):

    perfil = chave_perfil(request.session.get("perfil"))
    eh_paciente = perfil == _n(PERFIL_PACIENTE)

    if eh_paciente:
        # O paciente só pode excluir alergias do próprio cadastro
        cpf_usuario = cpf_da_sessao(request)

        if not cpf_usuario or cpf_usuario != cpf:
            raise PermissionDenied

        paciente = get_object_or_404(
            func_django,
            cpf=cpf_usuario
        )

    else:
        exigir(request, "pacientes", "alergia")

        paciente = get_object_or_404(
            pacientes_visiveis(request),
            cpf=cpf
        )

    alergia = get_object_or_404(
        Alergia,
        id_alergias=pk,
        paciente_id=paciente.cpf
    )

    alergia.delete()

    registrar_auditoria(
        request,
        "alergia_removida",
        f"cpf={cpf} id={pk}"
    )

    messages.success(request, "Alergia removida com sucesso.")

    if eh_paciente:
        return redirect("dashboard")

    return redirect("detalhe_paciente", cpf=cpf)



def atalhos_do_perfil(perfil):
    """Botões de acesso rápido do painel: só as telas que o perfil pode ver."""
    atalhos = []
    for recurso, cfg in RECURSOS.items():
        if "ver" not in acoes_do_perfil(perfil, recurso):
            continue
        url = reverse("financeiro") if recurso == "pagamentos" else reverse("lista", args=[recurso])
        atalhos.append({"titulo": cfg["titulo"], "url": url})
    return atalhos


@login_requerido
def dashboard(request):
    perfil = request.session.get("perfil")
    perfil_chave = chave_perfil(perfil)

    contexto = {
        "ativo": "dashboard",
        "perfil": perfil,
        "mostrar_area_paciente": False,
        "paciente_nao_vinculado": False,
        "paciente": None,
        "agendamentos": [],
        "proxima_consulta": None,
        "prontuarios": [],
        "alergias": [],
        "pagamentos": [],
        # None = "não se aplica a este perfil" (o template só mostra o que não for None)
        "consultas_hoje": None,
        "proximas_consultas": [],
        "solicitacoes_pendentes": None,
        "atalhos": atalhos_do_perfil(perfil),
        "total_pacientes": None,
        "total_medicos": None,
        "total_consultas": None,
        "mostrar_suporte": True,
    }
    agora = timezone.now() if settings.USE_TZ else dt.datetime.now()

    # --------------------------------------------------
    # ÁREA DO PACIENTE
    # --------------------------------------------------
    if perfil_chave == _n(PERFIL_PACIENTE):

        contexto["mostrar_area_paciente"] = True

        cpf = cpf_da_sessao(request)

        paciente = (
            func_django.objects.filter(cpf=cpf).first()
            if cpf else None
        )

        if not paciente:
            contexto["paciente_nao_vinculado"] = True
            return render(request, "dashboard.html", contexto)

        agendamentos = list(
            Agendamento.objects
            .filter(paciente=paciente)
            .select_related("medico", "status")
            .order_by("-data_hora")
        )
        for a in agendamentos:
            a.horario_a_definir = eh_status(a, NOMES_SOLICITADA)

        prontuarios = (
            Prontuario.objects
            .filter(paciente=paciente)
            .select_related("medico")
            .order_by("-id_prontuario")
        )

        alergias = (
            Alergia.objects
            .filter(paciente=paciente)
            .order_by("descricao")
        )

        pagamentos = (
            Pagamento.objects
            .filter(agendamento__paciente=paciente)
            .select_related("agendamento", "status_pagamento")
            .order_by("-data_pagamento")
        )

        proxima_consulta = next(
            (
                a for a in sorted(agendamentos, key=lambda x: x.data_hora)
                if a.data_hora >= agora
                and not eh_status(a, NOMES_CANCELADA)
                and not eh_status(a, NOMES_SOLICITADA)
            ),
            None,
        )

        contexto.update({
            "paciente": paciente,
            "agendamentos": agendamentos,
            "consultas": agendamentos,
            "proxima_consulta": proxima_consulta,
            "prontuarios": prontuarios,
            "alergias": alergias,
            "pagamentos": pagamentos,
            "pode_gerir_alergia": True,
        })

        return render(request, "dashboard.html", contexto)

    # --------------------------------------------------
    # ÁREA DO MÉDICO
    # --------------------------------------------------
    if perfil_chave == _n(PERFIL_MEDICO):

        # mesma regra da listagem: só o que a recepção já aceitou, sem cancelados
        consultas = (
            consultas_visiveis(request)
            .exclude(filtro_status(NOMES_CANCELADA))
            .select_related("paciente", "status")
        )
        hoje = hoje_local()

        contexto.update({
            "consultas": consultas,
            "consultas_hoje": consultas.filter(data_hora__date=hoje).count(),
            "total_consultas": consultas.count(),
            "proximas_consultas": list(
                consultas.filter(data_hora__gte=agora).order_by("data_hora")[:8]
            ),
        })

    # --------------------------------------------------
    # ADMINISTRADOR E RECEPCIONISTA
    # --------------------------------------------------
    else:

        contexto.update({
            "total_pacientes": func_django.objects.count(),
            "total_medicos": Medico.objects.filter(ativo=True).count(),
            "total_consultas": Agendamento.objects.count(),
            "solicitacoes_pendentes": (
                Agendamento.objects
                .filter(filtro_status(NOMES_SOLICITADA))
                .count()
                if "aceitar" in acoes_do_perfil(perfil, "consultas") else None
            ),
        })

    return render(request, "dashboard.html", contexto)

# ==================================================
# SUPORTE
# ==================================================

def _usuario_do_root():
    """O root (administrador geral) não existe na tabela de usuários. Para poder assinar
    respostas de suporte, usa (ou cria uma única vez) um registro dele, sem senha utilizável."""
    existente = Usuario.objects.filter(username__iexact="root").first()
    if existente:
        return existente

    perfil = next(
        (p for p in Perfil.objects.all() if chave_perfil(p.nome_perfil) == _n("Administrador")),
        None,
    ) or Perfil.objects.order_by("id_perfil").first()
    if perfil is None:
        raise Http404("Cadastre o perfil Administrador antes de usar o suporte com o root.")

    salt = secrets.token_hex(16)
    try:
        with transaction.atomic():
            return Usuario.objects.create(
                username="root", email="root@clinica.local", salt=salt,
                senha_hash=gerar_hash(secrets.token_urlsafe(32), salt), id_perfil=perfil,
            )
    except IntegrityError:
        # outra requisição criou o registro ao mesmo tempo (ex.: clique duplo)
        existente = Usuario.objects.filter(username__iexact="root").first()
        if existente:
            return existente
        raise


def usuario_logado(request):
    username = request.session["username"]
    usuario = Usuario.objects.filter(username=username).first()
    if usuario is None and chave_perfil(request.session.get("perfil")) == _n(PERFIL_ROOT):
        usuario = _usuario_do_root()
    if usuario is None:
        raise Http404("Usuário não encontrado.")
    return usuario


def equipe_suporte(request):
    perfil = chave_perfil(request.session.get("perfil"))

    return perfil in {
        _n(PERFIL_ROOT),
        _n("Administrador"),
        _n(PERFIL_RECEPCIONISTA),
    }


@login_requerido
def abrir_chamado(request):
    if chave_perfil(request.session.get("perfil")) != _n(PERFIL_PACIENTE):
        raise PermissionDenied

    usuario = usuario_logado(request)

    if not usuario.paciente_id:
        messages.error(
            request,
            "Sua conta ainda não está vinculada a um paciente."
        )
        return redirect("dashboard")

    if request.method == "POST":
        form = ChamadoSuporteForm(request.POST)

        if form.is_valid():
            chamado = form.save(commit=False)
            chamado.usuario = usuario
            chamado.save()

            messages.success(
                request,
                "Seu chamado foi enviado com sucesso."
            )
            return redirect("chamados_suporte")
    else:
        form = ChamadoSuporteForm()

    return render(
        request,
        "suporte/abrir_chamado.html",
        {
            "form": form,
            "voltar": reverse("chamados_suporte"),
        }
    )


@login_requerido
def chamados_suporte(request):
    usuario = usuario_logado(request)

    if equipe_suporte(request):
        chamados = ChamadoSuporte.objects.select_related(
            "usuario"
        ).all()

    elif chave_perfil(request.session.get("perfil")) == _n(PERFIL_PACIENTE):
        chamados = ChamadoSuporte.objects.filter(
            usuario=usuario
        )

    else:
        raise PermissionDenied

    return render(
        request,
        "suporte/lista_chamados.html",
        {
            "chamados": chamados,
            "equipe_suporte": equipe_suporte(request),
        }
    )


@login_requerido
def detalhe_chamado(request, pk):

    equipe = equipe_suporte(request)

    if equipe:
        chamado = get_object_or_404(
            ChamadoSuporte.objects.select_related("usuario"),
            pk=pk
        )

    elif chave_perfil(request.session.get("perfil")) == _n(PERFIL_PACIENTE):

        usuario = usuario_logado(request)

        chamado = get_object_or_404(
            ChamadoSuporte.objects.select_related("usuario"),
            pk=pk,
            usuario=usuario
        )

    else:
        raise PermissionDenied

    return render(
        request,
        "suporte/detalhe_chamado.html",
        {
            "chamado": chamado,
            "respostas": chamado.respostas.select_related("usuario"),
            "equipe_suporte": equipe,
        }
    )

@login_requerido
@require_POST
def responder_chamado(request, pk):
    usuario = usuario_logado(request)

    if equipe_suporte(request):
        chamado = get_object_or_404(ChamadoSuporte, pk=pk)

    elif chave_perfil(request.session.get("perfil")) == _n(PERFIL_PACIENTE):
        chamado = get_object_or_404(
            ChamadoSuporte,
            pk=pk,
            usuario=usuario
        )

    else:
        raise PermissionDenied

    mensagem = request.POST.get("mensagem", "").strip()

    if not mensagem:
        messages.error(request, "Digite uma mensagem antes de enviar.")
        return redirect("detalhe_chamado", pk=pk)

    RespostaSuporte.objects.create(
        chamado=chamado,
        usuario=usuario,
        mensagem=mensagem
    )

    if chamado.status == "Aberto":
        chamado.status = "Em andamento"

    chamado.save()

    messages.success(request, "Resposta enviada com sucesso.")

    return redirect("detalhe_chamado", pk=pk)


@login_requerido
@require_POST
def atualizar_status_chamado(request, pk):
    if not equipe_suporte(request):
        raise PermissionDenied

    chamado = get_object_or_404(ChamadoSuporte, pk=pk)

    novo_status = request.POST.get("status")

    status_validos = [
        escolha[0]
        for escolha in ChamadoSuporte.STATUS_CHOICES
    ]

    if novo_status not in status_validos:
        messages.error(request, "Status inválido.")
        return redirect("detalhe_chamado", pk=pk)

    chamado.status = novo_status
    chamado.save()

    messages.success(request, "Status atualizado com sucesso.")

    return redirect("detalhe_chamado", pk=pk)

@login_requerido
@require_POST
@transaction.atomic
def registrar_pagamento_dinheiro(request, agendamento_id):
    # Somente a recepcionista pode registrar dinheiro em espécie.
    perfil = request.session.get("perfil")

    if chave_perfil(perfil) != _n(PERFIL_RECEPCIONISTA):
        messages.error(
            request,
            "Somente a recepcionista pode registrar dinheiro em espécie."
        )
        return redirect("dashboard")

    exigir(request, "pagamentos", "criar")

    agendamento = get_object_or_404(
        Agendamento.objects.select_related("status"),
        pk=agendamento_id
    )

    if _n(agendamento.tipo) != _n("Consulta"):
        messages.error(
            request,
            "O pagamento em dinheiro está disponível somente para consultas."
        )
        return redirect("lista", recurso="consultas")

    if (
        eh_status(agendamento, NOMES_SOLICITADA)
        or eh_status(agendamento, NOMES_CANCELADA)
    ):
        messages.error(
            request,
            "Não é possível registrar pagamento para esta consulta."
        )
        return redirect("lista", recurso="consultas")

    if pagamento_ativo_existe(agendamento):
        messages.warning(
            request,
            "Esta consulta já possui um pagamento registrado."
        )
        return redirect("lista", recurso="consultas")

    pagamento = Pagamento.objects.create(
        agendamento=agendamento,
        descricao="Pagamento de consulta em dinheiro",
        valor=VALOR_CONSULTA,
        forma_pagamento="Dinheiro",
        status_pagamento=obter_status_pagamento("Concluído"),
        data_pagamento=hoje_local()
    )
    registrar_auditoria(request, "pagamento_dinheiro", f"id={pagamento.pk}")

    messages.success(
        request,
        "Pagamento de R$ 60,00 em dinheiro registrado com sucesso."
    )

    return redirect("lista", recurso="consultas")

class ChamadoSuporteForm(forms.ModelForm):

    class Meta:
        model = ChamadoSuporte
        fields = ["assunto", "descricao"]

        labels = {
            "assunto": "Assunto",
            "descricao": "Descreva sua solicitação",
        }

        widgets = {
            "assunto": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex.: Problema ao solicitar consulta",
                "maxlength": 150,
            }),
            "descricao": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Explique detalhadamente o que aconteceu...",
                "rows": 5,
            }),
        }

    def clean_assunto(self):
        assunto = self.cleaned_data["assunto"].strip()

        if not assunto:
            raise ValidationError("Informe o assunto do chamado.")

        return assunto

    def clean_descricao(self):
        descricao = self.cleaned_data["descricao"].strip()

        if not descricao:
            raise ValidationError("Informe a descrição do chamado.")

        return descricao


@login_requerido
def abrir_chamado(request):

    username = request.session.get("username", "")

    usuario = Usuario.objects.filter(
        username__iexact=username
    ).first()

    if not usuario:
        messages.error(
            request,
            "Não foi possível localizar sua conta."
        )
        return redirect("dashboard")

    if request.method == "POST":

        form = ChamadoSuporteForm(request.POST)

        if form.is_valid():
            chamado = form.save(commit=False)
            chamado.usuario = usuario
            chamado.save()

            messages.success(
                request,
                "Seu chamado foi aberto com sucesso!"
            )

            return redirect("dashboard")

    else:
        form = ChamadoSuporteForm()

    return render(
        request,
        "suporte/abrir_chamado.html",
        {
            "form": form,
            "ativo": "suporte",
            "titulo": "Abrir chamado de suporte",
        }
    )

@login_requerido
def listar_chamados(request):

    perfil = chave_perfil(request.session.get("perfil"))

    perfis_autorizados = {
        _n(PERFIL_ROOT),
        _n("Administrador"),
        _n(PERFIL_RECEPCIONISTA),
    }

    if perfil not in perfis_autorizados:
        raise PermissionDenied

    chamados = (
        ChamadoSuporte.objects
        .select_related("usuario")
        .order_by("-data_abertura")
    )

    contexto = {
        "chamados": chamados,
        "total_chamados": chamados.count(),
        "total_abertos": chamados.filter(status="Aberto").count(),
        "total_andamento": chamados.filter(
            status="Em andamento"
        ).count(),
        "total_resolvidos": chamados.filter(
            status="Resolvido"
        ).count(),
        "ativo": "suporte",
        "titulo": "Central de chamados",
    }

    return render(
        request,
        "suporte/listar_chamados.html",
        contexto
    )