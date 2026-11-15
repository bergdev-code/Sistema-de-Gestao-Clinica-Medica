from sistema_clinica.prontuarios.cadastro_prontuarios import prontuarios


def excluir_prontuario():
    print("\n===== EXCLUIR PRONTUÁRIO =====")

    if not prontuarios:
        print("Nenhum prontuário registrado!")
        return

    for i, prontuario in enumerate(prontuarios, start=1):
        print(f"\n--- PRONTUÁRIO {i} ---")
        print(f"Paciente: {prontuario['paciente']}")
        print(f"CPF: {prontuario['cpf']}")
        print(f"Médico: {prontuario['medico']}")
        print(f"Data: {prontuario['data']}")
        print(f"Diagnóstico: {prontuario['diagnostico']}")

    try:
        opcao = int(input("\nDigite o número do prontuário que deseja excluir: "))

        if opcao < 1 or opcao > len(prontuarios):
            print("\nProntuário não encontrado!")
            return

        confirmacao = input("\nDeseja realmente excluir? (S/N): ").strip().upper()

        if confirmacao != "S":
            print("\nExclusão cancelada!")
            return

        prontuario_removido = prontuarios.pop(opcao - 1)

        print("\nProntuário excluído com sucesso!")
        print(f"Paciente: {prontuario_removido['paciente']}")

    except ValueError:
        print("\nDigite um número válido!")
