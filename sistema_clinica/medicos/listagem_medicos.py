from tabulate import tabulate
from sistema_clinica.medicos.cadastro_medicos import *



def listar_medicos():
    print("\n=== MÉDICOS CADASTRADOS ===")

    if not medicos:
        print("Nenhum médico cadastrado!")
        return

    tabela = []

    for i, medico in enumerate(medicos, start=1):
        tabela.append([
            i,
            medico['nome'],
            medico['crm'],
            medico['especialidade'],
            medico['horario']
        ])

    cabecalho = ["ID", "Nome", "CRM", "Especialidade", "Horário"]

    print(tabulate(tabela, headers=cabecalho, tablefmt="grid"))
