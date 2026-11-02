from sistema_clinica.pacientes import cadastro_pacientes

def menu():
    main_loop = True
    while main_loop:
        valor_menu = int(input('======= SISTEMA DE GESTÃO MÉDICA ========\n1 - Cadastrar paciente\n2 - Cadastrar médico\n3 - Agendar consulta\n4 - Consultar pacientes\n5 - Gerenciar prontuários\n6 - Financeiro\n0 - Sair\nEscolha uma opção: '))
        
        match valor_menu:
            case 0:
                print('SAINDO...')
                main_loop = False
                break
            case 1:
                cadastro_pacientes.cadastrar_paciente()
                break
            case 2:
                #Aqui fica a chamada da função de cada funcionalidade
                break
            case 3:
                #Aqui fica a chamada da função de cada funcionalidade
                break
            case 4:
                #Aqui fica a chamada da função de cada funcionalidade
                break
            case 5:
                #Aqui fica a chamada da função de cada funcionalidade
                break
            case 6:
                #Aqui fica a chamada da função de cada funcionalidade
                break
            case _:
                print('VALOR INVÁLIDO.\nTENTE NOVAMENTE')
    
menu()