from django.urls import path
from . import views

app_name = 'teddyfinanca'

urlpatterns = [
    path('login/', views.financeiro_login, name='login'),
    path('cadastro/', views.financeiro_cadastro, name='cadastro'),
    path('logout/', views.financeiro_logout, name='logout'),
    path('painel/', views.dashboard, name='dashboard'),
    path('divida/<int:id>/pagar/', views.pagar_divida, name='pagar_divida'),
    path('emprestimo/<int:id>/receber/', views.receber_emprestimo, name='receber_emprestimo'),
    path('parcela/<int:id>/receber/', views.receber_parcela, name='receber_parcela'),
    path('venda/<int:id>/deletar/', views.deletar_venda, name='deletar_venda'),
    path('venda/<int:id>/arquivar/', views.arquivar_venda, name='arquivar_venda'),
    path('emprestimo/<int:id>/arquivar/', views.arquivar_emprestimo, name='arquivar_emprestimo'),
    path('divida/<int:id>/arquivar/', views.arquivar_divida, name='arquivar_divida'),
]
