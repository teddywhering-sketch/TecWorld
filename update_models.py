import re

with open('core/models.py', 'r') as f:
    content = f.read()

# Make tipo nullable
content = re.sub(
    r'tipo = models\.ForeignKey\(TipoServico, on_delete=models\.PROTECT, verbose_name="Tipo de Serviço"\)',
    r'tipo = models.ForeignKey(TipoServico, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tipo de Serviço Principal")',
    content
)

# Add ItemOS model
item_os_code = """
class ItemOS(models.Model):
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="itens")
    descricao = models.CharField(max_length=255)
    quantidade = models.PositiveIntegerField(default=1)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    @property
    def total(self):
        return self.quantidade * self.valor_unitario

"""

# Insert after OrdemServico model
content = content.replace("class Lancamento(TimeStampedModel):", item_os_code + "class Lancamento(TimeStampedModel):")

with open('core/models.py', 'w') as f:
    f.write(content)

print("Done")
