import MySQLdb

def conectar():
    conexao = MySQLdb.connect(
        host="",
        user="",
        passwd="",
        db="",
        port=

    return conexao