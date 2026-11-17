
from func_django.models import Agendamento


def listar_consultas():
    print("\n===== CONSULTAS AGENDADAS =====")

    consultas = (
        Agendamento.objects
        .select_related("paciente", "medico", "status")
        .order_by("data_hora")
    )

    if not consultas.exists():
        print("Nenhuma consulta cadastrada!")
        return

    for i, consulta in enumerate(consultas, start=1):
        print(f"\n--- CONSULTA {i} ---")

        print(f"ID: {consulta.id_agendamento}")
        print(f"Paciente: {consulta.paciente.nome}")
        print(f"CPF: {consulta.paciente.cpf}")

        print(f"Médico: {consulta.medico.nome}")
        print(f"CRM: {consulta.medico.crm}")

        print(f"Data: {consulta.data_hora.strftime('%d/%m/%Y')}")
        print(f"Horário: {consulta.data_hora.strftime('%H:%M')}")

        print(f"Status: {consulta.status.descricao}")
