import hashlib
import secrets
from getpass import getpass

from sistema_clinica.funcionalidades.regex import validar_nome, validar_email, validar_senha

usuarios = []

def cadastrar_usuario():
    print("\n=== CADASTRO DE USUÁRIO ===")

    while True:
        nome = input("Nome completo: ")

        if validar_nome(nome):
            break
        else:
            print("Nome inválido! Tente novamente.")

    while True:
        email = input("E-mail: ").strip().lower()

        if validar_email(email):
            break
        else:
            print("E-mail inválido! Tente novamente.")

    for usuario in usuarios:
        if usuario["email"] == email:
            print("E-mail já cadastrado!")
            return

    while True:
        senha = input("Senha: ")

        if validar_senha(senha):
            break
        else:
            print("Senha inválida! Mínimo de 8 caracteres.")

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
