from django import forms
from .models import Transacao, Divida, Emprestimo, VendaParcelada, Banco, Categoria

class BancoForm(forms.ModelForm):
    class Meta:
        model = Banco
        fields = ['nome', 'saldo_atual', 'limite_cheque_especial', 'limite_credito']

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'tipo']

class VendaParceladaForm(forms.ModelForm):
    class Meta:
        model = VendaParcelada
        fields = ['cliente', 'descricao', 'valor_total', 'entrada', 'quantidade_parcelas', 'data_venda']
        widgets = {
            'data_venda': forms.DateInput(attrs={'type': 'date'}),
        }

class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ['banco', 'categoria', 'tipo', 'valor', 'descricao', 'data', 'status']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }

class DividaForm(forms.ModelForm):
    TIPO_CHOICES = (
        ('UNICA', 'Única'),
        ('PARCELADA', 'Parcelada'),
        ('RECORRENTE', 'Fixa Mensal (Recorrente)'),
    )
    tipo_divida = forms.ChoiceField(choices=TIPO_CHOICES, initial='UNICA', label="Tipo de Dívida")
    quantidade_parcelas = forms.IntegerField(min_value=2, required=False, label="Quantas parcelas? (Se Parcelada)")
    entrada = forms.DecimalField(max_digits=12, decimal_places=2, required=False, initial=0.00, label="Valor de Entrada (Se houver)")

    class Meta:
        model = Divida
        fields = ['descricao', 'valor', 'data_vencimento', 'status']
        widgets = {
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'valor': 'Valor Total (Ou Mensalidade)'
        }

class EmprestimoForm(forms.ModelForm):
    class Meta:
        model = Emprestimo
        fields = ['nome_pessoa', 'valor', 'data_emprestimo', 'data_devolucao', 'status', 'observacao']
        widgets = {
            'data_emprestimo': forms.DateInput(attrs={'type': 'date'}),
            'data_devolucao': forms.DateInput(attrs={'type': 'date'}),
        }
