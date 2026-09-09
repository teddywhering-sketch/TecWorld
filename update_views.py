import re

with open('core/views.py', 'r') as f:
    content = f.read()

# Fix imports
content = content.replace(
    "OrcamentoItemFormSet, OrdemServicoForm",
    "OrcamentoItemFormSet, OrdemServicoForm, ItemOSFormSet"
)

# Update OrdemCreateView
ordem_create = """
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        import json
        precos = {str(t.id): str(t.valor_padrao) for t in TipoServico.objects.filter(ativo=True)}
        c['tipos_precos_json'] = json.dumps(precos)
        if self.request.POST:
            c['itens'] = ItemOSFormSet(self.request.POST)
        else:
            c['itens'] = ItemOSFormSet()
        return c

    def form_valid(self, form):
        context = self.get_context_data()
        itens = context['itens']
        if itens.is_valid():
            self.object = form.save()
            itens.instance = self.object
            itens.save()
            # Calculate total
            total = sum(item.total for item in self.object.itens.all()) if self.object.itens.exists() else form.cleaned_data.get('valor', 0)
            self.object.valor = total
            self.object.save(update_fields=['valor'])
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))
"""

# replace get_context_data in OrdemCreateView
content = re.sub(
    r'    def get_context_data\(self, \*\*kwargs\):\n        c = super\(\)\.get_context_data\(\*\*kwargs\)\n        import json\n        precos = \{str\(t\.id\): str\(t\.valor_padrao\) for t in TipoServico\.objects\.filter\(ativo=True\)\}\n        c\[\'tipos_precos_json\'\] = json\.dumps\(precos\)\n        return c',
    ordem_create,
    content,
    count=1
)


# Update OrdemUpdateView
ordem_update = """
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        import json
        precos = {str(t.id): str(t.valor_padrao) for t in TipoServico.objects.filter(ativo=True)}
        c['tipos_precos_json'] = json.dumps(precos)
        if self.request.POST:
            c['itens'] = ItemOSFormSet(self.request.POST, instance=self.object)
        else:
            c['itens'] = ItemOSFormSet(instance=self.object)
        return c

    def form_valid(self, form):
        context = self.get_context_data()
        itens = context['itens']
        if itens.is_valid():
            self.object = form.save()
            itens.instance = self.object
            itens.save()
            # Calculate total
            total = sum(item.total for item in self.object.itens.all()) if self.object.itens.exists() else form.cleaned_data.get('valor', 0)
            self.object.valor = total
            self.object.save(update_fields=['valor'])
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))
"""

content = re.sub(
    r'    def get_context_data\(self, \*\*kwargs\):\n        c = super\(\)\.get_context_data\(\*\*kwargs\)\n        import json\n        precos = \{str\(t\.id\): str\(t\.valor_padrao\) for t in TipoServico\.objects\.filter\(ativo=True\)\}\n        c\[\'tipos_precos_json\'\] = json\.dumps\(precos\)\n        return c',
    ordem_update,
    content,
    count=1
)

with open('core/views.py', 'w') as f:
    f.write(content)

print("Done")
