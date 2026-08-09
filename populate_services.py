import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import TipoServico
from decimal import Decimal

servicos = [
    {"nome": "Instalação de Internet (Residencial) (Por cliente ativo)", "valor": "80.00"},
    {"nome": "Lançamento de Fibra Óptica AS (Por metro/poste)", "valor": "1.50"},
    {"nome": "Fusão de Fibra Óptica (Por fusão realizada)", "valor": "25.00"},
    {"nome": "Instalação de Câmeras (CFTV) (Por câmera s/ infra)", "valor": "100.00"},
    {"nome": "Configuração de Rede (Switch/Roteador)", "valor": "100.00"},
    {"nome": "Instalação de Chuveiro Elétrico (Por unidade)", "valor": "80.00"},
    {"nome": "Instalação de Tomada / Interruptor (Por ponto)", "valor": "40.00"},
    {"nome": "Visita Técnica / Taxa de Deslocamento", "valor": "50.00"},
    {"nome": "Lançamento de cabo de rede (Por metro)", "valor": "2.30"},
]

for s in servicos:
    # Try to find a very similar existing one to update, but names have extra text now, 
    # so we will just create them or update them.
    obj, created = TipoServico.objects.update_or_create(
        nome=s["nome"],
        defaults={"valor_padrao": Decimal(s["valor"])}
    )
    print(f"{'Criado' if created else 'Atualizado'}: {obj.nome} - R$ {obj.valor_padrao}")

print("Script finalizado!")
