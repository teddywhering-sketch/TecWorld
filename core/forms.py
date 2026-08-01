from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User
from .models import Cliente, Lancamento, Orcamento, OrdemServico

class BaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput): field.widget.attrs["class"] = "form-check-input"

class ClienteForm(BaseForm):
    class Meta:
        model = Cliente
        fields = ["nome", "documento", "telefone", "email", "endereco", "observacoes"]

class OrdemServicoForm(BaseForm):
    class Meta:
        model = OrdemServico
        fields = ["cliente", "tipo", "status", "tecnico", "agendamento", "descricao", "anexo_inicial", "valor"]
        labels = {"anexo_inicial": "Anexo para o técnico (PDF ou foto)"}
        widgets = {"agendamento": forms.DateTimeInput(attrs={"type": "datetime-local"}), "descricao": forms.Textarea(attrs={"rows": 3}), "solucao": forms.Textarea(attrs={"rows": 3})}

class OrcamentoForm(BaseForm):
    class Meta:
        model = Orcamento
        fields = ["cliente", "descricao", "valor", "validade", "status"]
        widgets = {"validade": forms.DateInput(attrs={"type": "date"}), "descricao": forms.Textarea(attrs={"rows": 4})}

class LancamentoForm(BaseForm):
    class Meta:
        model = Lancamento
        fields = ["data", "descricao", "tipo", "categoria", "valor", "ordem_servico"]
        widgets = {"data": forms.DateInput(attrs={"type": "date"})}

class FinalizarOSForm(BaseForm):
    class Meta:
        model = OrdemServico
        fields = ["nome_cliente_instalado", "solucao", "foto_1", "foto_2", "foto_3"]
        labels = {"nome_cliente_instalado": "Cliente instalado", "solucao": "Descrição do serviço executado", "foto_1": "CTO", "foto_2": "ONT", "foto_3": "Sinal da fibra no cliente"}
        widgets = {"solucao": forms.Textarea(attrs={"rows": 5, "placeholder": "Descreva o que foi realizado no atendimento."})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome_cliente_instalado"].required = True
        self.fields["solucao"].required = True

class ConfirmarOSForm(BaseForm):
    class Meta:
        model = OrdemServico
        fields = ["comprovante_pagamento"]
        labels = {"comprovante_pagamento": "Comprovante de pagamento (PDF ou foto)"}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["comprovante_pagamento"].required = True

class UsuarioForm(UserCreationForm):
    PAPEL = [("TECNICO", "Técnico"), ("SECRETARIA", "Secretaria"), ("ADMIN", "Administrador")]
    papel = forms.ChoiceField(choices=PAPEL, label="Perfil")
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["papel"].widget.attrs["class"] = "form-select"
    def save(self, commit=True):
        user = super().save(commit=False)
        papel = self.cleaned_data["papel"]
        user.is_staff = papel == "ADMIN"
        if commit:
            user.save()
            secretaria, _ = Group.objects.get_or_create(name="Secretaria")
            user.groups.remove(secretaria)
            if papel == "SECRETARIA": user.groups.add(secretaria)
        return user
