import re

def validar_nome(nome):
    regex = r'^[A-Za-zÀ-ÿ\s]{3,100}$'

    if re.fullmatch(regex, nome):
        return True

    return False

def validar_email(email):
    regex = r'^[\w.-]+@[\w.-]+\.\w{2,}$'

    if re.fullmatch(regex, email):
        return True

    return False

def validar_senha(senha):
    regex = r'^.{8,}$'

    if re.fullmatch(regex, senha):
        return True

    return False
