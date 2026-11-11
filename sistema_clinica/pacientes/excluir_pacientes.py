from func_django.models import func_django


def excluir_paciente():

    print("\n========== EXCLUIR PACIENTE ==========")

    cpf = input("Informe o CPF do paciente: ").strip()

    paciente = func_django.objects.filter(cpf=cpf).first()

    if paciente is None:
        print("\nPaciente não encontrado!")
        return

    print("\nPaciente encontrado:")
    print(f"Nome: {paciente.nome}")
    print(f"CPF: {paciente.cpf}")

    confirmacao = input("\nDeseja realmente excluir? (S/N): ").strip().upper()

    if confirmacao == "S":

        paciente.delete()

        print("\nPaciente excluído com sucesso!")

    else:
        print("\nExclusão cancelada!")
