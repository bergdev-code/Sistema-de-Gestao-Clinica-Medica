from func_django.models import func_django
from sistema_clinica.medicos.cadastro_medicos import medicos

prontuarios = []


def registrar_prontuario():
    print("\n===== REGISTRO DE PRONTUÁRIO =====")

    if not func_django.objects.exists():
        print("Nenhum paciente cadastrado!")
        return

    cpf = input("CPF do paciente: ").strip()

    paciente = func_django.objects.filter(cpf=cpf).first()

    if paciente is None:
        print("Paciente não encontrado!")
        return

    if not medicos:
        print("Nenhum médico cadastrado!")
        return

    print("\n===== MÉDICOS DISPONÍVEIS =====")

    for medico in medicos:
        print(
            f"ID: {medico['id']} | "
            f"Nome: {medico['nome']} | "
            f"Especialidade: {medico['especialidade']}"
        )

    try:
        id_medico = int(input("\nID do médico: "))
    except ValueError:
        print("\nDigite um número válido!")
        return

    medico_selecionado = next(
        (m for m in medicos if m["id"] == id_medico),
        None
    )

    if medico_selecionado is None:
        print("Médico não encontrado!")
        return

    data = input("Data do atendimento: ").strip()
    queixa = input("Queixa principal: ").strip()
    diagnostico = input("Diagnóstico: ").strip()
    prescricao = input("Prescrição: ").strip()
    observacoes = input("Observações: ").strip()

    if not data or not queixa or not diagnostico:
        print("\nData, queixa e diagnóstico são obrigatórios!")
        return

    prontuario = {
        "id": len(prontuarios) + 1,
        "paciente": paciente.nome,
        "cpf": paciente.cpf,
        "medico": medico_selecionado["nome"],
        "especialidade": medico_selecionado["especialidade"],
        "data": data,
        "queixa": queixa,
        "diagnostico": diagnostico,
        "prescricao": prescricao,
        "observacoes": observacoes,
    }

    prontuarios.append(prontuario)

    print("\nProntuário registrado com sucesso!")
