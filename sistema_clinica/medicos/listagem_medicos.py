
from tabulate import tabulate
from func_django.models import Medico, MedicoEspecialidade, HorarioMedico


def listar_medicos():
    print("\n=== MÉDICOS CADASTRADOS ===")

    medicos = Medico.objects.filter(ativo=True).order_by("nome")

    if not medicos.exists():
        print("Nenhum médico cadastrado!")
        return

    tabela = []

    for i, medico in enumerate(medicos, start=1):

        # Busca as especialidades vinculadas ao médico
        especialidades = MedicoEspecialidade.objects.filter(
            medico=medico
        ).select_related("especialidade")

        nomes_especialidades = [
            item.especialidade.nome for item in especialidades
        ]

        especialidade = (
            ", ".join(nomes_especialidades)
            if nomes_especialidades
            else "Não informada"
        )

        # Busca os horários cadastrados para o médico
        horarios = HorarioMedico.objects.filter(medico=medico)

        lista_horarios = [
            f"{horario.dia_semana}: "
            f"{horario.hora_inicio.strftime('%H:%M')} às "
            f"{horario.hora_fim.strftime('%H:%M')}"
            for horario in horarios
        ]

        horario = (
            "\n".join(lista_horarios)
            if lista_horarios
            else "Não informado"
        )

        tabela.append([
            i,
            medico.nome,
            medico.crm,
            especialidade,
            horario
        ])

    cabecalho = [
        "ID",
        "Nome",
        "CRM",
        "Especialidade",
        "Horário"
    ]

    print(tabulate(tabela, headers=cabecalho, tablefmt="grid"))
