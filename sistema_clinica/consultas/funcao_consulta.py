
from datetime import datetime

from func_django.models import (
    func_django,
    Medico,
    Agendamento,
    StatusAgendamento
)


def agendar_consulta():
    print("\n===== AGENDAMENTO DE CONSULTAS =====")

    # Busca o paciente no banco de dados
    cpf = input("CPF do paciente: ").strip()

    paciente_selecionado = func_django.objects.filter(
        cpf=cpf
    ).first()

    if paciente_selecionado is None:
        print("\nPaciente não encontrado!")
        return

    print(f"\nPaciente: {paciente_selecionado.nome}")

    # Busca médicos ativos no banco
    medicos = Medico.objects.filter(
        ativo=True
    ).order_by("nome")

    if not medicos.exists():
        print("\nNenhum médico ativo cadastrado!")
        return

    lista_medicos = list(medicos)

    print("\n===== MÉDICOS DISPONÍVEIS =====")

    for i, medico in enumerate(lista_medicos, start=1):
        print(
            f"{i} - Nome: {medico.nome} | "
            f"CRM: {medico.crm}"
        )

    try:
        opcao_medico = int(input("\nSelecione o médico: "))

        if opcao_medico < 1 or opcao_medico > len(lista_medicos):
            print("\nMédico não encontrado!")
            return

        medico_selecionado = lista_medicos[opcao_medico - 1]

        # Recebe e valida a data e o horário
        data = input("\nData da consulta (DD/MM/AAAA): ").strip()
        horario = input("Horário (HH:MM): ").strip()

        try:
            data_hora = datetime.strptime(
                f"{data} {horario}",
                "%d/%m/%Y %H:%M"
            )
        except ValueError:
            print("\nData ou horário inválido!")
            return

        # Busca os status cadastrados no banco
        status_disponiveis = StatusAgendamento.objects.all().order_by(
            "id_status"
        )

        if not status_disponiveis.exists():
            print("\nNenhum status de agendamento cadastrado!")
            return

        lista_status = list(status_disponiveis)

        print("\n===== STATUS DA CONSULTA =====")

        for i, status in enumerate(lista_status, start=1):
            print(f"{i} - {status.descricao}")

        opcao_status = int(input("\nSelecione o status: "))

        if opcao_status < 1 or opcao_status > len(lista_status):
            print("\nStatus inválido!")
            return

        status_selecionado = lista_status[opcao_status - 1]

        # Salva o agendamento diretamente no MySQL
        Agendamento.objects.create(
            paciente=paciente_selecionado,
            medico=medico_selecionado,
            data_hora=data_hora,
            status=status_selecionado
        )

        print("\nConsulta agendada com sucesso!")
        print(f"Paciente: {paciente_selecionado.nome}")
        print(f"Médico: {medico_selecionado.nome}")
        print(f"CRM: {medico_selecionado.crm}")
        print(f"Data: {data_hora.strftime('%d/%m/%Y')}")
        print(f"Horário: {data_hora.strftime('%H:%M')}")
        print(f"Status: {status_selecionado.descricao}")

    except ValueError:
        print("\nDigite uma opção numérica válida!")

    except Exception as erro:
        print(f"\nErro ao agendar consulta: {erro}")
