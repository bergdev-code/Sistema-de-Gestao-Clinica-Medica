from datetime import datetime
from decimal import Decimal, InvalidOperation

from func_django.models import (
    func_django,
    Agendamento,
    Pagamento,
    StatusPagamento,
)


FORMAS = {
    "1": "Dinheiro",
    "2": "Pix",
    "3": "Cartão",
    "4": "Convênio",
}

STATUS = {
    "1": "Concluído",
    "2": "Pendente",
    "3": "Cancelado",
}


def registrar_pagamento():
    print("\n===== REGISTRO DE PAGAMENTO =====")

    cpf = input("CPF do paciente: ").strip()

    try:
        paciente = func_django.objects.get(cpf=cpf)

    except func_django.DoesNotExist:
        print("\nPaciente não encontrado!")
        return

    agendamentos = Agendamento.objects.filter(
        paciente=paciente
    )

    if not agendamentos.exists():
        print("\nNenhum agendamento encontrado!")
        return

    print("\n===== AGENDAMENTOS DO PACIENTE =====")

    for agendamento in agendamentos:
        print(
            f"ID: {agendamento.id_agendamento} | "
            f"Data: {agendamento.data_hora}"
        )

    try:
        id_agendamento = int(
            input("\nID do agendamento: ")
        )

    except ValueError:
        print("\nID inválido!")
        return

    agendamento_selecionado = agendamentos.filter(
        id_agendamento=id_agendamento
    ).first()

    if agendamento_selecionado is None:
        print("\nAgendamento não encontrado!")
        return

    descricao = input(
        "Descrição (consulta, exame, etc.): "
    ).strip()

    if not descricao:
        print("\nDescrição inválida!")
        return

    try:
        valor = Decimal(
            input("Valor: ").replace(",", ".")
        )

    except InvalidOperation:
        print("\nDigite um valor válido!")
        return

    if not valor.is_finite() or valor <= 0:
        print("\nO valor deve ser maior que zero!")
        return

    if valor.as_tuple().exponent < -2:
        print("\nO valor deve possuir no máximo duas casas decimais!")
        return

    print("\n===== FORMAS DE PAGAMENTO =====")

    for codigo, nome in FORMAS.items():
        print(f"{codigo} - {nome}")

    forma = input("Selecione a forma: ").strip()

    if forma not in FORMAS:
        print("\nForma de pagamento inválida!")
        return

    print("\n===== STATUS DO PAGAMENTO =====")

    for codigo, nome in STATUS.items():
        print(f"{codigo} - {nome}")

    status = input("Selecione o status: ").strip()

    if status not in STATUS:
        print("\nStatus inválido!")
        return

    data = input(
        "Data do pagamento (DD/MM/AAAA): "
    ).strip()

    try:
        data_convertida = datetime.strptime(
            data, "%d/%m/%Y"
        ).date()

    except ValueError:
        print("\nData inválida!")
        return

    try:
        status_selecionado = StatusPagamento.objects.get(
            descricao=STATUS[status]
        ) 

        Pagamento.objects.create(
            agendamento=agendamento_selecionado,
            descricao=descricao,
            valor=valor,
            forma_pagamento=FORMAS[forma],
            status_pagamento=status_selecionado,
            data_pagamento=data_convertida,
        )

    except StatusPagamento.DoesNotExist:
        print("\nStatus não encontrado no banco de dados!")
        return

    print("\nPagamento registrado com sucesso!")