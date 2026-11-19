
from func_django.models import (
    Medico,
    Agendamento,
    Prontuario,
    Usuario
)

from sistema_clinica.funcionalidades.acesso_medico import acesso_medico


def iniciar_atendimento():

    # VERIFICAR PERMISSÃO
    username = acesso_medico()

    if username is None:
        return

    try:

        # IDENTIFICAR USUÁRIO LOGADO
        usuario = Usuario.objects.select_related(
            "medico",
            "id_perfil"
        ).filter(username=username).first()

        if usuario is None:
            print("\nUsuário não encontrado!")
            return

        perfil = usuario.id_perfil.nome_perfil

        # IDENTIFICAR MÉDICO
        if perfil == "Médico":

            medico = usuario.medico

            if medico is None:
                print("\nNenhum médico vinculado a este usuário!")
                return

            if not medico.ativo:
                print("\nMédico inativo!")
                return

        elif perfil == "ADMIN GERAL":

            # ADMIN GERAL SELECIONA O MÉDICO
            medicos = Medico.objects.filter(
                ativo=True
            ).order_by("nome")

            if not medicos.exists():
                print("\nNenhum médico ativo encontrado!")
                return

            lista_medicos = list(medicos)

            print("\n===== SELECIONAR MÉDICO =====")

            for i, profissional in enumerate(lista_medicos, start=1):
                print(
                    f"{i} - {profissional.nome} "
                    f"| CRM: {profissional.crm}"
                )

            try:
                opcao_medico = int(input("\nSelecione o médico: "))

                if opcao_medico < 1 or opcao_medico > len(lista_medicos):
                    print("\nOpção inválida!")
                    return

                medico = lista_medicos[opcao_medico - 1]

            except ValueError:
                print("\nDigite um número válido!")
                return

        else:
            print("\nPerfil sem autorização para iniciar atendimento!")
            return

        # LISTAR AGENDAMENTOS
        print("\n===== INICIAR ATENDIMENTO =====")

        agendamentos = (
            Agendamento.objects
            .filter(medico=medico)
            .select_related("paciente", "status")
            .order_by("data_hora")
        )

        if not agendamentos.exists():
            print("\nNenhum agendamento disponível!")
            return

        lista = list(agendamentos)

        for i, agendamento in enumerate(lista, start=1):

            print(f"\n{i} - {agendamento.paciente.nome}")
            print(
                f"    Data: "
                f"{agendamento.data_hora.strftime('%d/%m/%Y %H:%M')}"
            )
            print(f"    Status: {agendamento.status.descricao}")

        # SELECIONAR AGENDAMENTO
        try:

            opcao = int(input("\nSelecione o atendimento: "))

            if opcao < 1 or opcao > len(lista):
                print("\nOpção inválida!")
                return

            agendamento = lista[opcao - 1]
            paciente = agendamento.paciente

        except ValueError:
            print("\nDigite um número válido!")
            return

        # DADOS DO PACIENTE
        print("\n===== DADOS DO PACIENTE =====")

        print(f"Nome: {paciente.nome}")
        print(f"CPF: {paciente.cpf}")
        print(f"Telefone: {paciente.telefone}")
        print(f"Data de nascimento: {paciente.data_nascimento}")

        # HISTÓRICO MÉDICO
        print("\n===== HISTÓRICO MÉDICO =====")

        prontuarios = (
            Prontuario.objects
            .filter(paciente=paciente)
            .order_by("-id_prontuario")
        )

        if not prontuarios.exists():
            print("\nNenhum prontuário anterior encontrado!")

        for prontuario in prontuarios:

            print(f"\nProntuário: {prontuario.id_prontuario}")
            print(f"Anamnese: {prontuario.anamnese}")
            print(f"Diagnóstico: {prontuario.diagnostico}")
            print(f"Prescrição: {prontuario.prescricao}")

        # NOVO ATENDIMENTO
        print("\n===== NOVO ATENDIMENTO =====")

        anamnese = input("Anamnese: ").strip()
        diagnostico = input("Diagnóstico: ").strip()
        prescricao = input("Prescrição médica: ").strip()

        if not anamnese and not diagnostico and not prescricao:
            print("\nNenhuma informação foi preenchida!")
            return

        # REGISTRAR PRONTUÁRIO
        Prontuario.objects.create(
            paciente=paciente,
            medico=medico,
            anamnese=anamnese,
            diagnostico=diagnostico,
            prescricao=prescricao
        )

        print("\nAtendimento registrado com sucesso!")

    except Exception as erro:
        print(f"\nErro ao realizar atendimento: {erro}")
