from django.db import models

class func_django(models.Model):

    cpf = models.CharField(max_length=11, primary_key=True)
    nome = models.CharField(max_length=150, null=True, blank=True)
    telefone = models.CharField(max_length=11, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'pacientes'
        managed = True
    
class Perfil(models.Model):

    id_perfil = models.AutoField(primary_key=True)
    nome_perfil = models.CharField(max_length=20)

    class Meta:
        db_table = 'perfil'
        managed = True


class Usuario(models.Model):

    id_usuario = models.AutoField(primary_key=True)

    senha_hash = models.CharField(max_length=255)
    salt = models.CharField(max_length=32)

    username = models.CharField(
        max_length=10,
        unique=True
    )

    email = models.EmailField(
        max_length=50,
        unique=True
    )

    id_perfil = models.ForeignKey(
        Perfil,
        on_delete=models.PROTECT,
        db_column='id_perfil'
    )

    class Meta:
        db_table = 'usuarios'
        managed = True