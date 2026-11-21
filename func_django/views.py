import datetime as dt
import hashlib
import hmac
import os
import secrets
import unicodedata
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
    Agendamento, Especialidade, HorarioMedico, Medico, MedicoEspecialidade, Pagamento,
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
        for nome_campo in ("id_perfil", "medico", "paciente"):
            if nome_campo in self.fields:
                self.fields[nome_campo].label_from_instance = rotulo
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
        nome = chave_perfil(perfil.nome_perfil) if perfil else ""

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
    "vinculos": {
        "model": MedicoEspecialidade, "titulo": "Especialidades dos médicos",
        "colunas": [("medico", "Médico"), ("especialidade", "Especialidade")],
        "busca": ["medico__nome", "especialidade__nome"],
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
    texto = unicodedata.normalize("NFKD", (perfil or "").strip().casefold())
    return "".join(c for c in texto if not unicodedata.combining(c))


PERFIL_MEDICO = "Médico"
PERFIL_PACIENTE = "Paciente"

PERMISSOES = {
    "Administrador": {"*": {"ver", "criar", "excluir", "aceitar"}},
    "ADMIN GERAL": {"*": {"ver", "criar", "excluir", "aceitar"}},  # usuário root
    "Recepcionista": {
        "pacientes": {"ver", "criar", "excluir"},
        "consultas": {"ver", "criar", "excluir", "aceitar"},
        "pagamentos": {"ver", "criar", "excluir"},
        "medicos": {"ver"},
        "especialidades": {"ver"},
        "horarios": {"ver"},
        "vinculos": {"ver"},
    },
    PERFIL_MEDICO: {
        "pacientes": {"ver"},
        "consultas": {"ver"},
        "prontuarios": {"ver", "criar"},
    },
    # paciente só consulta os próprios dados (o filtro está em aplicar_escopo)
    PERFIL_PACIENTE: {
        "consultas": {"ver", "solicitar"},
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
    for prefixo, chave in PREFIXOS.items():
        if n.startswith(prefixo):
            return chave
    return n


def acoes_do_perfil(perfil, recurso):
    perms = PERMISSOES.get(chave_perfil(perfil), {})
    return perms.get("*", perms.get(recurso, set()))


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
    if chave_perfil(perfil) == _n(PERFIL_MEDICO) and crm:
        consultas_hoje = Agendamento.objects.filter(
            medico=crm, data_hora__date=timezone.localdate()
        ).count()

    solicitacoes_pendentes = None
    if "aceitar" in acoes_do_perfil(perfil, "consultas"):
        solicitacoes_pendentes = Agendamento.objects.filter(filtro_status(NOMES_SOLICITADA)).count()

    mostrar_proxima = chave_perfil(perfil) == _n(PERFIL_PACIENTE)
    proxima_consulta = None
    cpf = cpf_da_sessao(request)
    if mostrar_proxima and cpf:
        proxima_consulta = (
            Agendamento.objects.select_related("medico")
            .filter(paciente=cpf, data_hora__gte=timezone.now())
            .order_by("data_hora").first()
        )

    return render(request, "dashboard.html", {
        "ativo": "dashboard", "atalhos": atalhos, "consultas_hoje": consultas_hoje,
        "mostrar_proxima": mostrar_proxima, "proxima_consulta": proxima_consulta,
        "solicitacoes_pendentes": solicitacoes_pendentes,
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


@login_requerido
def lista(request, recurso):
    cfg = get_recurso(recurso)
    exigir(request, recurso, "ver")
    acoes = acoes_do_perfil(request.session.get("perfil"), recurso)
    qs = cfg["model"].objects.all()

    qs = aplicar_escopo(request, cfg, qs)
    if recurso == "consultas" and chave_perfil(request.session.get("perfil")) == _n(PERFIL_MEDICO):
        qs = qs.exclude(filtro_status(NOMES_SOLICITADA))  # médico vê só o que a recepção já aceitou
    relacionados = [c for c, _ in cfg["colunas"] if cfg["model"]._meta.get_field(c).is_relation]
    if relacionados:
        qs = qs.select_related(*relacionados)

    q = request.GET.get("q", "").strip()
    if q and cfg["busca"]:
        filtro = Q()
        for campo in cfg["busca"]:
            filtro |= Q(**{f"{campo}__icontains": q})
        qs = qs.filter(filtro)

    campos = [c for c, _ in cfg["colunas"]]
    linhas = [
        {"pk": obj.pk, "valores": [formatar(getattr(obj, c)) for c in campos],
         "pendente": recurso == "consultas" and eh_status(obj, NOMES_SOLICITADA)}
        for obj in qs
    ]
    return render(request, "lista.html", {
        "recurso": recurso, "titulo": cfg["titulo"], "ativo": recurso,
        "colunas": [r for _, r in cfg["colunas"]], "linhas": linhas, "q": q,
        "pode_criar": cfg.get("criar", True) and "criar" in acoes,
        "pode_excluir": "excluir" in acoes,
        "pode_aceitar": recurso == "consultas" and "aceitar" in acoes,
        "pode_solicitar": recurso == "consultas" and "solicitar" in acoes,
        "pendentes": (Agendamento.objects.filter(filtro_status(NOMES_SOLICITADA)).count()
                      if recurso == "consultas" and "aceitar" in acoes else 0),
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
        "pode_pagar": "pagar" in acoes,
        "eh_paciente": chave_perfil(request.session.get("perfil")) == _n(PERFIL_PACIENTE),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status_pagamento"].label_from_instance = rotulo

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


# ==================================================
# SOLICITAÇÃO E ACEITE DE CONSULTAS
# ==================================================
# Nomes aceitos na tabela status_agendamento (se não existir, o primeiro é criado)
NOMES_SOLICITADA = ("Solicitada", "Solicitado")
NOMES_CONFIRMADA = ("Agendada", "Agendado", "Confirmada", "Confirmado")
NOMES_CANCELADA = ("Cancelada", "Cancelado", "Recusada", "Recusado")


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


class SolicitarConsultaForm(forms.Form):
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
                # primeiro médico ativo da especialidade que esteja livre nesse horário
                ocupados = (Agendamento.objects.filter(data_hora=quando)
                            .exclude(filtro_status(NOMES_CANCELADA)).values("medico_id"))
                medico = (Medico.objects.filter(ativo=True, medicoespecialidade__especialidade=esp)
                          .exclude(pk__in=ocupados).order_by("nome").first())
                if medico is None:
                    self.add_error("data_hora", f"Nenhum médico de {esp.nome} disponível nesse horário. Escolha outro.")
                else:
                    dados["medico"] = medico
        return dados


@login_requerido
def solicitar_consulta(request):
    exigir(request, "consultas", "solicitar")
    cpf = cpf_da_sessao(request)
    paciente = func_django.objects.filter(cpf=cpf).first() if cpf else None
    if paciente is None:
        messages.error(request, "Seu usuário não está vinculado a um paciente. Procure a recepção.")
        return redirect("lista", recurso="consultas")

    form = SolicitarConsultaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        Agendamento.objects.create(
            paciente=paciente, medico=form.cleaned_data["medico"],
            data_hora=form.cleaned_data["data_hora"], status=obter_status(NOMES_SOLICITADA),
        )
        messages.success(request, f"Solicitação enviada para {form.cleaned_data['especialidade'].nome} (Dr(a). {form.cleaned_data['medico'].nome}). Aguarde a confirmação da recepção.")
        return redirect("lista", recurso="consultas")
    return render(request, "form.html", {
        "form": form, "recurso": "consultas", "ativo": "consultas",
        "titulo": "Solicitar consulta", "botao": "Enviar solicitação",
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
        ocupado = (
            Agendamento.objects.filter(medico=ag.medico, data_hora=ag.data_hora).exclude(pk=ag.pk)
            .exclude(filtro_status(NOMES_CANCELADA)).exclude(filtro_status(NOMES_SOLICITADA)).exists()
        )
        if ocupado:
            messages.error(request, "Não foi possível aceitar: o médico já tem consulta marcada nesse horário.")
        else:
            ag.status = obter_status(NOMES_CONFIRMADA)
            ag.save(update_fields=["status"])
            messages.success(request, "Consulta aceita e agendada.")
    else:
        ag.status = obter_status(NOMES_CANCELADA)
        ag.save(update_fields=["status"])
        messages.success(request, "Solicitação recusada.")
    return redirect("lista", recurso="consultas")


# ==================================================
# PAGAMENTO PELO PACIENTE
# ==================================================

class PagamentoPacienteForm(forms.Form):
    agendamento = AgendamentoChoice(queryset=Agendamento.objects.none(), label="Consulta a pagar")
    valor = forms.DecimalField(
        min_value=Decimal("0.01"), max_digits=10, decimal_places=2, localize=True, label="Valor (R$)",
        error_messages={"min_value": "O valor deve ser maior que zero."},
    )
    forma_pagamento = forms.ChoiceField(choices=[(f, f) for f in FORMAS], label="Forma de pagamento")

    def __init__(self, *args, cpf=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agendamento"].queryset = (
            Agendamento.objects.select_related("paciente", "status").filter(paciente=cpf)
            .exclude(filtro_status(NOMES_CANCELADA)).exclude(filtro_status(NOMES_SOLICITADA))
            .order_by("-data_hora")
        )


@login_requerido
def pagar(request):
    exigir(request, "pagamentos", "pagar")
    cpf = cpf_da_sessao(request) or None
    form = PagamentoPacienteForm(request.POST or None, cpf=cpf)
    if request.method == "POST" and form.is_valid():
        ag = form.cleaned_data["agendamento"]
        pendente = (StatusPagamento.objects.filter(descricao__iexact="Pendente").first()
                    or StatusPagamento.objects.create(descricao="Pendente"))
        Pagamento.objects.create(
            agendamento=ag, descricao=f"Consulta de {formatar(ag.data_hora)}",
            valor=form.cleaned_data["valor"], forma_pagamento=form.cleaned_data["forma_pagamento"],
            status_pagamento=pendente, data_pagamento=dt.date.today(),
        )
        messages.success(request, "Pagamento enviado! A recepção irá confirmar o recebimento.")
        return redirect("financeiro")
    return render(request, "form.html", {
        "form": form, "recurso": "pagamentos", "ativo": "pagamentos",
        "titulo": "Realizar pagamento", "botao": "Enviar pagamento", "voltar": reverse("financeiro"),
    })


@login_requerido
@require_POST
def confirmar_pagamento(request, pk):
    exigir(request, "pagamentos", "criar")
    pag = get_object_or_404(Pagamento.objects.select_related("status_pagamento"), pk=pk)
    if _n(pag.status_pagamento.descricao) == "pendente":
        pag.status_pagamento = (StatusPagamento.objects.filter(descricao__iexact="Concluído").first()
                                or StatusPagamento.objects.create(descricao="Concluído"))
        pag.save(update_fields=["status_pagamento"])
        messages.success(request, "Pagamento confirmado.")
    else:
        messages.warning(request, "Este pagamento não está pendente.")
    return redirect("financeiro")