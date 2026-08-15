from django.db import migrations

def link_lancamentos_to_tecnicos(apps, schema_editor):
    Lancamento = apps.get_model('core', 'Lancamento')
    for lancamento in Lancamento.objects.filter(tecnico__isnull=True, ordem_servico__isnull=False):
        lancamento.tecnico = lancamento.ordem_servico.tecnico
        lancamento.save(update_fields=['tecnico'])

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_logtransacao'),
    ]

    operations = [
        migrations.RunPython(link_lancamentos_to_tecnicos, reverse_code=migrations.RunPython.noop),
    ]
