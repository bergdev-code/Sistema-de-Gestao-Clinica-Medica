import MySQLdb

def conectar():
    conexao = MySQLdb.connect(
        host="hostdobanco",
        user="userdobanco",
        passwd="senha",
        db="nomedobanco",
        port=porta
    )

    return conexao