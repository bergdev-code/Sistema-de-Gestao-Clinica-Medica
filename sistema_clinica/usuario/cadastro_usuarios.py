
import hashlib
import secrets
from getpass import getpass

from sistema_clinica.funcionalidades.regex import (
    validar_nome,
    validar_email,
    validar_senha
)

from func_django.models import Usuario, Perfil, Medico


def cadastrar_usuario():

    print("\n========== CADASTRO DE USUÁRIO ==========")

    # Username
    while True:
        username = input("Nome de usuário: ").strip()

        if not validar_nome(username):
            print("Nome de usuário inválido!")
            continue

        if len(username) > 10:
            print("O username deve possuir no máximo 10 caracteres!")
            continue

        if Usuario.objects.filter(username=username).exists():
            print("Nome de usuário já cadastrado!")
            continue

        break

    # E-mail
    while True:
        email = input("E-mail: ").strip().lower()

        if not validar_email(email):
            print("E-mail inválido!")
            continue

        if Usuario.objects.filter(email=email).exists():
            print("E-mail já cadastrado!")
            continue

        break

    # Senha
    while True:
        senha = getpass("Senha: ")

        if validar_senha(senha):
            break

        print("Senha inválida! Mínimo de 8 caracteres.")

    # Seleção de perfil
    print("\n========== PERFIS DISPONÍVEIS ==========")

    perfis = Perfil.objects.all().order_by('id_perfil')

    if not perfis.exists():
        print("Nenhum perfil cadastrado!")
        return

    for perfil_disponivel in perfis:
        print(
            f"{perfil_disponivel.id_perfil} - "
            f"{perfil_disponivel.nome_perfil}"
        )

    try:
        opcao = int(input("\nSelecione o perfil: "))
    except ValueError:
        print("Opção inválida!")
        return

    perfil = Perfil.objects.filter(id_perfil=opcao).first()

    if not perfil:
        print("Perfil não encontrado!")
        return

    # VINCULAR MÉDICO
    medico = None

    if perfil.nome_perfil == "Médico":

        medicos = Medico.objects.filter(ativo=True).order_by("nome")

        if not medicos.exists():
            print("\nNenhum médico ativo encontrado!")
            return

        medicos_disponiveis = list(
            medicos.exclude(
                crm__in=Usuario.objects.filter(
                    medico__isnull=False
                ).values_list("medico__crm", flat=True)
            )
        )

        if not medicos_disponiveis:
            print("\nTodos os médicos ativos já possuem usuário vinculado!")
            return

        print("\n========== MÉDICOS DISPONÍVEIS ==========")

        for i, profissional in enumerate(medicos_disponiveis, start=1):
            print(
                f"{i} - {profissional.nome} "
                f"| CRM: {profissional.crm}"
            )

        try:
            opcao_medico = int(input("\nSelecione o médico: "))
        except ValueError:
            print("Opção inválida!")
            return

        if opcao_medico < 1 or opcao_medico > len(medicos_disponiveis):
            print("Opção inválida!")
            return

        medico = medicos_disponiveis[opcao_medico - 1]

    # Gerar salt
    salt = secrets.token_bytes(16)

    # Gerar hash da senha
    senha_hash = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt,
        600000
    ).hex()

    # Salvar usuário
    try:

        Usuario.objects.create(
            username=username,
            email=email,
            senha_hash=senha_hash,
            salt=salt.hex(),
            id_perfil=perfil,
            medico=medico
        )

        print("\nUsuário cadastrado com sucesso!")

    except Exception as erro:
        print(f"\nErro ao cadastrar usuário: {erro}")
