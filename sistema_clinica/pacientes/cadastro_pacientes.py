pacientes = []

def cadastrar_paciente():
    print("\n===== CADASTRO DE PACIENTE =====")

    print("\n--- DADOS PESSOAIS ---")
    nome = input("Nome completo: ")
    cpf = input("CPF: ")
    data_nascimento = input("Data de nascimento: ")
    telefone = input("Telefone: ")

    paciente = {
        "nome": nome,
        "cpf": cpf,
        "data_nascimento": data_nascimento,
        "telefone": telefone
    }

    pacientes.append(paciente)

    print("\nPaciente cadastrado com sucesso!")
    