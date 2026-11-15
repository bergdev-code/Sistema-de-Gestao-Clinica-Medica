
from func_django.models import Usuario


def excluir_usuarios():

    print("\n========== EXCLUIR USUÁRIOS ==========")

    # Buscar usuários no banco de dados
    usuarios = Usuario.objects.select_related(
        'id_perfil'
    ).order_by('id_usuario')

    if not usuarios.exists():
        print("Nenhum usuário cadastrado!")
        return

    # Listar usuários
    for usuario in usuarios:

        print(f"\n--- USUÁRIO ID: {usuario.id_usuario} ---")
        print(f"Username: {usuario.username}")
        print(f"E-mail: {usuario.email}")
        print(f"Perfil: {usuario.id_perfil.nome_perfil}")

    # Solicitar ID do usuário
    try:
        opcao = int(input(
            "\nDigite o ID do usuário que deseja excluir: "
        ))

    except ValueError:
        print("\nDigite um número válido!")
        return

    # Localizar usuário no banco
    usuario = Usuario.objects.filter(
        id_usuario=opcao
    ).select_related('id_perfil').first()

    if not usuario:
        print("\nUsuário não encontrado!")
        return

    # Confirmar exclusão
    confirmacao = input(
        f"\nDeseja realmente excluir o usuário "
        f"'{usuario.username}'? (s/n): "
    ).strip().lower()

    if confirmacao != 's':
        print("\nExclusão cancelada!")
        return

    # Excluir registro
    username = usuario.username

    usuario.delete()

    print("\nUsuário excluído com sucesso!")
    print(f"Usuário removido: {username}")
