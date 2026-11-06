from tabulate import tabulate
from sistema_clinica.usuario.cadastro_usuarios import *

def listar_usuarios():

    print("\n========== USUÁRIOS CADASTRADOS ==========")

    if not usuarios:
        print("Nenhum usuário cadastrado!")
        return

    perfis = {
        "Administrador": [],
        "Médico": [],
        "Recepção": [],
        "Paciente": []
    }

    for usuario in usuarios:
        perfil = usuario["perfil"]

        if perfil in perfis:
            perfis[perfil].append(usuario)

    for perfil, lista_usuarios in perfis.items():

        print(f"\n========== {perfil.upper()} ==========")

        if not lista_usuarios:
            print(f"Nenhum usuário com perfil {perfil} cadastrado!")
            continue

        tabela = []

        for i, usuario in enumerate(lista_usuarios, start=1):
            tabela.append([
                i,
                usuario["nome"],
                usuario["email"],
                usuario["perfil"]
            ])

        cabecalho = ["ID", "Nome", "E-mail", "Perfil"]

        print(tabulate(tabela, headers=cabecalho, tablefmt="grid"))