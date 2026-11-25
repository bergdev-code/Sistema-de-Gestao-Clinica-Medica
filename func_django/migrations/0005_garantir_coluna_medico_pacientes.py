from django.db import migrations


def garantir_coluna_medico(apps, schema_editor):
    """A migration 0002 só registrou o campo pacientes.medico no estado do Django
    (SeparateDatabaseAndState sem operação de banco). Em um banco criado do zero,
    a coluna medico_id nunca existiria e qualquer consulta a pacientes falharia.

    Aqui a coluna só é criada se NÃO existir, então em bancos que já a possuem
    (o seu, provavelmente) esta migration não altera nada.
    """
    modelo = apps.get_model("func_django", "func_django")
    conexao = schema_editor.connection

    with conexao.cursor() as cursor:
        colunas = {
            coluna.name for coluna in
            conexao.introspection.get_table_description(cursor, modelo._meta.db_table)
        }

    if "medico_id" not in colunas:
        schema_editor.add_field(modelo, modelo._meta.get_field("medico"))


class Migration(migrations.Migration):

    dependencies = [
        ('func_django', '0004_googleidentity'),
    ]

    operations = [
        migrations.RunPython(garantir_coluna_medico, migrations.RunPython.noop),
    ]
