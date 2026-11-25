import MySQLdb

def conectar():
    conexao = MySQLdb.connect(
        host="bancoclinica-bancoclinica.g.aivencloud.com",
        user="",
        passwd="",
        db="",
        port=
    )

    return conexao