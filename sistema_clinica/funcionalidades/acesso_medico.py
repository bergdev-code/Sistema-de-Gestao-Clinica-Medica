from sistema_clinica.funcionalidades import sessao


def acesso_medico():

    username = sessao.usuario_logado
    perfil = sessao.perfil_logado

    if username is None or perfil is None:
        print("\nNenhuma sessão ativa!")
        return None

    if perfil not in ("Médico", "ADMIN GERAL"):
        print("\nAcesso restrito aos médicos e administrador geral!")
        return None

    return username