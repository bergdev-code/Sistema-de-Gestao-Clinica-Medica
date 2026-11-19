from tabulate import tabulate
from func_django.models import func_django


def listar_pacientes():

    print("\n========== PACIENTES CADASTRADOS ==========\n")

    pacientes = func_django.objects.select_related("medico").all()

    if not pacientes.exists():
        print("Nenhum paciente cadastrado!")
        return

    tabela = []

    for paciente in pacientes:

        medico_nome = (
            paciente.medico.nome
            if paciente.medico
            else "Sem médico vinculado"
        )

        tabela.append([
            paciente.nome,
            paciente.cpf,
            paciente.data_nascimento,
            paciente.telefone,
            medico_nome
        ])

    cabecalho = [
        "NOME",
        "CPF",
        "DATA DE NASCIMENTO",
        "TELEFONE",
        "MÉDICO RESPONSÁVEL"
    ]

    print(tabulate(
        tabela,
        headers=cabecalho,
        tablefmt="grid"
    ))