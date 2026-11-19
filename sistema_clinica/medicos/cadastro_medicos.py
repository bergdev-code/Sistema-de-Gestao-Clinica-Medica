from django.db import transaction
from func_django.models import (
    Medico,
    Especialidade,
    MedicoEspecialidade,
    HorarioMedico
)


def cadastrar_medico():

    print("\n===== CADASTRO DE MÉDICO =====")

    crm = input("CRM: ").strip()
    nome = input("Nome: ").strip()
    telefone = input("Telefone: ").strip()

    if not crm or not nome or not telefone:
        print("\nTodos os campos são obrigatórios!")
        return

    if Medico.objects.filter(crm=crm).exists():
        print("\nJá existe um médico cadastrado com esse CRM!")
        return

    print("\n===== ESPECIALIDADE =====")

    nome_especialidade = input("Especialidade: ").strip()

    if not nome_especialidade:
        print("\nEspecialidade inválida!")
        return

    print("\n===== HORÁRIO DE ATENDIMENTO =====")

    dia_semana = input("Dia da semana: ").strip()
    hora_inicio = input("Horário de início (HH:MM): ").strip()
    hora_fim = input("Horário de término (HH:MM): ").strip()

    if not dia_semana or not hora_inicio or not hora_fim:
        print("\nPreencha todos os campos de horário!")
        return

    try:

        with transaction.atomic():

            # Cadastrar médico
            medico = Medico.objects.create(
                crm=crm,
                nome=nome,
                telefone=telefone,
                ativo=True
            )

            # Buscar ou cadastrar especialidade
            especialidade = Especialidade.objects.filter(
                nome__iexact=nome_especialidade
            ).first()

            if especialidade is None:
                especialidade = Especialidade.objects.create(
                    nome=nome_especialidade
                )

            # Relacionar médico e especialidade
            MedicoEspecialidade.objects.create(
                medico=medico,
                especialidade=especialidade
            )

            # Cadastrar horário
            HorarioMedico.objects.create(
                medico=medico,
                dia_semana=dia_semana,
                hora_inicio=hora_inicio,
                hora_fim=hora_fim
            )

        print("\nMédico cadastrado com sucesso!")

    except Exception as erro:
        print(f"\nErro ao cadastrar médico: {erro}")