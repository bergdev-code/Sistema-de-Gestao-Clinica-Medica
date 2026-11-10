import MySQLdb

def conectar():
    conexao = MySQLdb.connect(
        host="db",
        user="root",
        passwd="berg1012",
        db="banco_clinica",
        port=3307
    )

    return conexao