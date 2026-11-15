from sistema_clinica.prontuarios.cadastro_prontuarios import prontuarios


def _exibir_prontuario(numero, prontuario):
    print(f"\n--- PRONTUÁRIO {numero} ---")
    print(f"Paciente: {prontuario['paciente']}")
    print(f"CPF: {prontuario['cpf']}")
    print(f"Médico: {prontuario['medico']}")
    print(f"Especialidade: {prontuario['especialidade']}")
    print(f"Data: {prontuario['data']}")
    print(f"Queixa: {prontuario['queixa']}")
    print(f"Diagnóstico: {prontuario['diagnostico']}")
    print(f"Prescrição: {prontuario['prescricao']}")
    print(f"Observações: {prontuario['observacoes']}")


def consultar_prontuario():
    print("\n===== CONSULTAR PRONTUÁRIO =====")

    if not prontuarios:
        print("Nenhum prontuário registrado!")
        return

    cpf = input("CPF do paciente: ").strip()

    if not cpf:
        print("\nCPF inválido!")
        return

    encontrados = [
        prontuario for prontuario in prontuarios if prontuario["cpf"] == cpf
    ]

    if not encontrados:
        print("\nNenhum prontuário encontrado para este paciente!")
        return

    print(f"\n{len(encontrados)} prontuário(s) encontrado(s).")

    for i, prontuario in enumerate(encontrados, start=1):
        _exibir_prontuario(i, prontuario)
