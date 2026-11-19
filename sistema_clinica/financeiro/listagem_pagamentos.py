from tabulate import tabulate

from func_django.models import Pagamento


def listar_pagamentos():
    print("\n===== PAGAMENTOS REGISTRADOS =====")

    pagamentos = Pagamento.objects.select_related(
        "agendamento__paciente",
        "status_pagamento"
    ).all()

    if not pagamentos.exists():
        print("\nNenhum pagamento registrado!")
        return

    tabela = []

    for i, pagamento in enumerate(pagamentos, start=1):
        paciente = pagamento.agendamento.paciente

        tabela.append([
            i,
            paciente.nome,
            paciente.cpf,
            pagamento.descricao,
            f"R$ {pagamento.valor:.2f}",
            pagamento.forma_pagamento,
            pagamento.status_pagamento.descricao,
            pagamento.data_pagamento.strftime("%d/%m/%Y"),
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

    pagamentos = Pagamento.objects.select_related(
        "status_pagamento"
    ).all()

    if not pagamentos.exists():
        print("\nNenhum pagamento registrado!")
        return

    total_pago = sum(
        (p.valor for p in pagamentos
         if p.status_pagamento.descricao == "Concluído"),
        start=0
    )

    total_pendente = sum(
        (p.valor for p in pagamentos
         if p.status_pagamento.descricao == "Pendente"),
        start=0
    )

    total_cancelado = sum(
        (p.valor for p in pagamentos
         if p.status_pagamento.descricao == "Cancelado"),
        start=0
    )

    total_geral = total_pago + total_pendente + total_cancelado

    print(f"Quantidade de registros: {pagamentos.count()}")
    print(f"Total recebido: R$ {total_pago:.2f}")
    print(f"Total pendente: R$ {total_pendente:.2f}")
    print(f"Total cancelado: R$ {total_cancelado:.2f}")
    print(f"Total geral: R$ {total_geral:.2f}")