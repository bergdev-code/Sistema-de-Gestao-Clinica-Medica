from sistema_clinica.pacientes.cadastro_pacientes import func_django
from sistema_clinica.medicos.cadastro_medicos import medicos

consultas = []


def agendar_consulta():

    print("\n===== AGENDAMENTO DE CONSULTAS =====")

    cpf = input("CPF do paciente: ")

    paciente_selecionado = next(
        (p for p in func_django if p["cpf"] == cpf),
        None
    )

    if paciente_selecionado is None:
        print("Paciente não encontrado!")
        return

    print("\n===== MÉDICOS DISPONÍVEIS =====")

    for medico in medicos:
        print(
            f"ID: {medico['id']} | "
            f"Nome: {medico['nome']} | "
            f"Especialidade: {medico['especialidade']}"
        )

    id_medico = int(input("\nID do médico: "))

    medico_selecionado = next(
        (m for m in medicos if m["id"] == id_medico),
        None
    )

    if medico_selecionado is None:
        print("Médico não encontrado!")
        return

    data = input("Data da consulta: ")
    horario = input("Horário: ")

    consulta = {
        "paciente": paciente_selecionado["nome"],
        "medico": medico_selecionado["nome"],
        "especialidade": medico_selecionado["especialidade"],
        "data": data,
        "horario": horario
    }

    consultas.append(consulta)

    print("\nConsulta agendada com sucesso!")
