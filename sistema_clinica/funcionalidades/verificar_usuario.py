
import hashlib
import hmac

from sistema_clinica.usuario.cadastro_usuarios import Usuario


U_user = "root"
U_senha = "root@123"


def verificar_email():

    tentativas = 3

    while tentativas > 0:

        print("\n========== LOGIN ==========")

        v_email = input("EMAIL: ").strip().lower()
        v_senha = input("SENHA: ")

        # LOGIN DO ADMINISTRADOR GERAL
        if v_email == U_user and v_senha == U_senha:
            return ("root", "ADMIN GERAL")

        # BUSCAR USUÁRIO NO BANCO DE DADOS
        usuario = Usuario.objects.filter(
            email__iexact=v_email
        ).select_related("id_perfil").first()

        if usuario is not None:

            # RECUPERAR O SALT
            salt = bytes.fromhex(usuario.salt)

            # GERAR HASH DA SENHA INFORMADA
            senha_hash = hashlib.pbkdf2_hmac(
                "sha256",
                v_senha.encode(),
                salt,
                600000
            ).hex()

            # COMPARAR OS HASHES
            if hmac.compare_digest(
                senha_hash,
                usuario.senha_hash
            ):

                return (
                    usuario.username,
                    usuario.id_perfil.nome_perfil
                )

        # LOGIN INVÁLIDO
        tentativas -= 1

        print("\nE-mail ou senha incorretos!")

        if tentativas > 0:
            print(f"Tentativas restantes: {tentativas}")

        else:
            print("\nAcesso bloqueado! Limite de tentativas excedido.")

    return None