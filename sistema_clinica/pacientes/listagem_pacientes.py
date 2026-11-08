from tabulate import tabulate

from sistema_clinica.pacientes.cadastro_pacientes import *

def listar_pacientes():
    print("\n========== PACIENTES CADASTRADOS ==========")

    if not pacientes:
        print("Nenhum paciente cadastrado!")
        return

    print("-" * 100)

    for i, paciente in enumerate(pacientes, start=1):
        print(f"\nPACIENTE {i}")
        print("-" * 100)

        print(f"{'NOME:':<22} {paciente['nome']}")
        print(f"{'CPF:':<22} {paciente['cpf']}")
        print(f"{'DATA DE NASCIMENTO:':<22} {paciente['data_nascimento']}")
        print(f"{'TELEFONE:':<22} {paciente['telefone']}")

        print("-" * 100)