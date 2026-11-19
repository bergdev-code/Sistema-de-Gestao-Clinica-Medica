from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('func_django', '0001_initial'),
    ]

    operations = [

        migrations.SeparateDatabaseAndState(
    database_operations=[],
    state_operations=[
        migrations.AddField(
            model_name='func_django',
            name='medico',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pacientes',
                to='func_django.medico'
            ),
        ),
    ],
),

        migrations.AddField(
            model_name='usuario',
            name='medico',
            field=models.ForeignKey(
                blank=True,
                db_column='crm',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='func_django.medico'
            ),
        ),

    ]