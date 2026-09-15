from django import forms
from .models import Perfil, Transacao, Divida, Emprestimo, VendaParcelada, Venda, Banco, Categoria

class LocalizedModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.DecimalField) or isinstance(field, forms.FloatField):
                field.localize = True
                field.widget.is_localized = True
                field.widget.input_type = 'text'
                if hasattr(field.widget, 'attrs'):
                    field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' money-mask'

class BancoForm(LocalizedModelForm):
    class Meta:
        model = Banco
        fields = ['nome', 'saldo_atual', 'limite_cheque_especial', 'limite_credito']

class CategoriaForm(LocalizedModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'tipo']

class VendaParceladaForm(LocalizedModelForm):
    class Meta:
        model = VendaParcelada
        fields = ['cliente', 'telefone_cliente', 'descricao', 'valor_total', 'entrada', 'quantidade_parcelas', 'data_venda']
        widgets = {
            'data_venda': forms.DateInput(attrs={'type': 'date'}),
        }

class TransacaoForm(LocalizedModelForm):
    categoria_texto = forms.CharField(max_length=100, required=False, label="Categoria", help_text="Digite para criar nova ou use uma existente", widget=forms.TextInput(attrs={'list': 'categorias-datalist', 'autocomplete': 'off'}))
    
    class Meta:
        model = Transacao
        fields = ['banco', 'forma_pagamento', 'tipo', 'valor', 'descricao', 'data', 'status']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }

class DividaForm(LocalizedModelForm):
    TIPO_CHOICES = (
        ('UNICA', 'Única'),
        ('PARCELADA', 'Parcelada'),
        ('RECORRENTE', 'Fixa Mensal (Recorrente)'),
    )
    tipo_divida = forms.ChoiceField(choices=TIPO_CHOICES, initial='UNICA', label="Tipo de Dívida")
    quantidade_parcelas = forms.IntegerField(min_value=2, required=False, label="Quantas parcelas? (Se Parcelada)")
    entrada = forms.DecimalField(max_digits=12, decimal_places=2, required=False, initial=0.00, label="Valor de Entrada (Se houver)", localize=True)

    class Meta:
        model = Divida
        fields = ['descricao', 'observacao', 'valor', 'data_vencimento', 'status']
        widgets = {
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'valor': 'Valor Total (Ou Mensalidade)'
        }

class VendaForm(LocalizedModelForm):
    class Meta:
        model = Venda
        fields = ['cliente', 'descricao', 'valor', 'data_venda']
        widgets = {
            'data_venda': forms.DateInput(attrs={'type': 'date'}),
        }

class EmprestimoForm(LocalizedModelForm):
    juros_percentual = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label="Juros Cobrado (%)", help_text="Opcional. Calcula automaticamente o total.")
    
    class Meta:
        model = Emprestimo
        fields = ['nome_pessoa', 'valor', 'juros_percentual', 'data_emprestimo', 'data_devolucao', 'status', 'observacao']
        widgets = {
            'data_emprestimo': forms.DateInput(attrs={'type': 'date'}),
            'data_devolucao': forms.DateInput(attrs={'type': 'date'}),
        }

class PerfilForm(LocalizedModelForm):
    class Meta:
        model = Perfil
        fields = ['nome_completo', 'cpf', 'telefone', 'endereco']
