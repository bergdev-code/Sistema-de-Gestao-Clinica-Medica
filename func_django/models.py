from django.db import models

class Medico(models.Model):

    crm = models.CharField(max_length=6, primary_key=True)
    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=11)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'medicos'
        managed = False

class func_django(models.Model):

    cpf = models.CharField(max_length=11, primary_key=True)
    nome = models.CharField(max_length=150, null=True, blank=True)
    telefone = models.CharField(max_length=11, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)

    medico = models.ForeignKey(
    Medico,
    on_delete=models.PROTECT,
    related_name="pacientes",
    null=True,
    blank=True
)

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

    medico = models.ForeignKey(
    Medico,
    on_delete=models.PROTECT,
    db_column='crm',
    null=True,
    blank=True
)

    paciente = models.ForeignKey(
        func_django,
        on_delete=models.PROTECT,
        db_column='paciente_cpf',
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'usuarios'
        managed = True

class Prontuario(models.Model):
    id_prontuario = models.AutoField(primary_key=True)

    anamnese = models.TextField(null=True, blank=True)
    diagnostico = models.TextField(null=True, blank=True)
    prescricao = models.TextField(null=True, blank=True)

    agendamento_id = models.IntegerField(null=True, blank=True)

    paciente = models.ForeignKey(
        func_django,
        on_delete=models.PROTECT,
        db_column='paciente_id'
    )

    medico = models.ForeignKey(
        Medico,
        on_delete=models.PROTECT,
        db_column='medico_id'
    )

    class Meta:
        db_table = 'prontuarios'
        managed = False

class Especialidade(models.Model):

    id_especialidade = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)

    class Meta:
        db_table = 'especialidades'
        managed = False


class MedicoEspecialidade(models.Model):

    id_medico_especialidade = models.AutoField(primary_key=True)

    medico = models.ForeignKey(
        Medico,
        on_delete=models.PROTECT,
        db_column='medico'
    )

    especialidade = models.ForeignKey(
        Especialidade,
        on_delete=models.PROTECT,
        db_column='especialidade'
    )

    class Meta:
        db_table = 'medico_especialidade'
        managed = False


class HorarioMedico(models.Model):

    id_horarios = models.AutoField(primary_key=True)

    medico = models.ForeignKey(
        Medico,
        on_delete=models.PROTECT,
        db_column='medico_id'
    )

    dia_semana = models.CharField(max_length=20)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    class Meta:
        db_table = 'horarios_medicos'
        managed = False


class StatusAgendamento(models.Model):
    id_status = models.AutoField(primary_key=True)
    descricao = models.CharField(max_length=30)

    class Meta:
        db_table = 'status_agendamento'
        managed = False


class Agendamento(models.Model):
    id_agendamento = models.AutoField(primary_key=True)

    paciente = models.ForeignKey(
        func_django,
        on_delete=models.PROTECT,
        db_column='paciente_id'
    )

    medico = models.ForeignKey(
        Medico,
        on_delete=models.PROTECT,
        db_column='medico_id'
    )

    data_hora = models.DateTimeField()

    status = models.ForeignKey(
        StatusAgendamento,
        on_delete=models.PROTECT,
        db_column='status_id'
    )

    tipo = models.CharField(max_length=20, default='Consulta')

    class Meta:
        db_table = 'agendamentos'
        managed = False

class StatusPagamento(models.Model):
    id_status = models.AutoField(primary_key=True)
    descricao = models.CharField(max_length=50)

    class Meta:
        db_table = "status_pagamento"


class Pagamento(models.Model):
    id_pagamento = models.AutoField(primary_key=True)

    agendamento = models.ForeignKey(
        Agendamento,
        on_delete=models.PROTECT,
        db_column="agendamento_id"
    )

    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pagamento = models.CharField(max_length=50)

    status_pagamento = models.ForeignKey(
        StatusPagamento,
        on_delete=models.PROTECT,
        db_column="status_pagamento_id"
    )

    data_pagamento = models.DateField()

    class Meta:
        db_table = "pagamentos"