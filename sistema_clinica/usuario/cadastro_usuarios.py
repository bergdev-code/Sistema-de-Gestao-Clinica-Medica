import hashlib
import secrets
from getpass import getpass

usuarios = []

def cadastrar_usuario():
    print("\n=== CADASTRO DE USUÁRIO ===")

    nome = input("Nome completo: ")
    email = input("E-mail: ")
    senha = input("Senha: ")

    print("\nPerfis disponíveis:")
    print("1 - Administrador")
    print("2 - Médico")
    print("3 - Recepção")
    print("4 - Paciente")

    opcao = input("Selecione o perfil: ")

    perfis = {
        "1": "Administrador",
        "2": "Médico",
        "3": "Recepção",
        "4": "Paciente"
    }

    if opcao not in perfis:
        print("Perfil inválido!")
        return

    for usuario in usuarios:
        if usuario["email"] == email:
            print("E-mail já cadastrado!")
            return

    salt = secrets.token_bytes(16)
    senha_hash = hashlib.pbkdf2_hmac(
        "sha256", senha.encode(), salt, 600000
    ).hex()

    usuario = {
        "nome": nome,
        "email": email,
        "senha": senha_hash,
        "salt": salt.hex(),
        "perfil": perfis[opcao]
    }

    usuarios.append(usuario)

    print("\nUsuário cadastrado com sucesso!")