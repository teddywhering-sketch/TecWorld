import re

with open('core/forms.py', 'r') as f:
    content = f.read()

# Replace fields = ["cliente", "cliente_final", "tipo", "agendamento", "valor", "descricao", "anexo_inicial"]
# with fields = ["cliente", "cliente_final", "tipo", "plus_code", "agendamento", "valor", "descricao", "anexo_inicial"]

content = content.replace(
    'fields = ["cliente", "cliente_final", "tipo", "agendamento", "valor", "descricao", "anexo_inicial"]',
    'fields = ["cliente", "cliente_final", "tipo", "plus_code", "agendamento", "valor", "descricao", "anexo_inicial"]'
)

with open('core/forms.py', 'w') as f:
    f.write(content)

print("Done")
