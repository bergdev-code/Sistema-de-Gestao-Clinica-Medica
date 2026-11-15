from tabulate import tabulate

from sistema_clinica.prontuarios.cadastro_prontuarios import prontuarios


def listar_prontuarios():
    print("\n===== PRONTUÁRIOS REGISTRADOS =====")

    if not prontuarios:
        print("Nenhum prontuário registrado!")
        return

    tabela = []

    for i, prontuario in enumerate(prontuarios, start=1):
        tabela.append([
            i,
            prontuario["paciente"],
            prontuario["cpf"],
            prontuario["medico"],
            prontuario["data"],
            prontuario["diagnostico"],
        ])

    cabecalho = ["Nº", "Paciente", "CPF", "Médico", "Data", "Diagnóstico"]

    print(tabulate(tabela, headers=cabecalho, tablefmt="grid"))
