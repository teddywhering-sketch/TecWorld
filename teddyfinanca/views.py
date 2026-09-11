from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from .models import Banco, Transacao, Divida, Emprestimo, VendaParcelada
from .forms import TransacaoForm, DividaForm, EmprestimoForm, BancoForm, VendaParceladaForm

from django.contrib.auth.models import User

def financeiro_login(request):
    if request.method == 'POST':
        usuario = request.POST.get('usuario')
        senha = request.POST.get('senha')
        user = authenticate(request, username=usuario, password=senha)
        if user is not None:
            auth_login(request, user)
            return redirect('teddyfinanca:dashboard')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'teddyfinanca/login.html')

def financeiro_cadastro(request):
    if request.method == 'POST':
        usuario = request.POST.get('usuario')
        senha = request.POST.get('senha')
        if User.objects.filter(username=usuario).exists():
            messages.error(request, 'Usuário já existe.')
        else:
            user = User.objects.create_user(username=usuario, password=senha)
            messages.success(request, 'Conta criada com sucesso! Faça login.')
            return redirect('teddyfinanca:login')
    return render(request, 'teddyfinanca/cadastro.html')

def financeiro_logout(request):
    auth_logout(request)
    return redirect('teddyfinanca:login')

@login_required(login_url='teddyfinanca:login')
def dashboard(request):
    if request.method == 'POST':
        if 'btn_transacao' in request.POST:
            form = TransacaoForm(request.POST)
            if form.is_valid():
                transacao = form.save(commit=False)
                transacao.usuario = request.user
                transacao.save()
                messages.success(request, "Transação adicionada com sucesso!")
                return redirect('teddyfinanca:dashboard')
        elif 'btn_divida' in request.POST:
            form = DividaForm(request.POST)
            if form.is_valid():
                divida = form.save(commit=False)
                divida.usuario = request.user
                divida.save()
                messages.success(request, "Dívida adicionada com sucesso!")
                return redirect('teddyfinanca:dashboard')
        elif 'btn_emprestimo' in request.POST:
            form = EmprestimoForm(request.POST)
            if form.is_valid():
                emp = form.save(commit=False)
                emp.usuario = request.user
                emp.save()
                messages.success(request, "Empréstimo adicionado com sucesso!")
                return redirect('teddyfinanca:dashboard')
        elif 'btn_banco' in request.POST:
            form = BancoForm(request.POST)
            if form.is_valid():
                banco = form.save(commit=False)
                banco.usuario = request.user
                banco.save()
                messages.success(request, "Banco adicionado com sucesso!")
                return redirect('teddyfinanca:dashboard')
        elif 'btn_venda' in request.POST:
            form = VendaParceladaForm(request.POST)
            if form.is_valid():
                venda = form.save(commit=False)
                venda.usuario = request.user
                venda.save()
                messages.success(request, "Venda Parcelada adicionada com sucesso!")
                return redirect('teddyfinanca:dashboard')
        elif 'btn_trocar_senha' in request.POST:
            nova_senha = request.POST.get('nova_senha')
            if nova_senha:
                request.user.set_password(nova_senha)
                request.user.save()
                messages.success(request, "Senha atualizada com sucesso! Faça login novamente.")
                return redirect('teddyfinanca:login')

    transacao_form = TransacaoForm()
    divida_form = DividaForm()
    emprestimo_form = EmprestimoForm()
    banco_form = BancoForm()
    venda_form = VendaParceladaForm()

    # Filtra tudo pelo usuário logado
    bancos = Banco.objects.filter(usuario=request.user)
    vendas = VendaParcelada.objects.filter(usuario=request.user)
    transacoes = Transacao.objects.filter(usuario=request.user).order_by('-data')[:10]

    # Cálculos dos mini-cards
    total_saldo = bancos.aggregate(total=Sum('saldo_atual'))['total'] or 0
    
    dividas_pendentes = Divida.objects.filter(usuario=request.user, status='PENDENTE')
    total_pagar = dividas_pendentes.aggregate(total=Sum('valor'))['total'] or 0
    
    emprestimos_pendentes = Emprestimo.objects.filter(usuario=request.user, status='PENDENTE')
    total_receber = emprestimos_pendentes.aggregate(total=Sum('valor'))['total'] or 0
    
    saldo_liquido = total_saldo - total_pagar + total_receber

    # Dados para os Gráficos
    entradas_mes = Transacao.objects.filter(usuario=request.user, tipo='ENTRADA').aggregate(total=Sum('valor'))['total'] or 0
    saidas_mes = Transacao.objects.filter(usuario=request.user, tipo='SAIDA').aggregate(total=Sum('valor'))['total'] or 0
    
    # Dívidas com paginação (5 por página)
    dividas_list = dividas_pendentes.order_by('data_vencimento')
    paginator_dividas = Paginator(dividas_list, 5)
    page_divida = request.GET.get('page_divida')
    dividas = paginator_dividas.get_page(page_divida)

    # Empréstimos com paginação (5 por página)
    emprestimos_list = emprestimos_pendentes.order_by('data_devolucao')
    paginator_emprestimos = Paginator(emprestimos_list, 5)
    page_emprestimo = request.GET.get('page_emprestimo')
    emprestimos = paginator_emprestimos.get_page(page_emprestimo)
    
    context = {
        'bancos': bancos,
        'dividas': dividas,
        'emprestimos': emprestimos,
        'vendas': vendas,
        'transacoes': transacoes,
        'total_saldo': total_saldo,
        'total_pagar': total_pagar,
        'total_receber': total_receber,
        'saldo_liquido': saldo_liquido,
        'entradas_mes': entradas_mes,
        'saidas_mes': saidas_mes,
        'transacao_form': transacao_form,
        'divida_form': divida_form,
        'emprestimo_form': emprestimo_form,
        'banco_form': banco_form,
        'venda_form': venda_form,
    }
    return render(request, 'teddyfinanca/dashboard.html', context)

@login_required(login_url='teddyfinanca:login')
def pagar_divida(request, id):
    try:
        divida = Divida.objects.get(id=id, usuario=request.user)
        divida.status = 'PAGO'
        divida.save()
        messages.success(request, f"Dívida '{divida.descricao}' marcada como paga!")
    except Divida.DoesNotExist:
        messages.error(request, "Dívida não encontrada.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
def receber_emprestimo(request, id):
    try:
        emp = Emprestimo.objects.get(id=id, usuario=request.user)
        emp.status = 'PAGO'
        emp.save()
        messages.success(request, f"Empréstimo de '{emp.nome_pessoa}' marcado como recebido!")
    except Emprestimo.DoesNotExist:
        messages.error(request, "Empréstimo não encontrado.")
    return redirect('teddyfinanca:dashboard')
