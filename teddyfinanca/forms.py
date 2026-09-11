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
    class Meta:
        model = Divida
        fields = ['descricao', 'valor', 'data_vencimento', 'status']
        widgets = {
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
        }

class EmprestimoForm(forms.ModelForm):
    class Meta:
        model = Emprestimo
        fields = ['nome_pessoa', 'valor', 'data_emprestimo', 'data_devolucao', 'status', 'observacao']
        widgets = {
            'data_emprestimo': forms.DateInput(attrs={'type': 'date'}),
            'data_devolucao': forms.DateInput(attrs={'type': 'date'}),
        }
