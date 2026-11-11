import os
import sys
from pathlib import Path

def verificar_conexao():

    # Identificar a raiz do projeto
    BASE_DIR = Path(__file__).resolve().parents[2]

    # Adicionar a raiz ao caminho de importação
    sys.path.insert(0, str(BASE_DIR))

    # Configurar o Django
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "config.settings"
    )

    import django
    django.setup()

    # Testar conexão com o banco
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION(), @@PORT")
            resultado = cursor.fetchone()

        print("\nConexão estabelecida com sucesso!")
        print(f"Versão do banco: {resultado[0]}")
        print(f"Porta: {resultado[1]}")

        return True

    except Exception as erro:
        print(f"\nErro na conexão: {erro}")
        return False