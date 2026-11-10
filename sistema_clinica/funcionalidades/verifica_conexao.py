from django.db import connection
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django.setup()

from django.db import connection

def verificar_conexao():

    try:
        connection.ensure_connection()

        print("Conexão com o banco de dados estabelecida!")

        return True

    except Exception as erro:

        print("Erro ao conectar ao banco de dados!")
        print(f"Detalhes: {erro}")

        return False
    
verificar_conexao()