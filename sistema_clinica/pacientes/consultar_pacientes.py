from tabulate import tabulate

from func_django.models import func_django
from sistema_clinica.prontuarios.cadastro_prontuarios import prontuarios


def _formatar_data(data):
    if data is None:
        return ""
    return data.strftime("%d/%m/%Y")


def _exibir_paciente(paciente):
    quantidade = sum(
        1 for prontuario in prontuarios if prontuario["cpf"] == paciente.cpf
    )

    print("\nPaciente encontrado:")
    print(f"Nome: {paciente.nome}")
    print(f"CPF: {paciente.cpf}")
    print(f"Data de nascimento: {_formatar_data(paciente.data_nascimento)}")
    print(f"Telefone: {paciente.telefone}")
    print(f"Prontuários registrados: {quantidade}")


def consultar_por_cpf():
    print("\n========== CONSULTAR PACIENTE ==========")

    cpf = input("Informe o CPF do paciente: ").strip()

    if not cpf:
        print("\nCPF inválido!")
        return

    paciente = func_django.objects.filter(cpf=cpf).first()

    if paciente is None:
        print("\nPaciente não encontrado!")
        return

    _exibir_paciente(paciente)


def consultar_por_nome():
    print("\n========== CONSULTAR PACIENTE ==========")

    nome = input("Informe o nome do paciente: ").strip()

    if not nome:
        print("\nNome inválido!")
        return

    pacientes = func_django.objects.filter(nome__icontains=nome)

    if not pacientes.exists():
        print("\nNenhum paciente encontrado!")
        return

    tabela = []

    for paciente in pacientes:
        tabela.append([
            paciente.nome,
            paciente.cpf,
            _formatar_data(paciente.data_nascimento),
            paciente.telefone,
        ])

    cabecalho = ["NOME", "CPF", "DATA DE NASCIMENTO", "TELEFONE"]

    print()
    print(tabulate(tabela, headers=cabecalho, tablefmt="grid"))

    if pacientes.count() == 1:
        _exibir_paciente(pacientes.first())
