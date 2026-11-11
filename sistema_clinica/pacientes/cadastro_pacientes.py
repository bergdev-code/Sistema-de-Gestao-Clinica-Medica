from func_django.models import func_django
from datetime import datetime

def cadastrar_paciente():

    print("\n===== CADASTRO DE PACIENTE =====")

    print("\n--- DADOS PESSOAIS ---")
    nome = input("Nome completo: ")
    cpf = input("CPF: ")
    data_nascimento = input("Data de nascimento (DD/MM/AAAA): ")
    telefone = input("Telefone: ")

    try:
        data_nascimento = datetime.strptime(
            data_nascimento, "%d/%m/%Y"
        ).date()

        func_django.objects.create(
            nome=nome,
            cpf=cpf,
            data_nascimento=data_nascimento,
            telefone=telefone
        )

        print("\nPaciente cadastrado com sucesso!")

    except ValueError:
        print("\nData de nascimento inválida!")

    except Exception as erro:
        print(f"\nErro ao cadastrar: {erro}")
