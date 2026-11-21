from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("sair/", views.logout_view, name="logout"),
    path("painel/", views.dashboard, name="dashboard"),
    path("financeiro/", views.financeiro, name="financeiro"),
    path("financeiro/novo/", views.novo_pagamento, name="novo_pagamento"),
    path("<slug:recurso>/", views.lista, name="lista"),
    path("<slug:recurso>/novo/", views.novo, name="novo"),
    path("<slug:recurso>/<str:pk>/excluir/", views.excluir, name="excluir"),
]