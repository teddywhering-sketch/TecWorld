from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0006_fechamentocaixa")]
    operations = [migrations.AddField(model_name="ordemservico", name="arquivada_em", field=models.DateTimeField(blank=True, null=True))]
