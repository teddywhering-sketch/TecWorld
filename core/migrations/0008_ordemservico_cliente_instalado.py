from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0007_ordemservico_arquivada_em")]
    operations = [migrations.AddField(model_name="ordemservico", name="cliente_instalado", field=models.BooleanField(default=False))]
