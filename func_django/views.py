import hashlib
import hmac
import os
import secrets
from decimal import Decimal
from functools import wraps

from django import forms
from django.contrib import messages
from django.db import models
from django.db.models import Count, ProtectedError, Q, Sum
from django.forms import modelform_factory
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.utils import timezone
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from sistema_clinica.funcionalidades.regex import validar_email, validar_nome
from func_django.models import (
    Agendamento, Especialidade, HorarioMedico, Medico, Pagamento,
    Prontuario, StatusPagamento, Usuario, func_django,
)

ITERACOES = 600000  # igual ao verificar_usuario.py


def gerar_hash(senha, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt_hex), ITERACOES).hex()


CAMPOS_USUARIO = ["username", "email", "id_perfil", "medico"]
if any(f.name == "paciente" for f in Usuario._meta.get_fields()):
    CAMPOS_USUARIO.append("paciente")


class UsuarioForm(forms.ModelForm):
    """Mesmas regras do cadastro_usuarios.py do terminal."""

    senha = forms.CharField(widget=forms.PasswordInput, min_length=8, label="Senha (mínimo 8 caracteres)")

    class Meta:
        model = Usuario
        fields = CAMPOS_USUARIO
        labels = {"username": "Nome de usuário", "id_perfil": "Perfil",
                  "medico": "Médico (obrigatório para o perfil Médico)",
                  "paciente": "Paciente (obrigatório para o perfil Paciente)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # só médicos ativos que ainda não têm usuário
        self.fields["medico"].queryset = (
            Medico.objects.filter(ativo=True).order_by("nome")
            .exclude(crm__in=Usuario.objects.filter(medico__isnull=False).values_list("medico_id", flat=True))
        )
        if "paciente" in self.fields:
            self.fields["paciente"].queryset = func_django.objects.exclude(
                cpf__in=Usuario.objects.filter(paciente__isnull=False).values_list("paciente_id", flat=True)
            )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not validar_nome(username):
            raise ValidationError("Use apenas letras e espaços (mínimo de 3 caracteres).")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not validar_email(email):
            raise ValidationError("E-mail inválido.")
        if Usuario.objects.filter(email=email).exists():
            raise ValidationError("E-mail já cadastrado.")
        return email

    def clean(self):
        dados = super().clean()
        perfil = dados.get("id_perfil")
        nome = _n(perfil.nome_perfil) if perfil else ""

        if nome == _n(PERFIL_MEDICO):
            if not dados.get("medico"):
                self.add_error("medico", "Selecione o médico deste usuário (só aparecem médicos ativos sem usuário).")
        else:
            dados["medico"] = None

        if "paciente" in self.fields:
            if nome == _n(PERFIL_PACIENTE):
                if not dados.get("paciente"):
                    self.add_error("paciente", "Selecione o paciente deste usuário.")
            else:
                dados["paciente"] = None
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.salt = secrets.token_hex(16)  # igual a secrets.token_bytes(16).hex() do terminal
        usuario.senha_hash = gerar_hash(self.cleaned_data["senha"], usuario.salt)
        if commit:
            usuario.save()
        return usuario


# Cada recurso vira lista + cadastro + exclusão usando os mesmos 3 templates.
# colunas: (campo, rótulo) | busca: campos da pesquisa | criar: libera "Cadastrar"
# esconder: campos que nunca aparecem no formulário
RECURSOS = {
    "pacientes": {
        "model": func_django, "titulo": "Pacientes", "escopo": {"medico": "medico", "paciente": "cpf"},
        "colunas": [("cpf", "CPF"), ("nome", "Nome"), ("telefone", "Telefone"),
                    ("data_nascimento", "Nascimento"), ("medico", "Médico")],
        "busca": ["nome", "cpf"],
    },
    "medicos": {
        "model": Medico, "titulo": "Médicos",
        "colunas": [("crm", "CRM"), ("nome", "Nome"), ("telefone", "Telefone"), ("ativo", "Ativo")],
        "busca": ["nome", "crm"],
    },
    "especialidades": {
        "model": Especialidade, "titulo": "Especialidades",
        "colunas": [("nome", "Nome")],
        "busca": ["nome"],
    },
    "horarios": {
        "model": HorarioMedico, "titulo": "Horários dos médicos",
        "colunas": [("medico", "Médico"), ("dia_semana", "Dia"), ("hora_inicio", "Início"), ("hora_fim", "Fim")],
        "busca": ["medico__nome", "dia_semana"],
    },
    "consultas": {
        "model": Agendamento, "titulo": "Consultas", "escopo": {"medico": "medico", "paciente": "paciente"},
        "colunas": [("paciente", "Paciente"), ("medico", "Médico"), ("data_hora", "Data e hora"), ("status", "Status")],
        "busca": ["paciente__nome", "medico__nome"],
    },
    "prontuarios": {
        "model": Prontuario, "titulo": "Prontuários", "escopo": {"medico": "medico", "paciente": "paciente"},
        "colunas": [("paciente", "Paciente"), ("medico", "Médico"), ("diagnostico", "Diagnóstico")],
        "busca": ["paciente__nome", "medico__nome"],
    },
    "pagamentos": {
        "model": Pagamento, "titulo": "Financeiro",
        "colunas": [("agendamento", "Consulta"), ("descricao", "Descrição"), ("valor", "Valor"),
                    ("forma_pagamento", "Forma"), ("status_pagamento", "Status"), ("data_pagamento", "Data")],
        "busca": ["descricao"],
        "escopo": {"paciente": "agendamento__paciente"},
        "criar": False,
    },
    "usuarios": {
        "model": Usuario, "titulo": "Usuários",
        "colunas": [("username", "Usuário"), ("email", "E-mail"), ("id_perfil", "Perfil"), ("medico", "Médico")],
        "busca": ["username", "email"],
        "form": UsuarioForm,
        "esconder": ["senha_hash", "salt"],
    },
}


# ==================================================
# PERMISSÕES POR PERFIL
# ==================================================
# As chaves devem ser IGUAIS aos valores de Perfil.nome_perfil no banco
# (com acento e maiúsculas). "*" = todos os recursos.
# Ações: "ver", "criar", "excluir". Chave "pagamentos" = tela Financeiro.
def _n(perfil):
    return (perfil or "").strip().casefold()


PERFIL_MEDICO = "Médico"
PERFIL_PACIENTE = "Paciente"

PERMISSOES = {
    "Administrador": {"*": {"ver", "criar", "excluir"}},
    "ADMIN GERAL": {"*": {"ver", "criar", "excluir"}},  # usuário root
    "Recepcionista": {
        "pacientes": {"ver", "criar", "excluir"},
        "consultas": {"ver", "criar", "excluir"},
        "pagamentos": {"ver", "criar", "excluir"},
        "medicos": {"ver"},
        "especialidades": {"ver"},
        "horarios": {"ver"},
    },
    PERFIL_MEDICO: {
        "pacientes": {"ver"},
        "consultas": {"ver"},
        "prontuarios": {"ver", "criar"},
    },
    # paciente só consulta os próprios dados (o filtro está em aplicar_escopo)
    PERFIL_PACIENTE: {
        "pacientes": {"ver"},
        "consultas": {"ver"},
        "prontuarios": {"ver"},
        "pagamentos": {"ver"},
    },
}


PERMISSOES = {_n(k): v for k, v in PERMISSOES.items()}


def acoes_do_perfil(perfil, recurso):
    perms = PERMISSOES.get(_n(perfil), {})
    return perms.get("*", perms.get(recurso, set()))


def exigir(request, recurso, acao):
    if acao not in acoes_do_perfil(request.session.get("perfil"), recurso):
        raise PermissionDenied


def aplicar_escopo(request, cfg, qs):
    """Médico e paciente só enxergam registros ligados a eles."""
    perfil = request.session.get("perfil")
    if _n(perfil) == _n(PERFIL_MEDICO):
        chave, valor = "medico", request.session.get("crm")
    elif _n(perfil) == _n(PERFIL_PACIENTE):
        chave, valor = "paciente", request.session.get("cpf")
    else:
        return qs
    campo = cfg.get("escopo", {}).get(chave)
    if not campo or not valor:
        return qs.none()  # na dúvida, não mostra nada
    return qs.filter(**{campo: valor})


def get_recurso(recurso):
    if recurso not in RECURSOS:
        raise Http404
    return RECURSOS[recurso]


def login_requerido(view):
    @wraps(view)
    def interno(request, *args, **kwargs):
        if "username" not in request.session:
            return redirect("login")
        return view(request, *args, **kwargs)
    return interno


# Usuário administrador geral (igual ao do terminal). Em produção, defina estas
# variáveis de ambiente em vez de deixar a senha escrita no código.
ROOT_USER = os.environ.get("CLINICA_ROOT_USER", "root")
ROOT_SENHA = os.environ.get("CLINICA_ROOT_SENHA", "root@123")


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


def login_view(request):
    if request.method == "POST":
        ident = request.POST.get("identificador", "").strip().lower()
        senha = request.POST.get("senha", "")

        if ident == ROOT_USER.lower() and hmac.compare_digest(senha.encode(), ROOT_SENHA.encode()):
            abrir_sessao(request, "root", "", "ADMIN GERAL")
            return redirect("dashboard")

        usuario = (
            Usuario.objects.select_related("id_perfil")
            .filter(Q(email__iexact=ident) | Q(username__iexact=ident))
            .first()
        )
        if usuario and senha_confere(usuario, senha):
            abrir_sessao(
                request, usuario.username, usuario.email, usuario.id_perfil.nome_perfil,
                crm=usuario.medico_id or "",
                cpf=getattr(usuario, "paciente_id", "") or "",
            )
            return redirect("dashboard")
        messages.error(request, "E-mail ou senha incorretos.")
    return render(request, "login.html")


@require_POST
def logout_view(request):
    request.session.flush()
    return redirect("login")


@login_requerido
def dashboard(request):
    perfil = request.session.get("perfil")
    atalhos = []
    for rec, cfg in RECURSOS.items():
        if "ver" in acoes_do_perfil(perfil, rec):
            url = reverse("financeiro") if rec == "pagamentos" else reverse("lista", args=[rec])
            atalhos.append({"titulo": cfg["titulo"], "url": url})

    consultas_hoje = None
    crm = request.session.get("crm")
    if _n(perfil) == _n(PERFIL_MEDICO) and crm:
        consultas_hoje = Agendamento.objects.filter(
            medico=crm, data_hora__date=timezone.localdate()
        ).count()

    mostrar_proxima = _n(perfil) == _n(PERFIL_PACIENTE)
    proxima_consulta = None
    cpf = request.session.get("cpf")
    if mostrar_proxima and cpf:
        proxima_consulta = (
            Agendamento.objects.select_related("medico")
            .filter(paciente=cpf, data_hora__gte=timezone.now())
            .order_by("data_hora").first()
        )

    return render(request, "dashboard.html", {
        "ativo": "dashboard", "atalhos": atalhos, "consultas_hoje": consultas_hoje,
        "mostrar_proxima": mostrar_proxima, "proxima_consulta": proxima_consulta,
    })


def formatar(valor):
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if valor is None:
        return ""
    if isinstance(valor, (int, float, str)) or hasattr(valor, "year") or hasattr(valor, "hour"):
        return valor
    return str(valor)  # chaves estrangeiras usam o __str__ do model


@login_requerido
def lista(request, recurso):
    cfg = get_recurso(recurso)
    exigir(request, recurso, "ver")
    acoes = acoes_do_perfil(request.session.get("perfil"), recurso)
    qs = cfg["model"].objects.all()

    qs = aplicar_escopo(request, cfg, qs)

    q = request.GET.get("q", "").strip()
    if q and cfg["busca"]:
        filtro = Q()
        for campo in cfg["busca"]:
            filtro |= Q(**{f"{campo}__icontains": q})
        qs = qs.filter(filtro)

    campos = [c for c, _ in cfg["colunas"]]
    linhas = [
        {"pk": obj.pk, "valores": [formatar(getattr(obj, c)) for c in campos]}
        for obj in qs
    ]
    return render(request, "lista.html", {
        "recurso": recurso, "titulo": cfg["titulo"], "ativo": recurso,
        "colunas": [r for _, r in cfg["colunas"]], "linhas": linhas, "q": q,
        "pode_criar": cfg.get("criar", True) and "criar" in acoes,
        "pode_excluir": "excluir" in acoes,
    })


def _campo_form(campo, **kwargs):
    f = campo.formfield(**kwargs)
    if f is None:
        return None
    if isinstance(campo, models.DateTimeField):
        f.widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
    elif isinstance(campo, models.DateField):
        f.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    elif isinstance(campo, models.TimeField):
        f.widget = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
    return f


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
    form = Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cadastro salvo com sucesso.")
        return redirect("lista", recurso=recurso)
    return render(request, "form.html", {
        "form": form, "recurso": recurso, "ativo": recurso,
        "titulo": f"Cadastrar em {cfg['titulo'].lower()}",
        "voltar": reverse("lista", args=[recurso]),
    })


@login_requerido
@require_POST
def excluir(request, recurso, pk):
    cfg = get_recurso(recurso)
    exigir(request, recurso, "excluir")
    obj = get_object_or_404(cfg["model"], pk=pk)
    try:
        obj.delete()
        messages.success(request, "Registro excluído.")
    except ProtectedError:
        messages.error(request, "Não foi possível excluir: existem outros registros vinculados a este.")
    if recurso == "pagamentos":
        return redirect("financeiro")
    return redirect("lista", recurso=recurso)


# ==================================================
# FINANCEIRO (resumo + pagamentos)
# ==================================================

FORMAS = ["Dinheiro", "Pix", "Cartão", "Convênio"]
STATUS = ["Concluído", "Pendente", "Cancelado"]


@login_requerido
def financeiro(request):
    exigir(request, "pagamentos", "ver")
    acoes = acoes_do_perfil(request.session.get("perfil"), "pagamentos")
    base = aplicar_escopo(
        request, RECURSOS["pagamentos"],
        Pagamento.objects.select_related("agendamento__paciente", "status_pagamento"),
    )

    q = request.GET.get("q", "").strip()
    pagamentos = base
    if q:
        pagamentos = base.filter(
            Q(agendamento__paciente__nome__icontains=q)
            | Q(agendamento__paciente__cpf__icontains=q)
            | Q(descricao__icontains=q)
        )

    def soma(status):
        return Sum("valor", filter=Q(status_pagamento__descricao=status))

    # o resumo considera todos os pagamentos, mesmo com a busca ativa
    resumo = base.aggregate(
        recebido=soma("Concluído"), pendente=soma("Pendente"),
        cancelado=soma("Cancelado"), quantidade=Count("pk"),
    )
    for chave in ("recebido", "pendente", "cancelado"):
        resumo[chave] = resumo[chave] or Decimal("0")
    resumo["total"] = resumo["recebido"] + resumo["pendente"] + resumo["cancelado"]

    return render(request, "financeiro.html", {
        "ativo": "pagamentos", "resumo": resumo, "q": q,
        "pode_criar": "criar" in acoes, "pode_excluir": "excluir" in acoes,
        "pagamentos": pagamentos.order_by("-data_pagamento", "-id_pagamento"),
    })


class AgendamentoChoice(forms.ModelChoiceField):
    def label_from_instance(self, ag):
        return f"{ag.paciente.nome} ({ag.paciente.cpf}) - {ag.data_hora:%d/%m/%Y %H:%M}"


class PagamentoForm(forms.ModelForm):
    agendamento = AgendamentoChoice(
        queryset=Agendamento.objects.select_related("paciente").order_by("-data_hora"),
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

    class Meta:
        model = Pagamento
        fields = ["agendamento", "descricao", "valor", "forma_pagamento", "status_pagamento", "data_pagamento"]
        labels = {"descricao": "Descrição (consulta, exame, etc.)"}


@login_requerido
def novo_pagamento(request):
    exigir(request, "pagamentos", "criar")
    form = PagamentoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pagamento registrado com sucesso.")
        return redirect("financeiro")
    return render(request, "form.html", {
        "form": form, "recurso": "pagamentos", "ativo": "pagamentos",
        "titulo": "Registrar pagamento", "voltar": reverse("financeiro"),
    })