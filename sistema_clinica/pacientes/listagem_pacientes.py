from tabulate import tabulate
from func_django.models import func_django


def listar_pacientes():

    print("\n========== PACIENTES CADASTRADOS ==========\n")

    pacientes = func_django.objects.all()

    if not pacientes.exists():
        print("Nenhum paciente cadastrado!")
        return

    tabela = []

    for paciente in pacientes:
        tabela.append([
            paciente.nome,
            paciente.cpf,
            paciente.data_nascimento,
            paciente.telefone
        ])

    cabecalho = ["NOME", "CPF", "DATA DE NASCIMENTO", "TELEFONE"]

    print(tabulate(
        tabela,
        headers=cabecalho,
        tablefmt="grid"
    ))
