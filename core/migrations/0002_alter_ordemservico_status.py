from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="ordemservico",
            name="status",
            field=models.CharField(
                max_length=25,
                default="ABERTA",
                choices=[
                    ("ABERTA", "Aberta"), ("AGENDADA", "Agendada"),
                    ("EM_ANDAMENTO", "Em andamento"),
                    ("AGUARDANDO_CONFIRMACAO", "Aguardando confirmação"),
                    ("CONCLUIDA", "Concluída"), ("CANCELADA", "Cancelada"),
                ],
            ),
        ),
    ]
