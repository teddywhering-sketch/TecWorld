from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_alter_ordemservico_status")]
    operations = [
        migrations.AddField(model_name="ordemservico", name="foto_1", field=models.ImageField(blank=True, null=True, upload_to="ordens/%Y/%m/")),
        migrations.AddField(model_name="ordemservico", name="foto_2", field=models.ImageField(blank=True, null=True, upload_to="ordens/%Y/%m/")),
        migrations.AddField(model_name="ordemservico", name="foto_3", field=models.ImageField(blank=True, null=True, upload_to="ordens/%Y/%m/")),
    ]
