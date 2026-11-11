from tabulate import tabulate
from func_django.models import func_django


def listar_pacientes():

    print("\n========== PACIENTES CADASTRADOS ==========\n")

    # Buscar pacientes diretamente no banco de dados
    pacientes = func_django.objects.all()

    # Verificar se existem registros
    if not pacientes.exists():
        print("Nenhum paciente cadastrado!")
        return

    # Organizar os dados em uma tabela
    tabela = []

    for paciente in pacientes:
        tabela.append([
            paciente.nome,
            paciente.cpf,
            paciente.data_nascimento,
            paciente.telefone
        ])

    # Exibir os resultados
    cabecalho = ["NOME", "CPF", "DATA DE NASCIMENTO", "TELEFONE"]

    print(tabulate(
        tabela,
        headers=cabecalho,
        tablefmt="grid"
    ))
