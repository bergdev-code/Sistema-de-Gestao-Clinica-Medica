
from tabulate import tabulate

from func_django.models import Prontuario


def listar_prontuarios():

    print("\n===== PRONTUÁRIOS REGISTRADOS =====")

    prontuarios = Prontuario.objects.select_related(
        "paciente"
    ).all().order_by("id_prontuario")

    if not prontuarios.exists():
        print("Nenhum prontuário registrado!")
        return

    tabela = []

    for prontuario in prontuarios:

        tabela.append([
            prontuario.id_prontuario,
            prontuario.paciente.nome,
            prontuario.paciente_id,
            prontuario.medico_id,
            prontuario.diagnostico
        ])

    cabecalho = [
        "ID",
        "Paciente",
        "CPF",
        "CRM DO MÉDICO",
        "Diagnóstico"
    ]

    print(
        tabulate(
            tabela,
            headers=cabecalho,
            tablefmt="grid"
        )
    )
