from func_django.models import Pagamento


def excluir_pagamento():
    print("\n===== EXCLUIR PAGAMENTO =====")

    pagamentos = Pagamento.objects.select_related(
        "agendamento__paciente",
        "status_pagamento"
    ).all()

    if not pagamentos.exists():
        print("\nNenhum pagamento registrado!")
        return

    pagamentos_lista = list(pagamentos)

    for i, pagamento in enumerate(pagamentos_lista, start=1):
        paciente = pagamento.agendamento.paciente

        print(f"\n--- PAGAMENTO {i} ---")
        print(f"ID: {pagamento.id_pagamento}")
        print(f"Paciente: {paciente.nome}")
        print(f"CPF: {paciente.cpf}")
        print(f"Descrição: {pagamento.descricao}")
        print(f"Valor: R$ {pagamento.valor:.2f}")
        print(f"Forma: {pagamento.forma_pagamento}")
        print(f"Status: {pagamento.status_pagamento.descricao}")
        print(f"Data: {pagamento.data_pagamento.strftime('%d/%m/%Y')}")

    try:
        opcao = int(
            input("\nDigite o número do pagamento que deseja excluir: ")
        )

        if opcao < 1 or opcao > len(pagamentos_lista):
            print("\nPagamento não encontrado!")
            return

        pagamento_selecionado = pagamentos_lista[opcao - 1]

    except ValueError:
        print("\nDigite um número válido!")
        return

    confirmacao = input(
        "\nDeseja realmente excluir este pagamento? (S/N): "
    ).strip().upper()

    if confirmacao != "S":
        print("\nExclusão cancelada!")
        return

    pagamento_selecionado.delete()

    print("\nPagamento excluído com sucesso!")