from sistema_clinica.financeiro.cadastro_pagamentos import pagamentos


def excluir_pagamento():
    print("\n===== EXCLUIR PAGAMENTO =====")

    if not pagamentos:
        print("Nenhum pagamento registrado!")
        return

    for i, pagamento in enumerate(pagamentos, start=1):
        print(f"\n--- PAGAMENTO {i} ---")
        print(f"Paciente: {pagamento['paciente']}")
        print(f"CPF: {pagamento['cpf']}")
        print(f"Descrição: {pagamento['descricao']}")
        print(f"Valor: R$ {pagamento['valor']:.2f}")
        print(f"Forma: {pagamento['forma']}")
        print(f"Status: {pagamento['status']}")
        print(f"Data: {pagamento['data']}")

    try:
        opcao = int(input("\nDigite o número do pagamento que deseja excluir: "))

        if opcao < 1 or opcao > len(pagamentos):
            print("\nPagamento não encontrado!")
            return

        pagamento_removido = pagamentos.pop(opcao - 1)

        print("\nPagamento excluído com sucesso!")
        print(f"Paciente: {pagamento_removido['paciente']}")
        print(f"Descrição: {pagamento_removido['descricao']}")

    except ValueError:
        print("\nDigite um número válido!")
