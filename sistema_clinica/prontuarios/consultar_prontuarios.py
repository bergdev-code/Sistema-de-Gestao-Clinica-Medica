
from func_django.models import Prontuario


def _exibir_prontuario(numero, prontuario):

    print(f"\n--- PRONTUÁRIO {numero} ---")
    print(f"Paciente: {prontuario.paciente.nome}")
    print(f"CPF: {prontuario.paciente_id}")
    print(f"Médico (CRM): {prontuario.medico_id}")
    print(f"Anamnese / Queixa: {prontuario.anamnese}")
    print(f"Diagnóstico: {prontuario.diagnostico}")
    print(f"Prescrição: {prontuario.prescricao}")


def consultar_prontuario():

    print("\n===== CONSULTAR PRONTUÁRIO =====")

    cpf = input("CPF do paciente: ").strip()

    if not cpf:
        print("\nCPF inválido!")
        return

    encontrados = Prontuario.objects.filter(
        paciente_id=cpf
    ).select_related("paciente").order_by("id_prontuario")

    if not encontrados.exists():
        print("\nNenhum prontuário encontrado para este paciente!")
        return

    print(f"\n{encontrados.count()} prontuário(s) encontrado(s).")

    for i, prontuario in enumerate(encontrados, start=1):
        _exibir_prontuario(i, prontuario)
