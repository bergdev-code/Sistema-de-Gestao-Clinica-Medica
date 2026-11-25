from .models import GoogleIdentity, Usuario
from .views import PERFIL_PACIENTE, RECURSOS, _n, acoes_do_perfil, chave_perfil


def menu(request):
    sessao = getattr(request, "session", None)
    perfil = sessao.get("perfil") if sessao else None

    menu_permitido = {
        r for r in RECURSOS
        if "ver" in acoes_do_perfil(perfil, r)
    }

    # O aviso "complete seu cadastro" só existe para o paciente que entrou pelo
    # Google e ainda não tem CPF/dados. Quando a sessão já tem o CPF (o caso comum)
    # não há nenhuma consulta ao banco aqui, em nenhuma página.
    mostrar_completar_cadastro = False
    username = sessao.get("username") if sessao else None

    if (
        username
        and not sessao.get("cpf")
        and chave_perfil(perfil) == _n(PERFIL_PACIENTE)
    ):
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
