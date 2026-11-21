from .views import RECURSOS, acoes_do_perfil


def menu(request):
    sessao = getattr(request, "session", None)
    perfil = sessao.get("perfil") if sessao else None
    return {"menu_permitido": {r for r in RECURSOS if "ver" in acoes_do_perfil(perfil, r)}}
