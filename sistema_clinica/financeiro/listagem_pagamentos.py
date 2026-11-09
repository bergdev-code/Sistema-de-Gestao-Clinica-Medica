from tabulate import tabulate

from sistema_clinica.financeiro.cadastro_pagamentos import pagamentos


def listar_pagamentos():
    print("\n===== PAGAMENTOS REGISTRADOS =====")

    if not pagamentos:
        print("Nenhum pagamento registrado!")
        return

    tabela = []

    for i, pagamento in enumerate(pagamentos, start=1):
        tabela.append([
            i,
            pagamento["paciente"],
            pagamento["cpf"],
            pagamento["descricao"],
            f"R$ {pagamento['valor']:.2f}",
            pagamento["forma"],
            pagamento["status"],
            pagamento["data"],
        ])

    cabecalho = [
        "Nº",
        "Paciente",
        "CPF",
        "Descrição",
        "Valor",
        "Forma",
        "Status",
        "Data",
    ]

    print(tabulate(tabela, headers=cabecalho, tablefmt="grid"))


def resumo_financeiro():
    print("\n===== RESUMO FINANCEIRO =====")

    if not pagamentos:
        print("Nenhum pagamento registrado!")
        return

    total_pago = sum(
        pagamento["valor"]
        for pagamento in pagamentos
        if pagamento["status"] == "Pago"
    )
    total_pendente = sum(
        pagamento["valor"]
        for pagamento in pagamentos
        if pagamento["status"] == "Pendente"
    )

    print(f"Quantidade de registros: {len(pagamentos)}")
    print(f"Total recebido: R$ {total_pago:.2f}")
    print(f"Total pendente: R$ {total_pendente:.2f}")
    print(f"Total geral: R$ {total_pago + total_pendente:.2f}")
