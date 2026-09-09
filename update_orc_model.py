import re

with open('core/models.py', 'r') as f:
    content = f.read()

# Replace ForeignKey(ClienteFinal with ForeignKey('ClienteFinal'
content = content.replace(
    'cliente_final = models.ForeignKey(ClienteFinal, on_delete=models.SET_NULL, blank=True, null=True, related_name="orcamentos")',
    'cliente_final = models.ForeignKey("ClienteFinal", on_delete=models.SET_NULL, blank=True, null=True, related_name="orcamentos")'
)

with open('core/models.py', 'w') as f:
    f.write(content)

print("Done")
