import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from sistema_clinica.pacientes import cadastro_pacientes
from sistema_clinica.pacientes import listagem_pacientes
from sistema_clinica.pacientes import excluir_pacientes
from sistema_clinica.pacientes import consultar_pacientes

from sistema_clinica.medicos import cadastro_medicos
from sistema_clinica.medicos import listagem_medicos
from sistema_clinica.medicos import excluir_medicos

from sistema_clinica.usuario import cadastro_usuarios
from sistema_clinica.usuario import listagem_usuarios
from sistema_clinica.usuario import excluir_usuarios

from sistema_clinica.consultas import funcao_consulta
from sistema_clinica.consultas import listagem_consultas
from sistema_clinica.consultas import excluir_consultas

from sistema_clinica.prontuarios import cadastro_prontuarios
from sistema_clinica.prontuarios import listagem_prontuarios
from sistema_clinica.prontuarios import consultar_prontuarios
from sistema_clinica.prontuarios import excluir_prontuarios

from sistema_clinica.financeiro import cadastro_pagamentos
from sistema_clinica.financeiro import listagem_pagamentos
from sistema_clinica.financeiro import excluir_pagamentos

from sistema_clinica.funcionalidades.verificar_usuario import verificar_email
from sistema_clinica.funcionalidades.verifica_conexao import verificar_conexao

from sistema_clinica.atendimento.meus_agendamentos import meus_agendamentos
from sistema_clinica.atendimento.iniciar_atendimento import iniciar_atendimento

def login():

    resultado = verificar_email()

    if resultado is None:
        print("\nNão foi possível realizar o login.")
        return

    username_logado, perfil = resultado

    print("\nLogin realizado com sucesso!")
    print(f"Perfil: {perfil}")

    menu(username_logado, perfil)

def menu(username_logado, perfil):

    main_loop = True

    while main_loop:

        valor_menu = input(
            "\n======= SISTEMA DE GESTÃO MÉDICA =======\n"
            "1 - Cadastros\n"
            "2 - Consultas\n"
            "3 - Atendimento médico\n"
            "4 - Gerenciar prontuários\n"
            "5 - Financeiro\n"
            "0 - Sair\n"
            "Escolha uma opção: "
        )

        match valor_menu:

            case "0":
                print("\nSAINDO...")
                main_loop = False

            case "1":
                menu_cadastros()

            case "2":
                menu_consultas()

            case "3":
                menu_atendimento_medico(username_logado)

            case "4":
                menu_prontuarios()

            case "5":
                menu_financeiro()

            case _:
                print("\nVALOR INVÁLIDO. TENTE NOVAMENTE.")


# ==================================================
# MENU DE CADASTROS
# ==================================================

def menu_cadastros():

    cadastro_loop = True

    while cadastro_loop:

        valor = input(
            "\n======= CADASTROS =======\n"
            "1 - Pacientes\n"
            "2 - Médicos\n"
            "3 - Usuários\n"
            "0 - Retornar\n"
            "Escolha uma opção: "
        )

        match valor:

            case "0":
                cadastro_loop = False

            case "1":
                menu_pacientes()

            case "2":
                menu_medicos()

            case "3":
                menu_usuarios()

            case _:
                print("\nVALOR INVÁLIDO. TENTE NOVAMENTE.")


# ==================================================
# MENU DE PACIENTES
# ==================================================

def menu_pacientes():

    paciente_loop = True

    while paciente_loop:

        valor = input(
            "\n======= PACIENTES =======\n"
            "1 - Cadastrar paciente\n"
            "2 - Listar pacientes\n"
            "3 - Excluir paciente\n"
            "4 - Pesquisar paciente\n"
            "0 - Retornar\n"
            "Escolha uma opção: "
        )

        match valor:

            case "0":
                paciente_loop = False

            case "1":
                cadastro_pacientes.cadastrar_paciente()

            case "2":
                listagem_pacientes.listar_pacientes()

            case "3":
                excluir_pacientes.excluir_paciente()

            case "4":
                consultar_pacientes.consultar_paciente()

            case _:
                print("\nVALOR INVÁLIDO. TENTE NOVAMENTE.")


# ==================================================
# MENU DE MÉDICOS
# ==================================================

def menu_medicos():

    medico_loop = True

    while medico_loop:

        valor = input(
            "\n======= MÉDICOS =======\n"
            "1 - Cadastrar médico\n"
            "2 - Listar médicos\n"
            "3 - Excluir médico\n"
            "0 - Retornar\n"
            "Escolha uma opção: "
        )

        match valor:

            case "0":
                medico_loop = False

            case "1":
                cadastro_medicos.cadastrar_medico()

            case "2":
                listagem_medicos.listar_medicos()

            case "3":
                excluir_medicos.excluir_medico()

            case _:
                print("\nVALOR INVÁLIDO. TENTE NOVAMENTE.")


# ==================================================
# MENU DE USUÁRIOS
# ==================================================

def menu_usuarios():

    usuario_loop = True

    while usuario_loop:

        valor = input(
            "\n======= USUÁRIOS =======\n"
            "1 - Cadastrar usuário\n"
            "2 - Listar usuários\n"
            "3 - Excluir usuário\n"
            "0 - Retornar\n"
            "Escolha uma opção: "
        )

        match valor:

            case "0":
                usuario_loop = False

            case "1":
                cadastro_usuarios.cadastrar_usuario()

            case "2":
                listagem_usuarios.listar_usuarios()

            case "3":
                excluir_usuarios.excluir_usuarios()

            case _:
                print("\nVALOR INVÁLIDO. TENTE NOVAMENTE.")


# ==================================================
# MENU DE CONSULTAS
# ==================================================

def menu_consultas():

    consulta_loop = True

    while consulta_loop:

        valor = input(
            "\n======= CONSULTAS =======\n"
            "1 - Cadastrar nova consulta\n"
            "2 - Listar consultas\n"
            "3 - Cancelar consulta\n"
            "0 - Retornar\n"
            "Escolha uma opção: "
        )

        match valor:

            case "0":
                consulta_loop = False

            case "1":
                funcao_consulta.agendar_consulta()

            case "2":
                listagem_consultas.listar_consultas()

            case "3":
                excluir_consultas.excluir_consulta()

            case _:
                print("\nVALOR INVÁLIDO. TENTE NOVAMENTE.")


# ==================================================
# MENU DE ATENDIMENTO MÉDICO
# ==================================================

def menu_atendimento_medico(username_logado):

    atendimento_loop = True

    while atendimento_loop:

        valor = input(
            "\n======= ATENDIMENTO MÉDICO =======\n"
            "1 - Meus agendamentos\n"
            "2 - Iniciar atendimento médico\n"
            "0 - Retornar\n"
            "Escolha uma opção: "
        )

        match valor:

            case "0":
                atendimento_loop = False

            case "1":
                meus_agendamentos(username_logado)

            case "2":
                iniciar_atendimento(username_logado)

            case _:
                print("\nVALOR INVÁLIDO. TENTE NOVAMENTE.")


# ==================================================
# MENU DE PRONTUÁRIOS
# ==================================================

def menu_prontuarios():

    prontuario_loop = True

    while prontuario_loop:

        valor = input(
            "\n======= PRONTUÁRIOS =======\n"
            "1 - Registrar prontuário\n"
            "2 - Listar prontuários\n"
            "3 - Consultar prontuário\n"
            "4 - Excluir prontuário\n"
            "0 - Retornar\n"
            "Escolha uma opção: "
        )

        match valor:

            case "0":
                prontuario_loop = False

            case "1":
                cadastro_prontuarios.registrar_prontuario()

            case "2":
                listagem_prontuarios.listar_prontuarios()

            case "3":
                consultar_prontuarios.consultar_prontuario()

            case "4":
                excluir_prontuarios.excluir_prontuario()

            case _:
                print("\nVALOR INVÁLIDO. TENTE NOVAMENTE.")


# ==================================================
# MENU FINANCEIRO
# ==================================================

def menu_financeiro():

    financeiro_loop = True

    while financeiro_loop:

        valor = input(
            "\n======= FINANCEIRO =======\n"
            "1 - Registrar pagamento\n"
            "2 - Listar pagamentos\n"
            "3 - Excluir pagamento\n"
            "4 - Resumo financeiro\n"
            "0 - Retornar\n"
            "Escolha uma opção: "
        )

        match valor:

            case "0":
                financeiro_loop = False

            case "1":
                cadastro_pagamentos.registrar_pagamento()

            case "2":
                listagem_pagamentos.listar_pagamentos()

            case "3":
                excluir_pagamentos.excluir_pagamento()

            case "4":
                listagem_pagamentos.resumo_financeiro()

            case _:
                print("\nVALOR INVÁLIDO. TENTE NOVAMENTE.")


# ==================================================
# EXECUÇÃO DO SISTEMA
# ==================================================

if __name__ == "__main__":

    verificar_conexao()
    login()