from sistema_clinica.consultas.funcao_consulta import consultas

def listar_consultas():
    print("\n===== CONSULTAS AGENDADAS =====")

    if not consultas:
        print("Nenhuma consulta cadastrada!")
        return

    for i, consulta in enumerate(consultas, start=1):
        print(f"\n--- CONSULTA {i} ---")
        print(f"Paciente: {consulta['paciente']}")
        print(f"Médico: {consulta['medico']}")
        print(f"Especialidade: {consulta['especialidade']}")
        print(f"Data: {consulta['data']}")
        print(f"Horário: {consulta['horario']}")
