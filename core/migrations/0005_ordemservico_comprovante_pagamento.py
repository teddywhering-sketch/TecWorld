from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0004_ordemservico_anexo_inicial")]
    operations = [
        migrations.AddField(
            model_name="ordemservico",
            name="comprovante_pagamento",
            field=models.FileField(blank=True, null=True, upload_to="ordens/pagamentos/%Y/%m/", validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png", "webp"])]),
        ),
    ]
