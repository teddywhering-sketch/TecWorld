import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0005_ordemservico_comprovante_pagamento"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="FechamentoCaixa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fechado_em", models.DateTimeField(auto_now_add=True)),
                ("entradas", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("saidas", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("responsavel", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fechado_em"]},
        ),
    ]
