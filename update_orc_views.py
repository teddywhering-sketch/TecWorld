import re

with open('core/views.py', 'r') as f:
    content = f.read()

# Update get_form in OrcamentoCreateView and OrcamentoUpdateView
def replace_get_form(view_name):
    global content
    pattern = r'(class ' + view_name + r'.*?def get_form.*?if cliente:\n\s*form.fields\[\'cliente\'\].queryset = Cliente.objects.filter\(id=cliente.id\)\n)(\s*else:\n\s*form.fields\[\'cliente\'\].queryset = Cliente.objects.none\(\)\n\s*return form)'
    
    match = re.search(pattern, content, re.DOTALL)
    if match:
        new_text = match.group(1) + "                form.fields['cliente_final'].queryset = ClienteFinal.objects.filter(provedor=cliente)\n" + match.group(2).replace(
            "form.fields['cliente'].queryset = Cliente.objects.none()",
            "form.fields['cliente'].queryset = Cliente.objects.none()\n                form.fields['cliente_final'].queryset = ClienteFinal.objects.none()"
        )
        content = content.replace(match.group(0), new_text)

replace_get_form('OrcamentoCreateView')
replace_get_form('OrcamentoUpdateView')

with open('core/views.py', 'w') as f:
    f.write(content)

print("Done")
