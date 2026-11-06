medicos = []

def cadastrar_medico():
    print("\n=== CADASTRO DE MÉDICO ===")

    medico = {
        "nome": input("Nome: "),
        "crm": input("CRM: "),
        "especialidade": input("Especialidade: "),
        "horario": input("Horário de atendimento: ")
    }

    medicos.append(medico)

    print("\nMédico cadastrado com sucesso!")