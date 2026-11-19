from func_django.models import Medico, Agendamento


def meus_agendamentos(crm):

    print("\n===== MEUS AGENDAMENTOS =====")

    medico = Medico.objects.filter(
        crm=crm,
        ativo=True
    ).first()

    if medico is None:
        print("\nMédico não encontrado ou inativo!")
        return

    agendamentos = (
        Agendamento.objects
        .filter(medico=medico)
        .select_related("paciente", "status")
        .order_by("data_hora")
    )

    if not agendamentos.exists():
        print("\nVocê não possui agendamentos!")
        return

    lista_agendamentos = list(agendamentos)

    for i, agendamento in enumerate(lista_agendamentos, start=1):

        print(f"\n--- AGENDAMENTO {i} ---")
        print(f"ID: {agendamento.id_agendamento}")
        print(f"Paciente: {agendamento.paciente.nome}")
        print(f"CPF: {agendamento.paciente.cpf}")

        print(
            f"Data: {agendamento.data_hora.strftime('%d/%m/%Y')}"
        )

        print(
            f"Horário: {agendamento.data_hora.strftime('%H:%M')}"
        )

        print(f"Status: {agendamento.status.descricao}")