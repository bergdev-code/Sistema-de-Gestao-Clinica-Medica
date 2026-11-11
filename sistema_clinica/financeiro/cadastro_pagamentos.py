from sistema_clinica.pacientes.cadastro_pacientes import func_django

pagamentos = []

FORMAS = {
    "1": "Dinheiro",
    "2": "Pix",
    "3": "Cartão",
    "4": "Convênio",
}

STATUS = {
    "1": "Pago",
    "2": "Pendente",
}


def registrar_pagamento():
    print("\n===== REGISTRO DE PAGAMENTO =====")

    if not func_django:
        print("Nenhum paciente cadastrado!")
        return

    cpf = input("CPF do paciente: ")

    paciente_selecionado = next(
        (p for p in func_django if p["cpf"] == cpf),
        None
    )

    if paciente_selecionado is None:
        print("Paciente não encontrado!")
        return

    descricao = input("Descrição (consulta, exame, etc.): ").strip()

    if not descricao:
        print("Descrição inválida!")
        return

    try:
        valor = float(input("Valor: ").replace(",", "."))
    except ValueError:
        print("\nDigite um valor válido!")
        return

    if valor <= 0:
        print("\nO valor deve ser maior que zero!")
        return

    print("\nFormas de pagamento:")
    print("1 - Dinheiro")
    print("2 - Pix")
    print("3 - Cartão")
    print("4 - Convênio")

    forma = input("Selecione a forma: ")

    if forma not in FORMAS:
        print("Forma de pagamento inválida!")
        return

    print("\nStatus:")
    print("1 - Pago")
    print("2 - Pendente")

    status = input("Selecione o status: ")

    if status not in STATUS:
        print("Status inválido!")
        return

    data = input("Data do pagamento: ")

    pagamento = {
        "id": len(pagamentos) + 1,
        "paciente": paciente_selecionado["nome"],
        "cpf": paciente_selecionado["cpf"],
        "descricao": descricao,
        "valor": valor,
        "forma": FORMAS[forma],
        "status": STATUS[status],
        "data": data,
    }

    pagamentos.append(pagamento)

    print("\nPagamento registrado com sucesso!")
