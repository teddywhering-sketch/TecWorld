from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0003_ordemservico_fotos")]
    operations = [
        migrations.AddField(
            model_name="ordemservico",
            name="anexo_inicial",
            field=models.FileField(blank=True, null=True, upload_to="ordens/anexos/%Y/%m/", validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png", "webp"])]),
        ),
    ]
