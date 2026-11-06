from sistema_clinica.pacientes.cadastro_pacientes import pacientes

def excluir_paciente():
    print("\n===== EXCLUIR PACIENTE =====")

    if not pacientes:
        print("Nenhum paciente cadastrado!")
        return

    for i, paciente in enumerate(pacientes, start=1):
        print(f"\n--- PACIENTE {i} ---")
        print(f"Nome: {paciente['nome']}")
        print(f"CPF: {paciente['cpf']}")
        print(f"Data de nascimento: {paciente['data_nascimento']}")
        print(f"Telefone: {paciente['telefone']}")

    try:
        opcao = int(input("\nDigite o número do paciente que deseja excluir: "))

        if opcao < 1 or opcao > len(pacientes):
            print("\nPaciente não encontrado!")
            return

        paciente_removido = pacientes.pop(opcao - 1)

        print("\nPaciente excluído com sucesso!")
        print(f"Paciente removido: {paciente_removido['nome']}")

    except ValueError:
        print("\nDigite um número válido!")
