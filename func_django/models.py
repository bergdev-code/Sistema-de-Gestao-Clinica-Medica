from django.db import models

class func_django(models.Model):

    cpf = models.CharField(max_length=11, primary_key=True)
    nome = models.CharField(max_length=150, null=True, blank=True)
    telefone = models.CharField(max_length=11, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'pacientes'
        managed = True