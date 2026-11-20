
import hashlib
import hmac
from functools import wraps

from django.contrib import messages
from django.shortcuts import render, redirect

from func_django.models import Usuario


# Credenciais do administrador geral
U_user = "root"
U_senha = "root@123"


def verificar_senha(senha_digitada, senha_hash, salt):
    """
    Verifica se a senha informada corresponde ao hash armazenado.
    Utiliza o mesmo algoritmo do cadastro de usuários.
    """
    try:
        salt_bytes = bytes.fromhex(salt)

        hash_gerado = hashlib.pbkdf2_hmac(
            "sha256",
            senha_digitada.encode("utf-8"),
            salt_bytes,
            600000
        ).hex()

        return hmac.compare_digest(hash_gerado, senha_hash)

    except (ValueError, TypeError):
        return False


def login_view(request):

    if request.session.get("usuario_id") or request.session.get("admin_geral"):
        return redirect("dashboard")

    tentativas = request.session.get("tentativas_login", 0)

    if tentativas >= 3:
        messages.error(
            request,
            "Acesso bloqueado! Limite de tentativas excedido."
        )
        return render(request, "autenticacao/login.html")

    if request.method == "POST":

        email = request.POST.get("identificador", "").strip().lower()
        senha = request.POST.get("senha", "")
        lembrar = request.POST.get("lembrar") == "on"

        if not email or not senha:
            messages.error(request, "Preencha o e-mail e a senha.")
            return render(request, "autenticacao/login.html")

        # LOGIN DO ADMINISTRADOR GERAL
        if email == U_user and senha == U_senha:

            request.session.cycle_key()

            request.session["usuario_id"] = None
            request.session["username"] = "root"
            request.session["email"] = "root"
            request.session["perfil"] = "ADMIN GERAL"
            request.session["admin_geral"] = True

            request.session.pop("tentativas_login", None)

            request.session.set_expiry(1209600 if lembrar else 0)

            messages.success(request, "Login realizado com sucesso!")
            return redirect("dashboard")

        # BUSCAR USUÁRIO NO BANCO
        usuario = Usuario.objects.filter(
            email__iexact=email
        ).select_related("id_perfil").first()

        # VERIFICAR SENHA
        if usuario and verificar_senha(
            senha,
            usuario.senha_hash,
            usuario.salt
        ):

            request.session.cycle_key()

            request.session["usuario_id"] = usuario.id_usuario
            request.session["username"] = usuario.username
            request.session["email"] = usuario.email
            request.session["perfil"] = usuario.id_perfil.nome_perfil
            request.session["admin_geral"] = False

            request.session.pop("tentativas_login", None)

            request.session.set_expiry(1209600 if lembrar else 0)

            messages.success(request, "Login realizado com sucesso!")
            return redirect("dashboard")

        # LOGIN INVÁLIDO
        tentativas += 1
        request.session["tentativas_login"] = tentativas

        if tentativas >= 3:
            messages.error(
                request,
                "Acesso bloqueado! Limite de tentativas excedido."
            )
        else:
            restantes = 3 - tentativas
            messages.error(
                request,
                f"E-mail ou senha incorretos! "
                f"Tentativas restantes: {restantes}."
            )

    return render(request, "autenticacao/login.html")


def usuario_autenticado(view_func):
    """
    Impede o acesso às páginas protegidas sem login.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.session.get("usuario_id") and not request.session.get("admin_geral"):
            messages.warning(request, "Faça login para acessar o sistema.")
            return redirect("login")

        return view_func(request, *args, **kwargs)

    return wrapper


@usuario_autenticado
def dashboard(request):
    return render(request, "autenticacao/dashboard.html")


def logout_view(request):

    if request.method == "POST":
        request.session.flush()
        messages.success(request, "Você saiu do sistema.")

    return redirect("login")
