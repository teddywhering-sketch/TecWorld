import re

with open('core/forms.py', 'r') as f:
    content = f.read()

# Replace fields = ["cliente", "descricao", "valor", "desconto", "validade", "status"]
# with fields = ["cliente", "cliente_final", "descricao", "valor", "desconto", "validade", "status"]
content = content.replace(
    'fields = ["cliente", "descricao", "valor", "desconto", "validade", "status"]',
    'fields = ["cliente", "cliente_final", "descricao", "valor", "desconto", "validade", "status"]'
)

# Replace labels = {"valor": "Subtotal (Opcional se usar Itens)", "desconto": "Desconto Geral"}
# with labels = {"cliente_final": "Cliente Final (Opcional)", "valor": "Subtotal (Opcional se usar Itens)", "desconto": "Desconto Geral"}
content = content.replace(
    'labels = {"valor": "Subtotal (Opcional se usar Itens)", "desconto": "Desconto Geral"}',
    'labels = {"cliente_final": "Cliente Final (Opcional)", "valor": "Subtotal (Opcional se usar Itens)", "desconto": "Desconto Geral"}'
)

with open('core/forms.py', 'w') as f:
    f.write(content)

print("Done")
