
from django.core.exceptions import ImproperlyConfigured
from func_django.models import func_django, Prontuario, Medico


def cadastrar_prontuario():
    print("\n===== CADASTRO DE PRONTUÁRIO =====")

    cpf = input("CPF do paciente: ").strip()

    try:
        paciente = func_django.objects.get(cpf=cpf)
    except func_django.DoesNotExist:
        print("\nPaciente não encontrado!")
        return

    # Busca os médicos diretamente no banco de dados
    medicos = Medico.objects.filter(ativo=True).order_by("nome")

    if not medicos.exists():
        print("\nNenhum médico ativo cadastrado!")
        return

    print("\n===== MÉDICOS DISPONÍVEIS =====")

    lista_medicos = list(medicos)

    for i, medico in enumerate(lista_medicos, start=1):
        print(f"{i} - {medico.nome} | CRM: {medico.crm}")

    try:
        opcao = int(input("\nSelecione o médico: "))

        if opcao < 1 or opcao > len(lista_medicos):
            print("\nOpção inválida!")
            return

        medico_selecionado = lista_medicos[opcao - 1]

    except ValueError:
        print("\nDigite um número válido!")
        return

    anamnese = input("\nAnamnese: ").strip()
    diagnostico = input("Diagnóstico: ").strip()
    prescricao = input("Prescrição: ").strip()

    try:
        Prontuario.objects.create(
            paciente=paciente,
            medico=medico_selecionado,
            anamnese=anamnese,
            diagnostico=diagnostico,
            prescricao=prescricao
        )

        print("\nProntuário cadastrado com sucesso!")

    except Exception as erro:
        print(f"\nErro ao cadastrar prontuário: {erro}")
