from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0008_ordemservico_cliente_instalado")]
    operations = [migrations.AddField(model_name="ordemservico", name="nome_cliente_instalado", field=models.CharField(blank=True, max_length=150))]
