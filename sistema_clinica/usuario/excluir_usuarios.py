from sistema_clinica.usuario.cadastro_usuarios import usuarios

def excluir_usuarios():
    print("\n===== EXCLUIR USUÁRIOS =====")

    if not usuarios:
        print("Nenhum usuário cadastrado!")
        return

    for i, usuario in enumerate(usuarios, start=1):
        print(f"\n--- USUÁRIO {i} ---")
        print(f"Nome: {usuario['nome']}")
        print(f"E-mail: {usuario['email']}")
        print(f"Perfil: {usuario['perfil']}")

    try:
        opcao = int(input(
            "\nDigite o número do usuário que deseja excluir: "
        ))

        if opcao < 1 or opcao > len(usuarios):
            print("\nUsuário não encontrado!")
            return

        usuario_removido = usuarios.pop(opcao - 1)

        print("\nUsuário excluído com sucesso!")
        print(f"Usuário removido: {usuario_removido['nome']}")

    except ValueError:
        print("\nDigite um número válido!")
