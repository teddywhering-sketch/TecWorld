import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from core.models import Lancamento, OrdemServico, Cliente, TipoServico
from django.utils import timezone
from datetime import timedelta

# Criar Técnicos
tecnico1, _ = User.objects.get_or_create(username='tecnico1', defaults={'first_name': 'Carlos', 'last_name': 'Técnico'})
tecnico2, _ = User.objects.get_or_create(username='tecnico2', defaults={'first_name': 'João', 'last_name': 'Técnico'})

# Configurar senha padrão para facilitar se o user quiser testar logar com eles
tecnico1.set_password('123456')
tecnico1.save()
tecnico2.set_password('123456')
tecnico2.save()

# Buscar um cliente e tipo de servico para criar OS
cliente = Cliente.objects.first()
tipo_servico = TipoServico.objects.first()

if not cliente:
    cliente = Cliente.objects.create(nome='Cliente Teste Simulacao')
if not tipo_servico:
    tipo_servico = TipoServico.objects.create(nome='Instalação de Teste', valor_padrao=100.00)

hoje = timezone.now().date()

# ---- TÉCNICO 1: CARLOS ----
# Ordem de Servico (Concluida) - R$ 200,00
os1 = OrdemServico.objects.create(
    cliente=cliente,
    tipo=tipo_servico,
    tecnico=tecnico1,
    status='CONCLUIDA',
    valor=Decimal('200.00'),
    descricao='Instalação de fibra para simulação'
)
# Lançamento Entrada (referente a OS)
Lancamento.objects.create(
    data=hoje,
    descricao='Recebimento Instalação (Carlos)',
    tipo='ENTRADA',
    categoria='Serviço',
    valor=Decimal('200.00'),
    ordem_servico=os1,
    tecnico=tecnico1
)
# Lançamento Saída (Combustível) - R$ 50,00
Lancamento.objects.create(
    data=hoje,
    descricao='Abastecimento Posto X (Carlos)',
    tipo='SAIDA',
    categoria='Combustível',
    valor=Decimal('50.00'),
    tecnico=tecnico1
)

# ---- TÉCNICO 2: JOÃO ----
# Ordem de Servico (Concluida) - R$ 350,00
os2 = OrdemServico.objects.create(
    cliente=cliente,
    tipo=tipo_servico,
    tecnico=tecnico2,
    status='CONCLUIDA',
    valor=Decimal('350.00'),
    descricao='Manutenção e Reparo (João)'
)
# Lançamento Entrada
Lancamento.objects.create(
    data=hoje,
    descricao='Recebimento Manutenção (João)',
    tipo='ENTRADA',
    categoria='Serviço',
    valor=Decimal('350.00'),
    ordem_servico=os2,
    tecnico=tecnico2
)
# Lançamento Saída (Combustível) - R$ 100,00
Lancamento.objects.create(
    data=hoje,
    descricao='Abastecimento Posto Y (João)',
    tipo='SAIDA',
    categoria='Combustível',
    valor=Decimal('100.00'),
    tecnico=tecnico2
)
# Lançamento Saída (Outros gastos) - R$ 30,00
Lancamento.objects.create(
    data=hoje,
    descricao='Compra de lanche',
    tipo='SAIDA',
    categoria='Alimentação',
    valor=Decimal('30.00'),
    tecnico=tecnico2
)

print("Simulação gerada com sucesso! Dois técnicos (Carlos e João) foram criados com Ordens de Serviço e lançamentos.")
