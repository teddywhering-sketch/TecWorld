import re

with open('core/forms.py', 'r') as f:
    content = f.read()

# Make sure ItemOS is imported
content = content.replace(
    'Cliente, ClienteFinal, FechamentoCaixa, Lancamento, Orcamento, OrcamentoItem,',
    'Cliente, ClienteFinal, FechamentoCaixa, Lancamento, Orcamento, OrcamentoItem, ItemOS,'
)

item_os_code = """
class ItemOSForm(BaseForm):
    class Meta:
        model = ItemOS
        fields = ["descricao", "quantidade", "valor_unitario"]
        labels = {"descricao": "Descrição", "quantidade": "Qtd", "valor_unitario": "Valor Un. (R$)"}

ItemOSFormSet = inlineformset_factory(
    OrdemServico, ItemOS, form=ItemOSForm,
    extra=3, can_delete=True
)
"""

content = content.replace(
    "OrcamentoItemFormSet = inlineformset_factory(",
    item_os_code + "\nOrcamentoItemFormSet = inlineformset_factory("
)

with open('core/forms.py', 'w') as f:
    f.write(content)

print("Done")
