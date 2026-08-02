from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User
from .models import (
    Cliente, ClienteFinal, FechamentoCaixa, Lancamento, Orcamento, 
    OrdemServico, TipoServico, Produto, ProdutoOS
)

class TipoServicoForm(forms.ModelForm):
    class Meta:
        model = TipoServico
        fields = ["nome", "ativo"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-control"
            else:
                field.widget.attrs["class"] = "form-check-input"

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

class ClienteFinalForm(BaseForm):
    class Meta:
        model = ClienteFinal
        fields = ["provedor", "nome", "telefone", "endereco"]
        labels = {"provedor": "Provedor (Cliente)"}

class OrdemServicoForm(BaseForm):
    class Meta:
        model = OrdemServico
        fields = ["cliente", "cliente_final", "tipo", "tecnico", "agendamento", "valor", "descricao", "anexo_inicial"]
        widgets = {"agendamento": forms.DateTimeInput(attrs={"type": "datetime-local"}), "descricao": forms.Textarea(attrs={"rows": 4})}
        labels = {"cliente": "Provedor", "cliente_final": "Cliente do Provedor (Opcional)"}

class OrcamentoForm(BaseForm):
    class Meta:
        model = Orcamento
        fields = ["cliente", "descricao", "valor", "validade", "status"]
        widgets = {"validade": forms.DateInput(attrs={"type": "date"}), "descricao": forms.Textarea(attrs={"rows": 4})}

class LancamentoForm(BaseForm):
    class Meta:
        model = Lancamento
        fields = ["data", "descricao", "tipo", "categoria", "valor", "ordem_servico", "tecnico"]
        widgets = {"data": forms.DateInput(attrs={"type": "date"})}

class CombustivelForm(BaseForm):
    class Meta:
        model = Lancamento
        fields = ["data", "tecnico", "valor", "descricao"]
        widgets = {"data": forms.DateInput(attrs={"type": "date"})}
        labels = {"tecnico": "Técnico", "valor": "Valor Gasto (R$)", "descricao": "Observação (Posto, KM, etc)"}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tecnico"].required = True

class ProdutoForm(BaseForm):
    class Meta:
        model = Produto
        fields = ["nome", "unidade", "estoque_base"]
        labels = {"estoque_base": "Quantidade no Estoque (Sede)"}

class TransferenciaEstoqueForm(forms.Form):
    tecnico = forms.ModelChoiceField(queryset=User.objects.filter(groups__name__isnull=True), label="Técnico Destino")
    produto = forms.ModelChoiceField(queryset=Produto.objects.all(), label="Produto")
    quantidade = forms.IntegerField(min_value=1, label="Quantidade a transferir")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Assuming technicians might not be in the Secretaria group or just all users are fine
        self.fields["tecnico"].queryset = User.objects.all()
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["tecnico"].widget.attrs["class"] = "form-select"
        self.fields["produto"].widget.attrs["class"] = "form-select"

class ProdutoOSForm(BaseForm):
    class Meta:
        model = ProdutoOS
        fields = ["produto", "quantidade"]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["produto"].widget.attrs["class"] = "form-select"

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
        self.fields["foto_1"].required = True
        self.fields["foto_2"].required = True
        self.fields["foto_3"].required = True

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
