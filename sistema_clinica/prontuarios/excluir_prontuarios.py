
from func_django.models import Prontuario


def excluir_prontuario():

    print("\n===== EXCLUIR PRONTUÁRIO =====")

    prontuarios = Prontuario.objects.select_related(
        "paciente"
    ).all().order_by("id_prontuario")

    if not prontuarios.exists():
        print("Nenhum prontuário registrado!")
        return

    for prontuario in prontuarios:

        print(f"\n--- PRONTUÁRIO {prontuario.id_prontuario} ---")
        print(f"Paciente: {prontuario.paciente.nome}")
        print(f"CPF: {prontuario.paciente_id}")
        print(f"Médico (CRM): {prontuario.medico_id}")
        print(f"Diagnóstico: {prontuario.diagnostico}")

    try:
        opcao = int(
            input("\nDigite o ID do prontuário que deseja excluir: ")
        )

    except ValueError:
        print("\nDigite um número válido!")
        return

    prontuario = Prontuario.objects.filter(
        id_prontuario=opcao
    ).first()

    if prontuario is None:
        print("\nProntuário não encontrado!")
        return

    confirmacao = input(
        "\nDeseja realmente excluir? (S/N): "
    ).strip().upper()

    if confirmacao != "S":
        print("\nExclusão cancelada!")
        return

    paciente_nome = prontuario.paciente.nome

    prontuario.delete()

    print("\nProntuário excluído com sucesso!")
    print(f"Paciente: {paciente_nome}")
