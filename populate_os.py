import os
import django
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import OrdemServico, Cliente, TipoServico
from django.contrib.auth import get_user_model

User = get_user_model()

# Ensure we have at least one client, type and technician
cliente = Cliente.objects.first()
if not cliente:
    cliente = Cliente.objects.create(nome="Cliente Teste", email="teste@teste.com", telefone="11999999999")

tipo = TipoServico.objects.first()
if not tipo:
    tipo = TipoServico.objects.create(nome="Serviço Teste", preco_base=100)

tecnico = User.objects.filter(is_staff=False).first()
if not tecnico:
    tecnico = User.objects.first() # fallback to any user

statuses = [
    OrdemServico.Status.ABERTA,
    OrdemServico.Status.EM_ANDAMENTO,
    OrdemServico.Status.AGUARDANDO_CONFIRMACAO,
    OrdemServico.Status.CONCLUIDA
]

print("Criando 20 OS para cada status...")

for status in statuses:
    for i in range(20):
        # We assign the technician to all of them so they appear in their dashboard!
        os_obj = OrdemServico.objects.create(
            cliente=cliente,
            tipo=tipo,
            status=status,
            descricao=f"OS de Teste {status} #{i}",
            tecnico=tecnico,
            agendamento=timezone.now() if status == OrdemServico.Status.ABERTA else None,
            iniciado_em=timezone.now() if status != OrdemServico.Status.ABERTA else None,
            finalizado_em=timezone.now() if status in [OrdemServico.Status.AGUARDANDO_CONFIRMACAO, OrdemServico.Status.CONCLUIDA] else None,
        )

print("Finalizado!")
