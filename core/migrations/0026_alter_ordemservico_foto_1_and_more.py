from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0025_produto_preco_base")]
    operations = [
        migrations.AlterField(
            model_name="ordemservico",
            name="foto_1",
            field=models.FileField(blank=True, null=True, upload_to="ordens/%Y/%m/"),
        ),
        migrations.AlterField(
            model_name="ordemservico",
            name="foto_2",
            field=models.FileField(blank=True, null=True, upload_to="ordens/%Y/%m/"),
        ),
        migrations.AlterField(
            model_name="ordemservico",
            name="foto_3",
            field=models.FileField(blank=True, null=True, upload_to="ordens/%Y/%m/"),
        ),
    ]
