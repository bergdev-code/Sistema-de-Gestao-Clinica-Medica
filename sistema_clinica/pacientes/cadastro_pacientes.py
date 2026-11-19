from django.db import transaction
from datetime import datetime

from func_django.models import (
    func_django,
    Medico,
    MedicoEspecialidade
)


def cadastrar_paciente():

    print("\n===== CADASTRO DE PACIENTE =====")

    # Verificar médicos disponíveis
    medicos = Medico.objects.filter(ativo=True)

    if not medicos.exists():
        print("\nNão existem médicos disponíveis!")
        print("Cadastre um médico antes de cadastrar pacientes.")
        return

    # Dados pessoais
    print("\n--- DADOS PESSOAIS ---")

    nome = input("Nome completo: ").strip()
    cpf = input("CPF: ").strip()
    data_nascimento = input(
        "Data de nascimento (DD/MM/AAAA): "
    ).strip()
    telefone = input("Telefone: ").strip()

    if not nome or not cpf or not data_nascimento or not telefone:
        print("\nTodos os campos são obrigatórios!")
        return

    # Verificar CPF duplicado
    if func_django.objects.filter(cpf=cpf).exists():
        print("\nJá existe um paciente com esse CPF!")
        return

    # Validar data de nascimento
    try:
        data_nascimento = datetime.strptime(
            data_nascimento, "%d/%m/%Y"
        ).date()

    except ValueError:
        print("\nData de nascimento inválida!")
        return

    # Exibir médicos disponíveis e especialidades
    print("\n===== MÉDICOS DISPONÍVEIS =====")

    for medico in medicos:

        especialidades = MedicoEspecialidade.objects.filter(
            medico=medico
        ).select_related("especialidade")

        nomes_especialidades = [
            relacao.especialidade.nome
            for relacao in especialidades
        ]

        print(f"\nCRM: {medico.crm}")
        print(f"Nome: {medico.nome}")

        if nomes_especialidades:
            print(
                "Especialidade(s): "
                + ", ".join(nomes_especialidades)
            )
        else:
            print("Especialidade(s): Não cadastrada")

    # Selecionar médico pelo CRM
    crm_medico = input(
        "\nDigite o CRM do médico desejado: "
    ).strip()

    try:
        medico = medicos.get(crm=crm_medico)

    except Medico.DoesNotExist:
        print("\nMédico inválido ou indisponível!")
        return

    # Cadastrar paciente
    try:

        with transaction.atomic():

            paciente = func_django.objects.create(
                nome=nome,
                cpf=cpf,
                data_nascimento=data_nascimento,
                telefone=telefone,
                medico=medico
            )

        print("\nPaciente cadastrado com sucesso!")

        print("\n===== RESUMO DO CADASTRO =====")
        print(f"Nome: {paciente.nome}")
        print(f"CPF: {paciente.cpf}")
        print(f"Médico responsável: {medico.nome}")
        print(f"CRM: {medico.crm}")

    except Exception as erro:
        print(f"\nErro ao cadastrar paciente: {erro}")