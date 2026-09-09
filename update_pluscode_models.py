import re

with open('core/models.py', 'r') as f:
    content = f.read()

# Add plus_code to OrdemServico model
# Find the start of OrdemServico class and add the field
old_field = '    agendamento = models.DateTimeField(null=True, blank=True)'
new_field = '    plus_code = models.CharField("Plus Code (Localização)", max_length=50, blank=True, help_text="Ex: 87G8Q222+22")\n    agendamento = models.DateTimeField(null=True, blank=True)'

content = content.replace(old_field, new_field)

with open('core/models.py', 'w') as f:
    f.write(content)

print("Done")
