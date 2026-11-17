
from func_django.models import Medico


def excluir_medico():
    print("\n===== EXCLUIR MÉDICO =====")

    medicos = Medico.objects.filter(ativo=True).order_by("nome")

    if not medicos.exists():
        print("Nenhum médico ativo cadastrado!")
        return

    lista_medicos = list(medicos)

    for i, medico in enumerate(lista_medicos, start=1):
        print(f"\n--- MÉDICO {i} ---")
        print(f"Nome: {medico.nome}")
        print(f"CRM: {medico.crm}")
        print(f"Telefone: {medico.telefone}")
        print(f"Status: {'Ativo' if medico.ativo else 'Inativo'}")

    try:
        opcao = int(input("\nDigite o número do médico que deseja excluir: "))

        if opcao < 1 or opcao > len(lista_medicos):
            print("\nMédico não encontrado!")
            return

        medico_selecionado = lista_medicos[opcao - 1]

        confirmacao = input(
            f"\nDeseja realmente excluir o médico "
            f"{medico_selecionado.nome}? (S/N): "
        ).strip().upper()

        if confirmacao != "S":
            print("\nOperação cancelada!")
            return

        # Desativa o médico em vez de apagar seu registro
        medico_selecionado.ativo = False
        medico_selecionado.save(update_fields=["ativo"])

        print("\nMédico desativado com sucesso!")
        print(f"Médico: {medico_selecionado.nome}")

    except ValueError:
        print("\nDigite um número válido!")

    except Exception as erro:
        print(f"\nErro ao desativar médico: {erro}")
