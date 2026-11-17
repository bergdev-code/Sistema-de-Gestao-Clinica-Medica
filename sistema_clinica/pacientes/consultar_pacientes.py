
from tabulate import tabulate

from func_django.models import func_django
from func_django.models import Prontuario


def _formatar_data(data):
    if data is None:
        return ""

    return data.strftime("%d/%m/%Y")


def _exibir_paciente(paciente):

    quantidade = Prontuario.objects.filter(
        paciente_id=paciente.cpf
    ).count()

    print("\n========== PACIENTE ENCONTRADO ==========")
    print(f"Nome: {paciente.nome}")
    print(f"CPF: {paciente.cpf}")
    print(f"Data de nascimento: {_formatar_data(paciente.data_nascimento)}")
    print(f"Telefone: {paciente.telefone}")
    print(f"Prontuários registrados: {quantidade}")


def consultar_paciente():

    print("\n========== CONSULTAR PACIENTE ==========")
    print("1 - Consultar por CPF")
    print("2 - Consultar por nome")

    opcao = input("\nEscolha uma opção: ").strip()

    if opcao == "1":

        valor = input("\nInforme o CPF do paciente: ").strip()

        if not valor:
            print("\nCPF inválido!")
            return

        pacientes = func_django.objects.filter(cpf=valor)

    elif opcao == "2":

        valor = input("\nInforme o nome do paciente: ").strip()

        if not valor:
            print("\nNome inválido!")
            return

        pacientes = func_django.objects.filter(nome__icontains=valor)

    else:
        print("\nOpção inválida!")
        return

    if not pacientes.exists():
        print("\nNenhum paciente encontrado!")
        return

    if pacientes.count() == 1:
        _exibir_paciente(pacientes.first())
        return

    tabela = []

    for paciente in pacientes:

        tabela.append([
            paciente.nome,
            paciente.cpf,
            _formatar_data(paciente.data_nascimento),
            paciente.telefone
        ])

    cabecalho = [
        "NOME",
        "CPF",
        "DATA DE NASCIMENTO",
        "TELEFONE"
    ]

    print("\n========== PACIENTES ENCONTRADOS ==========")
    print(tabulate(tabela, headers=cabecalho, tablefmt="grid"))
