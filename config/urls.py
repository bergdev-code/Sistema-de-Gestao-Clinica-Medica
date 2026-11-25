
from django.contrib import admin
from django.urls import path
from func_django import views


urlpatterns = [
    path("admin/", admin.site.urls),
    
    # LOGIN COM GOOGLE
    path("google/entrar/", views.google_login, name="google_login"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path(
        "completar-cadastro/",
        views.completar_cadastro_google,
        name="completar_cadastro_google"
    ),

    # LOGIN E CADASTRO
    path("", views.login_view, name="login"),
    path("cadastro/", views.cadastro_publico, name="cadastro_publico"),
    path("sair/", views.logout_view, name="logout"),


    # PAINEL E CONTA
    path("painel/", views.dashboard, name="dashboard"),
    path("conta/", views.conta, name="conta"),

    # CONSULTAS
path("consultas/solicitar/", views.solicitar_consulta, name="solicitar_consulta"),

path("consultas/<int:pk>/aceitar/", views.aceitar_consulta, name="aceitar_consulta"),

path(
    "consultas/<int:pk>/recusar/",
    views.responder_consulta,
    {"acao": "recusar"},
    name="recusar_consulta"
),

path(
    "consultas/<int:pk>/cancelar/",
    views.cancelar_consulta,
    name="cancelar_consulta"
),

    # FINANCEIRO
    path("financeiro/", views.financeiro, name="financeiro"),
    path("financeiro/pagar/", views.pagar, name="pagar"),
    path("financeiro/<int:pk>/confirmar/", views.confirmar_pagamento, name="confirmar_pagamento"),
    path("financeiro/novo/", views.novo_pagamento, name="novo_pagamento"),
    path(
    "financeiro/pagamento/",
    views.pagar_consulta,
    name="pagar_consulta"
),

    # DETALHES E ALERGIAS DOS PACIENTES
    path("pacientes/<str:cpf>/", views.detalhe_paciente, name="detalhe_paciente"),
    path(
        "pacientes/<str:cpf>/alergias/adicionar/",
        views.adicionar_alergia,
        name="adicionar_alergia"
    ),
    path(
        "pacientes/<str:cpf>/alergias/<int:pk>/excluir/",
        views.excluir_alergia,
        name="excluir_alergia"
    ),

    # ROTAS GENÉRICAS SEMPRE NO FINAL
path("<slug:recurso>/", views.lista, name="lista"),
path("<slug:recurso>/novo/", views.novo, name="novo"),

path(
    "<slug:recurso>/<str:pk>/editar/",
    views.editar,
    name="editar"
),

path(
    "<slug:recurso>/<str:pk>/excluir/",
    views.excluir,
    name="excluir"
),
path(
    "financeiro/<int:pk>/cancelar/",
    views.cancelar_pagamento,
    name="cancelar_pagamento"
),

# SUPORTE
path(
    "suporte/abrir/",
    views.abrir_chamado,
    name="abrir_chamado"
),
path(
    "suporte/chamados/",
    views.listar_chamados,
    name="listar_chamados"
),
path(
    "suporte/chamados/<int:pk>/",
    views.detalhe_chamado,
    name="detalhe_chamado"
),
path(
    "suporte/chamados/<int:pk>/responder/",
    views.responder_chamado,
    name="responder_chamado"
),
path(
    "suporte/chamados/<int:pk>/status/",
    views.atualizar_status_chamado,
    name="atualizar_status_chamado"
),
path(
    "suporte/meus-chamados/",
    views.chamados_suporte,
    name="chamados_suporte"
),
]
