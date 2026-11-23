from .views import RECURSOS, acoes_do_perfil
from .models import Usuario, GoogleIdentity


def menu(request):
    sessao = getattr(request, "session", None)
    perfil = sessao.get("perfil") if sessao else None

    menu_permitido = {
        r for r in RECURSOS
        if "ver" in acoes_do_perfil(perfil, r)
    }

    mostrar_completar_cadastro = False

    username = sessao.get("username") if sessao else None

    if username:
        usuario = (
            Usuario.objects
            .filter(username=username)
            .only("id_usuario", "paciente_id")
            .first()
        )

        if usuario and usuario.paciente_id is None:
            mostrar_completar_cadastro = GoogleIdentity.objects.filter(
                usuario=usuario
            ).exists()

    return {
        "menu_permitido": menu_permitido,
        "mostrar_completar_cadastro": mostrar_completar_cadastro,
    }