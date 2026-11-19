from datetime import datetime
from django.utils import timezone

from func_django.models import (
    func_django,
    Medico,
    Agendamento,
    StatusAgendamento
)


def agendar_consulta():

    print("\n===== AGENDAMENTO DE CONSULTAS =====")

    # Busca o paciente
    cpf = input("CPF do paciente: ").strip()

    paciente = func_django.objects.filter(cpf=cpf).first()

    if paciente is None:
        print("\nPaciente não encontrado!")
        return

    print(f"\nPaciente: {paciente.nome}")

    # Verifica o médico vinculado ao paciente
    medico = paciente.medico

    if medico is None or not medico.ativo:
        print("\nO paciente não possui médico responsável ativo!")
        return

    print("\n===== MÉDICO RESPONSÁVEL =====")
    print(f"Nome: {medico.nome}")
    print(f"CRM: {medico.crm}")

    # Recebe e valida data e horário
    data = input("\nData da consulta (DD/MM/AAAA): ").strip()
    horario = input("Horário (HH:MM): ").strip()

    try:
        data_hora = datetime.strptime(
            f"{data} {horario}",
            "%d/%m/%Y %H:%M"
        )

        data_hora = timezone.make_aware(data_hora)

    except ValueError:
        print("\nData ou horário inválido!")
        return

    # Verifica conflito de horário
    conflito = Agendamento.objects.filter(
        medico=medico,
        data_hora=data_hora
    ).exclude(
        status__descricao__iexact="Cancelado"
    ).exists()

    if conflito:
        print("\nEsse médico já possui um agendamento nesse horário!")
        return

    # Busca o status inicial
    status_pendente = StatusAgendamento.objects.filter(
        descricao__iexact="Pendente"
    ).first()

    if status_pendente is None:
        print("\nStatus 'Pendente' não cadastrado no banco!")
        return

    # Registra o agendamento
    try:

        agendamento = Agendamento.objects.create(
            paciente=paciente,
            medico=medico,
            data_hora=data_hora,
            status=status_pendente
        )

        print("\n===== CONSULTA AGENDADA COM SUCESSO =====")
        print(f"ID: {agendamento.id_agendamento}")
        print(f"Paciente: {paciente.nome}")
        print(f"CPF: {paciente.cpf}")
        print(f"Médico: {medico.nome}")
        print(f"CRM: {medico.crm}")
        print(f"Data: {data_hora.strftime('%d/%m/%Y')}")
        print(f"Horário: {data_hora.strftime('%H:%M')}")
        print(f"Status: {status_pendente.descricao}")

    except Exception as erro:
        print(f"\nErro ao agendar consulta: {erro}")