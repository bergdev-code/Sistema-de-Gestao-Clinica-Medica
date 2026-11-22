"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from func_django import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.login_view, name="login"),
    path("sair/", views.logout_view, name="logout"),
    path("painel/", views.dashboard, name="dashboard"),
    path("conta/", views.conta, name="conta"),
    path("consultas/solicitar/", views.solicitar_consulta, name="solicitar_consulta"),
    path("consultas/<int:pk>/aceitar/", views.aceitar_consulta, name="aceitar_consulta"),
    path("consultas/<int:pk>/recusar/", views.responder_consulta, {"acao": "recusar"}, name="recusar_consulta"),
    path("financeiro/", views.financeiro, name="financeiro"),
    path("financeiro/pagar/", views.pagar, name="pagar"),
    path("financeiro/<int:pk>/confirmar/", views.confirmar_pagamento, name="confirmar_pagamento"),
    path("financeiro/novo/", views.novo_pagamento, name="novo_pagamento"),
    path("<slug:recurso>/", views.lista, name="lista"),
    path("<slug:recurso>/novo/", views.novo, name="novo"),
    path("<slug:recurso>/<str:pk>/excluir/", views.excluir, name="excluir"),
]