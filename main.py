from sistema_clinica.pacientes import cadastro_pacientes
from sistema_clinica.medicos import cadastro_medicos
from sistema_clinica.usuario import cadastro_usuarios
from sistema_clinica.medicos import listagem_medicos
from sistema_clinica.pacientes import listagem_pacientes
from sistema_clinica.usuario import listagem_usuarios
from sistema_clinica.consultas import funcao_consulta
from sistema_clinica.consultas import listagem_consultas
from sistema_clinica.consultas import excluir_consultas
from sistema_clinica.usuario import excluir_usuarios
from sistema_clinica.medicos import excluir_medicos
from sistema_clinica.pacientes import excluir_pacientes
from sistema_clinica.financeiro import cadastro_pagamentos
from sistema_clinica.financeiro import listagem_pagamentos
from sistema_clinica.financeiro import excluir_pagamentos

def menu():
    main_loop = True
    while main_loop:
        valor_menu = int(input('======= SISTEMA DE GESTÃO MÉDICA ========\n1 - Cadastros\n2 - Consultas\n3 - Consultar pacientes\n4 - Gerenciar prontuários\n5 - Financeiro\n0 - Sair\nEscolha uma opção: '))
        
        match valor_menu:
            case 0:
                print('SAINDO...')
                main_loop = False
                break
            case 1:
                cadastro_loop = True
                while cadastro_loop:
                    valor_cadastro = int(input('======= CADASTROS =======\n1 - Pacientes\n2 - Médicos\n3 - Usuários\n0 - Retornar\nEscolha uma opção: '))
                    match valor_cadastro:
                        case 0:
                            print('RETORNANDO...')
                            cadastro_loop = False
                            break
                        case 1:
                            paciente_loop = True
                            while paciente_loop:
                                    valor_paciente = int(input('======= CADASTROS =======\n1 - Cadastrar pacientes\n2 - listar pacientes\n3 - excluir paciente\n0 - Retornar\nEscolha uma opção: '))
                                    match valor_paciente:
                                        case 0:
                                            print('RETORNANDO...')
                                            paciente_loop = False
                                            break
                                        case 1:
                                            cadastro_pacientes.cadastrar_paciente()
                                        case 2:
                                            listagem_pacientes.listar_pacientes()
                                        case 3:
                                              excluir_pacientes.excluir_paciente()
                                        case _:
                                            print('VALOR INVÁLIDO. TENTE NOVAMENTE.')
                        case 2:
                            medico_loop = True
                            while medico_loop:
                                    valor_medico = int(input('======= CADASTROS =======\n1 - Cadastrar médico\n2 - listar médicos\n3 - Apagar médicos\n0 - Retornar\nEscolha uma opção: '))
                                    match valor_medico:
                                        case 0:
                                            print('RETORNANDO...')
                                            medico_loop = False
                                            break
                                        case 1:
                                            cadastro_medicos.cadastrar_medico()
                                        case 2:
                                            listagem_medicos.listar_medicos()
                                        case 3:
                                              excluir_medicos.excluir_medico()
                                        case _:
                                            print('VALOR INVÁLIDO. TENTE NOVAMENTE.')
                        case 3:
                            usuario_loop = True
                            while usuario_loop:
                                    valor_usuario = int(input('======= CADASTROS =======\n1 - Cadastrar usuários\n2 - listar usuários\n3 - Excluir usuário\n0 - Retornar\nEscolha uma opção: '))
                                    match valor_usuario:
                                        case 0:
                                            print('RETORNANDO...')
                                            usuario_loop = False
                                            break
                                        case 1:
                                            cadastro_usuarios.cadastrar_usuario()
                                        case 2:
                                            listagem_usuarios.listar_usuarios()
                                        case 3:
                                            excluir_usuarios.excluir_usuarios()
                                        case _:
                                            print('VALOR INVÁLIDO. TENTE NOVAMENTE.')
                        case _:
                            print('VALOR INVÁLIDO. TENTE NOVAMENTE.')
            case 2:
                            consulta_loop = True
                            while consulta_loop:
                                    valor_consulta = int(input('======= CONSULTAS =======\n1 - Cadastrar nova consulta\n2 - listar consultas\n3 - Excluir consultas\n0 - Retornar\nEscolha uma opção: '))
                                    match valor_consulta:
                                        case 0:
                                            print('RETORNANDO...')
                                            consulta_loop = False
                                            break
                                        case 1:
                                            funcao_consulta.agendar_consulta()
                                        case 2:
                                            listagem_consultas.listar_consultas()
                                        case 3:
                                            excluir_consultas.excluir_consulta()
                                        case _:
                                            print('VALOR INVÁLIDO. TENTE NOVAMENTE.')                
            case 3:
                #Aqui fica a chamada da função de cada funcionalidade
                break
            case 4:
                #Aqui fica a chamada da função de cada funcionalidade
                break
            case 5:
                financeiro_loop = True
                while financeiro_loop:
                    valor_financeiro = int(input('======= FINANCEIRO =======\n1 - Registrar pagamento\n2 - Listar pagamentos\n3 - Excluir pagamento\n4 - Resumo financeiro\n0 - Retornar\nEscolha uma opção: '))
                    match valor_financeiro:
                        case 0:
                            print('RETORNANDO...')
                            financeiro_loop = False
                            break
                        case 1:
                            cadastro_pagamentos.registrar_pagamento()
                        case 2:
                            listagem_pagamentos.listar_pagamentos()
                        case 3:
                            excluir_pagamentos.excluir_pagamento()
                        case 4:
                            listagem_pagamentos.resumo_financeiro()
                        case _:
                            print('VALOR INVÁLIDO. TENTE NOVAMENTE.')
            case 6:
                #Aqui fica a chamada da função de cada funcionalidade
                break
            case _:
                print('VALOR INVÁLIDO.\nTENTE NOVAMENTE')
    
menu()