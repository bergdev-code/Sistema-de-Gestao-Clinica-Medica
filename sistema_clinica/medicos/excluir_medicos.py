from sistema_clinica.medicos.cadastro_medicos import medicos

def excluir_medico():
    print("\n===== EXCLUIR MÉDICO =====")

    if not medicos:
        print("Nenhum médico cadastrado!")
        return

    for i, medico in enumerate(medicos, start=1):
        print(f"\n--- MÉDICO {i} ---")
        print(f"ID: {medico['id']}")
        print(f"Nome: {medico['nome']}")
        print(f"CRM: {medico['crm']}")
        print(f"Especialidade: {medico['especialidade']}")
        print(f"Horário: {medico['horario']}")

    try:
        opcao = int(input("\nDigite o número do médico que deseja excluir: "))

        if opcao < 1 or opcao > len(medicos):
            print("\nMédico não encontrado!")
            return

        medico_removido = medicos.pop(opcao - 1)

        print("\nMédico excluído com sucesso!")
        print(f"Médico removido: {medico_removido['nome']}")

    except ValueError:
        print("\nDigite um número válido!")
