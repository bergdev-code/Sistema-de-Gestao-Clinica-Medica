usuario_logado = None
perfil_logado = None


def iniciar_sessao(username, perfil):
    global usuario_logado, perfil_logado

    usuario_logado = username
    perfil_logado = perfil


def encerrar_sessao():
    global usuario_logado, perfil_logado

    usuario_logado = None
    perfil_logado = None