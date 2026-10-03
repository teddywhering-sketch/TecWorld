from django.core.management.base import BaseCommand
from teddyfinanca.models import ParcelaVenda, Emprestimo, Divida, Venda, Transacao

class Command(BaseCommand):
    help = 'Corrige valores inflados (multiplicados por 100) no banco de dados causados pelo bug de formatação'

    def handle(self, *args, **kwargs):
        fix_count = 0
        
        # ParcelaVenda
        for p in ParcelaVenda.objects.filter(valor_pago__gt=0):
            if p.valor_pago >= p.valor * 10:
                old_val = p.valor_pago
                p.valor_pago = p.valor_pago / 100
                p.save()
                self.stdout.write(f"Corrigido ParcelaVenda {p.id}: {old_val} -> {p.valor_pago}")
                fix_count += 1

        # Emprestimo
        for p in Emprestimo.objects.filter(valor_pago__gt=0):
            if p.valor_pago >= p.valor * 10:
                old_val = p.valor_pago
                p.valor_pago = p.valor_pago / 100
                p.save()
                self.stdout.write(f"Corrigido Emprestimo {p.id}: {old_val} -> {p.valor_pago}")
                fix_count += 1

        # Divida
        for p in Divida.objects.filter(valor_pago__gt=0):
            if p.valor_pago >= p.valor * 10:
                old_val = p.valor_pago
                p.valor_pago = p.valor_pago / 100
                p.save()
                self.stdout.write(f"Corrigido Divida {p.id}: {old_val} -> {p.valor_pago}")
                fix_count += 1

        # Venda Unica
        for p in Venda.objects.filter(valor_pago__gt=0):
            if p.valor_pago >= p.valor * 10:
                old_val = p.valor_pago
                p.valor_pago = p.valor_pago / 100
                p.save()
                self.stdout.write(f"Corrigido Venda {p.id}: {old_val} -> {p.valor_pago}")
                fix_count += 1

        self.stdout.write(self.style.SUCCESS(f'Concluído! {fix_count} registros corrigidos.'))
