from django.contrib import admin
from django.urls import path
from func_django import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.login_view, name="login"),
    path("sair/", views.logout_view, name="logout"),
    path("painel/", views.dashboard, name="dashboard"),
    path("consultas/solicitar/", views.solicitar_consulta, name="solicitar_consulta"),
    path("consultas/<int:pk>/aceitar/", views.responder_consulta, {"acao": "aceitar"}, name="aceitar_consulta"),
    path("consultas/<int:pk>/recusar/", views.responder_consulta, {"acao": "recusar"}, name="recusar_consulta"),
    path("financeiro/", views.financeiro, name="financeiro"),
    path("financeiro/pagar/", views.pagar, name="pagar"),
    path("financeiro/<int:pk>/confirmar/", views.confirmar_pagamento, name="confirmar_pagamento"),
    path("financeiro/novo/", views.novo_pagamento, name="novo_pagamento"),
    path("<slug:recurso>/", views.lista, name="lista"),
    path("<slug:recurso>/novo/", views.novo, name="novo"),
    path("<slug:recurso>/<str:pk>/excluir/", views.excluir, name="excluir"),
]