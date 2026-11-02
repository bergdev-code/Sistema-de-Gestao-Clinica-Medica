pacientes = []

def cadastrar_paciente():
    print("\n===== CADASTRO DE PACIENTE =====")

    print("\n--- DADOS PESSOAIS ---")
    nome = input("Nome completo: ")
    cpf = input("CPF: ")
    data_nascimento = input("Data de nascimento: ")
    telefone = input("Telefone: ")

    print("\n--- HISTÓRICO MÉDICO ---")
    historico_medico = input("Histórico médico: ")

    print("\n--- ALERGIAS ---")
    alergias = input("Possui alergias? Quais? ")

    paciente = {
        "nome": nome,
        "cpf": cpf,
        "data_nascimento": data_nascimento,
        "telefone": telefone,
        "historico_medico": historico_medico,
        "alergias": alergias
    }

    pacientes.append(paciente)

    print("\nPaciente cadastrado com sucesso!")
    