from django.contrib import admin

from .models import (
    Especialidade,
    Perfil,
    StatusAgendamento,
    StatusPagamento,
)

# Tabelas de apoio: o /admin/ (superusuário do Django) serve para manter estes
# cadastros, que o sistema exige existirem (ex.: o perfil "Paciente").
# Usuários, pacientes, consultas e pagamentos continuam sendo geridos pelas telas
# do próprio sistema, com as permissões de cada perfil.
admin.site.register(Perfil)
admin.site.register(Especialidade)
admin.site.register(StatusAgendamento)
admin.site.register(StatusPagamento)
