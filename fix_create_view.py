import re

with open('core/views.py', 'r') as f:
    content = f.read()

# Let's just manually replace the exact string in OrcamentoCreateView
old_str = """    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                form.fields['cliente'].queryset = Cliente.objects.filter(id=cliente.id)
                form.fields['cliente'].initial = cliente
            else:
                form.fields['cliente'].queryset = Cliente.objects.none()
        return form"""

new_str = """    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                form.fields['cliente'].queryset = Cliente.objects.filter(id=cliente.id)
                form.fields['cliente'].initial = cliente
                form.fields['cliente_final'].queryset = ClienteFinal.objects.filter(provedor=cliente)
            else:
                form.fields['cliente'].queryset = Cliente.objects.none()
                form.fields['cliente_final'].queryset = ClienteFinal.objects.none()
        return form"""

content = content.replace(old_str, new_str)

with open('core/views.py', 'w') as f:
    f.write(content)
