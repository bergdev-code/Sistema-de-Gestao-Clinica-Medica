from sistema_clinica.consultas.funcao_consulta import consultas


def excluir_consulta():
    print("\n===== EXCLUIR CONSULTA =====")

    if not consultas:
        print("Nenhuma consulta cadastrada!")
        return

    for i, consulta in enumerate(consultas, start=1):
        print(f"\n--- CONSULTA {i} ---")
        print(f"Paciente: {consulta['paciente']}")
        print(f"Médico: {consulta['medico']}")
        print(f"Data: {consulta['data']}")
        print(f"Horário: {consulta['horario']}")

    try:
        opcao = int(input("\nDigite o número da consulta que deseja excluir: "))

        if opcao < 1 or opcao > len(consultas):
            print("\nConsulta não encontrada!")
            return

        consulta_removida = consultas.pop(opcao - 1)

        print("\nConsulta excluída com sucesso!")
        print(f"Paciente: {consulta_removida['paciente']}")

    except ValueError:
        print("\nDigite um número válido!")
