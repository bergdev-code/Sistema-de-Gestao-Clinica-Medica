import hashlib
import hmac

from sistema_clinica.usuario.cadastro_usuarios import usuarios

U_user = "root"
U_senha = "root@123"


def verificar_email():

    tentativas = 3

    while tentativas > 0:

        print("\n========== LOGIN ==========")

        v_email = input("USER: ").strip().lower()
        v_senha = input("SENHA: ")

        if v_email == U_user and v_senha == U_senha:
            return "ADMIN GERAL"

        autenticado = False

        for v_usuario in usuarios:

            if v_usuario["email"] == v_email:

                salt = bytes.fromhex(v_usuario["salt"])

                senha_hash = hashlib.pbkdf2_hmac(
                    "sha256",
                    v_senha.encode(),
                    salt,
                    600000
                ).hex()

                if hmac.compare_digest(
                    senha_hash,
                    v_usuario["senha"]
                ):
                    return v_usuario["perfil"]

                autenticado = True
                break

        tentativas -= 1

        print("\nE-mail ou senha incorretos!")

        if tentativas > 0:
            print(f"Tentativas restantes: {tentativas}")
        else:
            print("Acesso bloqueado! Limite de tentativas excedido.")

    return None
