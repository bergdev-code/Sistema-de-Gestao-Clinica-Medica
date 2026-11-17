
from func_django.models import Agendamento, StatusAgendamento


def excluir_consulta():
    print("\n===== EXCLUIR CONSULTA =====")

    consultas = (
        Agendamento.objects
        .select_related("paciente", "medico", "status")
        .order_by("data_hora")
    )

    if not consultas.exists():
        print("Nenhuma consulta cadastrada!")
        return

    lista_consultas = list(consultas)

    for i, consulta in enumerate(lista_consultas, start=1):
        print(f"\n--- CONSULTA {i} ---")
        print(f"ID: {consulta.id_agendamento}")
        print(f"Paciente: {consulta.paciente.nome}")
        print(f"Médico: {consulta.medico.nome}")
        print(f"Data: {consulta.data_hora.strftime('%d/%m/%Y')}")
        print(f"Horário: {consulta.data_hora.strftime('%H:%M')}")
        print(f"Status: {consulta.status.descricao}")

    try:
        opcao = int(
            input("\nDigite o número da consulta que deseja cancelar: ")
        )

        if opcao < 1 or opcao > len(lista_consultas):
            print("\nConsulta não encontrada!")
            return

        consulta_selecionada = lista_consultas[opcao - 1]

        confirmacao = input(
            "\nDeseja realmente cancelar esta consulta? (S/N): "
        ).strip().upper()

        if confirmacao != "S":
            print("\nOperação cancelada!")
            return

        status_cancelado = StatusAgendamento.objects.filter(
            descricao__iexact="Cancelado"
        ).first()

        if status_cancelado is None:
            print("\nStatus 'Cancelado' não cadastrado!")
            return

        consulta_selecionada.status = status_cancelado
        consulta_selecionada.save(update_fields=["status"])

        print("\nConsulta cancelada com sucesso!")
        print(f"Paciente: {consulta_selecionada.paciente.nome}")

    except ValueError:
        print("\nDigite um número válido!")

    except Exception as erro:
        print(f"\nErro ao cancelar consulta: {erro}")
