from urllib.parse import urlparse

from django.conf import settings
from django.contrib import admin
from django.urls import path

from func_django import views


# A rota de retorno do Google precisa ser exatamente a cadastrada no Google Cloud
# (GOOGLE_REDIRECT_URI). Se ela for diferente do caminho padrão abaixo, o caminho
# configurado também passa a funcionar, sem você precisar mexer neste arquivo.
CALLBACK_GOOGLE_PADRAO = "google/callback/"
_caminho_configurado = urlparse(getattr(settings, "GOOGLE_REDIRECT_URI", "") or "").path.strip("/")
_caminho_configurado = f"{_caminho_configurado}/" if _caminho_configurado else ""

urlpatterns = [
    path("admin/", admin.site.urls),

    # Autenticação, cadastro e painel
    path("", views.login_view, name="login"),
    path("sair/", views.logout_view, name="logout"),
    path("painel/", views.dashboard, name="dashboard"),
    path("cadastro/", views.cadastro_publico, name="cadastro_publico"),
    path("conta/", views.conta, name="conta"),

    # Login com Google
    path("google/entrar/", views.google_login, name="google_login"),
    path(CALLBACK_GOOGLE_PADRAO, views.google_callback, name="google_callback"),
    path(
        "google/completar-cadastro/",
        views.completar_cadastro_google,
        name="completar_cadastro_google"
    ),

    # Consultas
    path(
        "consultas/solicitar/",
        views.solicitar_consulta,
        name="solicitar_consulta"
    ),
    path(
        "consultas/<int:pk>/aceitar/",
        views.aceitar_consulta,
        name="aceitar_consulta"
    ),
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

    # Financeiro
    path("financeiro/", views.financeiro, name="financeiro"),
    path("financeiro/pagar/", views.pagar, name="pagar"),
    path(
        "financeiro/<int:pk>/confirmar/",
        views.confirmar_pagamento,
        name="confirmar_pagamento"
    ),
    path(
        "financeiro/<int:pk>/cancelar/",
        views.cancelar_pagamento,
        name="cancelar_pagamento"
    ),
    path(
        "financeiro/novo/",
        views.novo_pagamento,
        name="novo_pagamento"
    ),
    path(
        "financeiro/pagamento/",
        views.pagar_consulta,
        name="pagar_consulta"
    ),

    # Pagamento em dinheiro pela recepcionista
    path(
        "pagamentos/dinheiro/<int:agendamento_id>/",
        views.registrar_pagamento_dinheiro,
        name="registrar_pagamento_dinheiro"
    ),

    # Listagem, cadastro, edição e exclusão genéricos.
    # ATENÇÃO À ORDEM: tudo o que é específico fica ACIMA destas rotas genéricas,
    # senão "<slug:recurso>/" captura o endereço antes da view certa.
    path("<slug:recurso>/", views.lista, name="lista"),
    path("<slug:recurso>/novo/", views.novo, name="novo"),

    # Ficha do paciente e alergias ("pacientes/novo/" já foi tratado acima)
    path(
        "pacientes/<str:cpf>/",
        views.detalhe_paciente,
        name="detalhe_paciente"
    ),
    path(
        "pacientes/<str:cpf>/alergias/nova/",
        views.adicionar_alergia,
        name="adicionar_alergia"
    ),
    path(
        "pacientes/<str:cpf>/alergias/<int:pk>/excluir/",
        views.excluir_alergia,
        name="excluir_alergia"
    ),

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
]

if _caminho_configurado and _caminho_configurado != CALLBACK_GOOGLE_PADRAO:
    urlpatterns.insert(
        0,
        path(_caminho_configurado, views.google_callback, name="google_callback_configurado"),
    )
