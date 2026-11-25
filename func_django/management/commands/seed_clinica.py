from django.core.management.base import BaseCommand
from django.db import transaction

from func_django.models import Perfil, StatusAgendamento, StatusPagamento

# Os nomes dos perfis precisam bater com os do dicionário PERMISSOES (views.py).
PERFIS = ["Administrador", "Recepcionista", "Médico", "Paciente"]
STATUS_AGENDAMENTO = ["Solicitada", "Agendada", "Cancelada"]
STATUS_PAGAMENTO = ["Pendente", "Concluído", "Cancelado"]


def garantir(modelo, campo, valor):
    """Cria o registro só se ainda não existir (sem diferenciar maiúsculas)."""
    if modelo.objects.filter(**{f"{campo}__iexact": valor}).exists():
        return False
    modelo.objects.create(**{campo: valor})
    return True


class Command(BaseCommand):
    help = (
        "Cadastra os registros de apoio que o sistema exige (perfis e status). "
        "Pode ser executado várias vezes: não duplica nada."
    )

    @transaction.atomic
    def handle(self, *args, **opcoes):
        criados = []
        for nome in PERFIS:
            if garantir(Perfil, "nome_perfil", nome):
                criados.append(f"perfil {nome}")
        for nome in STATUS_AGENDAMENTO:
            if garantir(StatusAgendamento, "descricao", nome):
                criados.append(f"status de consulta {nome}")
        for nome in STATUS_PAGAMENTO:
            if garantir(StatusPagamento, "descricao", nome):
                criados.append(f"status de pagamento {nome}")

        if criados:
            self.stdout.write(self.style.SUCCESS("Criados: " + ", ".join(criados) + "."))
        else:
            self.stdout.write("Nada a fazer: todos os registros de apoio já existem.")
