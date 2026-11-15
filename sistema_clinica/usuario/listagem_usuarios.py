
from tabulate import tabulate

from func_django.models import Usuario


def listar_usuarios():

    print("\n========== USUÁRIOS CADASTRADOS ==========")

    # Buscar usuários no banco de dados
    usuarios = Usuario.objects.select_related(
        'id_perfil'
    ).order_by('id_perfil__nome_perfil', 'username')

    if not usuarios.exists():
        print("Nenhum usuário cadastrado!")
        return

    # Agrupar usuários por perfil
    perfis = {}

    for usuario in usuarios:
        nome_perfil = usuario.id_perfil.nome_perfil

        if nome_perfil not in perfis:
            perfis[nome_perfil] = []

        perfis[nome_perfil].append(usuario)

    # Exibir usuários por perfil
    for perfil, lista_usuarios in perfis.items():

        print(f"\n========== {perfil.upper()} ==========")

        tabela = []

        for i, usuario in enumerate(lista_usuarios, start=1):

            tabela.append([
                usuario.id_usuario,
                usuario.username,
                usuario.email,
                perfil
            ])

        cabecalho = ["ID", "Username", "E-mail", "Perfil"]

        print(tabulate(
            tabela,
            headers=cabecalho,
            tablefmt="grid"
        ))
