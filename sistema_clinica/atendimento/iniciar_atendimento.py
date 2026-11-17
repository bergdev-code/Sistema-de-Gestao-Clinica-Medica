
from func_django.models import (
    Medico,
    Agendamento,
    Prontuario,
    func_django
)


def iniciar_atendimento(username):
    print("\n===== INICIAR ATENDIMENTO =====")

    medico = Medico.objects.filter(
        usuario=username,
        ativo=True
    ).first()

    if medico is None:
        print("Médico não encontrado!")
        return

    agendamentos = (
        Agendamento.objects
        .filter(medico=medico)
        .select_related("paciente", "status")
        .order_by("data_hora")
    )

    if not agendamentos.exists():
        print("Nenhum agendamento disponível!")
        return

    lista = list(agendamentos)

    for i, agendamento in enumerate(lista, start=1):
        print(f"\n{i} - {agendamento.paciente.nome}")
        print(f"    Data: {agendamento.data_hora.strftime('%d/%m/%Y %H:%M')}")
        print(f"    Status: {agendamento.status.descricao}")

    try:
        opcao = int(input("\nSelecione o atendimento: "))

        if opcao < 1 or opcao > len(lista):
            print("Opção inválida!")
            return

        agendamento = lista[opcao - 1]
        paciente = agendamento.paciente

        print("\n===== DADOS DO PACIENTE =====")
        print(f"Nome: {paciente.nome}")
        print(f"CPF: {paciente.cpf}")
        print(f"Telefone: {paciente.telefone}")
        print(f"Data de nascimento: {paciente.data_nascimento}")

        print("\n===== HISTÓRICO MÉDICO =====")

        prontuarios = Prontuario.objects.filter(
            paciente=paciente
        ).order_by("-id_prontuario")

        if not prontuarios.exists():
            print("Nenhum prontuário anterior encontrado!")

        for prontuario in prontuarios:
            print(f"\nProntuário: {prontuario.id_prontuario}")
            print(f"Anamnese: {prontuario.anamnese}")
            print(f"Diagnóstico: {prontuario.diagnostico}")
            print(f"Prescrição: {prontuario.prescricao}")

        print("\n===== NOVO ATENDIMENTO =====")

        anamnese = input("Anamnese: ").strip()
        diagnostico = input("Diagnóstico: ").strip()
        prescricao = input("Prescrição médica: ").strip()

        if not anamnese and not diagnostico and not prescricao:
            print("Nenhuma informação foi preenchida!")
            return

        Prontuario.objects.create(
            paciente=paciente,
            medico=medico,
            agendamento_id=agendamento.id_agendamento,
            anamnese=anamnese,
            diagnostico=diagnostico,
            prescricao=prescricao
        )

        print("\nAtendimento registrado com sucesso!")

    except ValueError:
        print("Digite um número válido!")

    except Exception as erro:
        print(f"Erro ao realizar atendimento: {erro}")
