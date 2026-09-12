from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from .models import Banco, Transacao, Divida, Emprestimo, VendaParcelada, Categoria, CompraParcelada
from .forms import TransacaoForm, DividaForm, EmprestimoForm, BancoForm, VendaParceladaForm, CategoriaForm

from django.contrib.auth.models import User

from functools import wraps
from django.shortcuts import redirect
from datetime import date
from .models import Assinatura

def check_assinatura(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            assinatura, _ = Assinatura.objects.get_or_create(usuario=request.user)
            dias_uso = (date.today() - request.user.date_joined.date()).days
            
            # Se for ativa ou estiver nos 30 dias de teste, libera.
            # Se a assinatura estiver ativa, garantimos que não está vencida (data_expiracao).
            if assinatura.ativa and assinatura.data_expiracao and assinatura.data_expiracao < date.today():
                assinatura.ativa = False
                assinatura.save()
                
            if not assinatura.ativa and dias_uso > 30:
                return redirect('teddyfinanca:bloqueado')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required(login_url='teddyfinanca:login')
def bloqueado(request):
    from datetime import date
    assinatura, _ = Assinatura.objects.get_or_create(usuario=request.user)
    dias_uso = (date.today() - request.user.date_joined.date()).days
    if assinatura.ativa or dias_uso <= 30:
        return redirect('teddyfinanca:dashboard')
    
    return render(request, 'teddyfinanca/bloqueado.html')

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
@check_assinatura
def dashboard(request):
    from datetime import date
    # -- LÓGICA DE GERAÇÃO PREGUIÇOSA DE RECORRENTES --
    hoje = date.today()
    geradores = Divida.objects.filter(usuario=request.user, tipo_recorrencia='RECORRENTE')
    for gerador in geradores:
        # Se o mês/ano do gerador for menor que o atual, gera o próximo
        while (gerador.data_vencimento.year < hoje.year) or (gerador.data_vencimento.year == hoje.year and gerador.data_vencimento.month < hoje.month):
            prox_mes = gerador.data_vencimento.month % 12 + 1
            prox_ano = gerador.data_vencimento.year + (gerador.data_vencimento.month // 12)
            try:
                nova_data = gerador.data_vencimento.replace(year=prox_ano, month=prox_mes)
            except ValueError:
                nova_data = gerador.data_vencimento.replace(year=prox_ano, month=prox_mes, day=28)
            
            # O gerador antigo vira UNICA
            gerador.tipo_recorrencia = 'UNICA'
            gerador.save()
            
            # O novo criado assume o posto de gerador RECORRENTE
            gerador = Divida.objects.create(
                usuario=gerador.usuario,
                descricao=gerador.descricao,
                valor=gerador.valor,
                data_vencimento=nova_data,
                tipo_recorrencia='RECORRENTE',
                status='PENDENTE'
            )
    # ------------------------------------------------

    if request.method == 'POST':
        if 'btn_transacao' in request.POST:
            form = TransacaoForm(request.POST)
            if form.is_valid():
                transacao = form.save(commit=False)
                transacao.usuario = request.user
                
                # Categoria Automática
                if not transacao.categoria:
                    desc_lower = transacao.descricao.lower()
                    CATEGORIAS_MAP = {
                        'pao': 'Alimentação',
                        'pão': 'Alimentação',
                        'mercado': 'Alimentação',
                        'comida': 'Alimentação',
                        'lanche': 'Alimentação',
                        'pizza': 'Alimentação',
                        'ifood': 'Alimentação',
                        'restaurante': 'Alimentação',
                        'gasolina': 'Combustível',
                        'combustivel': 'Combustível',
                        'combustível': 'Combustível',
                        'alcool': 'Combustível',
                        'álcool': 'Combustível',
                        'diesel': 'Combustível',
                        'posto': 'Combustível',
                        'farmacia': 'Saúde',
                        'farmácia': 'Saúde',
                        'remedio': 'Saúde',
                        'remédio': 'Saúde',
                        'medico': 'Saúde',
                        'médico': 'Saúde',
                        'luz': 'Contas da Casa',
                        'energia': 'Contas da Casa',
                        'agua': 'Contas da Casa',
                        'água': 'Contas da Casa',
                        'internet': 'Contas da Casa',
                        'aluguel': 'Contas da Casa'
                    }
                    
                    cat_nome = None
                    for palavra, categoria_alvo in CATEGORIAS_MAP.items():
                        if palavra in desc_lower:
                            cat_nome = categoria_alvo
                            break
                    
                    if cat_nome:
                        categoria_obj, created = Categoria.objects.get_or_create(
                            usuario=request.user, 
                            nome=cat_nome,
                            defaults={'tipo': 'SAIDA' if transacao.tipo == 'SAIDA' else 'ENTRADA'}
                        )
                        transacao.categoria = categoria_obj

                transacao.save()
                
                # Desconta ou adiciona ao saldo do banco
                if transacao.banco and transacao.status == 'PAGO':
                    if transacao.forma_pagamento == 'CREDITO':
                        if transacao.tipo == 'ENTRADA':
                            transacao.banco.limite_credito += transacao.valor
                        elif transacao.tipo == 'SAIDA':
                            transacao.banco.limite_credito -= transacao.valor
                    else:
                        if transacao.tipo == 'ENTRADA':
                            transacao.banco.saldo_atual += transacao.valor
                        elif transacao.tipo == 'SAIDA':
                            transacao.banco.saldo_atual -= transacao.valor
                    transacao.banco.save()

                messages.success(request, "Transação adicionada com sucesso!")
                return redirect('teddyfinanca:dashboard')
        elif 'btn_divida' in request.POST:
            form = DividaForm(request.POST)
            if form.is_valid():
                from datetime import timedelta
                from decimal import Decimal
                tipo = form.cleaned_data.get('tipo_divida')
                entrada = form.cleaned_data.get('entrada') or Decimal('0.00')
                valor_total = form.cleaned_data['valor']
                
                if tipo == 'PARCELADA':
                    qtd = form.cleaned_data.get('quantidade_parcelas') or 2
                    valor_parcela = (valor_total - entrada) / qtd
                    
                    compra = CompraParcelada.objects.create(
                        usuario=request.user,
                        descricao=form.cleaned_data['descricao'],
                        observacao=form.cleaned_data.get('observacao', ''),
                        valor_total=valor_total,
                        entrada=entrada,
                        quantidade_parcelas=qtd,
                        data_compra=form.cleaned_data['data_vencimento']
                    )
                    
                    for i in range(qtd):
                        Divida.objects.create(
                            compra_vinculada=compra,
                            usuario=request.user,
                            descricao=f"Parcela {i+1}",
                            observacao=form.cleaned_data.get('observacao', ''),
                            valor=valor_parcela,
                            data_vencimento=form.cleaned_data['data_vencimento'] + timedelta(days=30*i),
                            tipo_recorrencia='UNICA',
                            status=form.cleaned_data['status']
                        )
                    messages.success(request, f"{qtd} parcelas de R$ {valor_parcela:.2f} geradas e agrupadas com sucesso! Lembre-se de lançar a entrada de R$ {entrada:.2f} no fluxo diário se ela saiu hoje.")
                else:
                    divida = form.save(commit=False)
                    divida.usuario = request.user
                    divida.valor = valor_total - entrada
                    divida.tipo_recorrencia = 'RECORRENTE' if tipo == 'RECORRENTE' else 'UNICA'
                    divida.save()
                    messages.success(request, f"Dívida adicionada com sucesso! Lembre-se de lançar a entrada no fluxo diário se houver.")
                return redirect('teddyfinanca:dashboard')
        elif 'btn_emprestimo' in request.POST:
            form = EmprestimoForm(request.POST)
            if form.is_valid():
                emp = form.save(commit=False)
                emp.usuario = request.user
                emp.save()
                messages.success(request, "Empréstimo adicionado com sucesso!")
                return redirect('teddyfinanca:dashboard')
        elif 'btn_categoria' in request.POST:
            form = CategoriaForm(request.POST)
            if form.is_valid():
                categoria = form.save(commit=False)
                categoria.usuario = request.user
                categoria.save()
                messages.success(request, "Categoria criada com sucesso!")
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
                
                # Gerar as parcelas
                from datetime import timedelta
                valor_parcela = (venda.valor_total - venda.entrada) / venda.quantidade_parcelas
                for i in range(venda.quantidade_parcelas):
                    # aproximação de 30 dias para cada parcela
                    data_venc = venda.data_venda + timedelta(days=30*(i+1))
                    from .models import ParcelaVenda
                    ParcelaVenda.objects.create(
                        usuario=request.user,
                        venda=venda,
                        numero=i+1,
                        valor=valor_parcela,
                        data_vencimento=data_venc,
                        status='PENDENTE'
                    )

                messages.success(request, "Venda Parcelada adicionada com sucesso e parcelas geradas!")
                return redirect('teddyfinanca:dashboard')
        elif 'btn_trocar_senha' in request.POST:
            nova_senha = request.POST.get('nova_senha')
            if nova_senha:
                request.user.set_password(nova_senha)
                request.user.save()
                messages.success(request, "Senha atualizada com sucesso! Faça login novamente.")
                return redirect('teddyfinanca:login')

    transacao_form = TransacaoForm()
    transacao_form.fields['categoria'].queryset = Categoria.objects.filter(usuario=request.user)
    transacao_form.fields['banco'].queryset = Banco.objects.filter(usuario=request.user)
    
    divida_form = DividaForm()
    emprestimo_form = EmprestimoForm()
    banco_form = BancoForm()
    venda_form = VendaParceladaForm()
    categoria_form = CategoriaForm()

    # Filtra tudo pelo usuário logado
    bancos = Banco.objects.filter(usuario=request.user)
    vendas = VendaParcelada.objects.filter(usuario=request.user)

    # Cálculos dos mini-cards
    total_saldo_atual = bancos.aggregate(total=Sum('saldo_atual'))['total'] or 0
    total_limite = bancos.aggregate(total=Sum('limite_cheque_especial'))['total'] or 0
    total_saldo = total_saldo_atual + total_limite
    total_credito = bancos.aggregate(total=Sum('limite_credito'))['total'] or 0
    
    dividas_pendentes = Divida.objects.filter(usuario=request.user, status='PENDENTE')
    total_divida = dividas_pendentes.aggregate(total=Sum('valor'))['total'] or 0
    pago_divida = dividas_pendentes.aggregate(total=Sum('valor_pago'))['total'] or 0
    total_pagar = total_divida - pago_divida
    
    emprestimos_pendentes = Emprestimo.objects.filter(usuario=request.user, status='PENDENTE')
    total_emp = emprestimos_pendentes.aggregate(total=Sum('valor'))['total'] or 0
    pago_emp = emprestimos_pendentes.aggregate(total=Sum('valor_pago'))['total'] or 0
    total_receber_emp = total_emp - pago_emp
    
    from .models import ParcelaVenda
    parcelas_pendentes = ParcelaVenda.objects.filter(usuario=request.user, status='PENDENTE')
    total_parc = parcelas_pendentes.aggregate(total=Sum('valor'))['total'] or 0
    pago_parc = parcelas_pendentes.aggregate(total=Sum('valor_pago'))['total'] or 0
    total_receber_parcelas = total_parc - pago_parc
    
    total_receber = total_receber_emp + total_receber_parcelas
    
    saldo_liquido = total_saldo - total_pagar + total_receber
    
    # Atrasados
    hoje = date.today()
    dividas_atrasadas = dividas_pendentes.filter(data_vencimento__lt=hoje).order_by('data_vencimento')
    emprestimos_atrasados = emprestimos_pendentes.filter(data_devolucao__lt=hoje).order_by('data_devolucao')
    parcelas_atrasadas = parcelas_pendentes.filter(data_vencimento__lt=hoje).order_by('data_vencimento')

    # Dados para os Gráficos
    entradas_mes = Transacao.objects.filter(usuario=request.user, tipo='ENTRADA').aggregate(total=Sum('valor'))['total'] or 0
    saidas_mes = Transacao.objects.filter(usuario=request.user, tipo='SAIDA').aggregate(total=Sum('valor'))['total'] or 0
    
    # Agrupamento para gráfico de pizza de categorias
    import json
    saidas_por_categoria = Transacao.objects.filter(usuario=request.user, tipo='SAIDA').values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
    categorias_labels = []
    categorias_valores = []
    for item in saidas_por_categoria:
        cat = item['categoria__nome'] or 'Outros'
        categorias_labels.append(cat)
        categorias_valores.append(float(item['total']))
    
    categorias_labels_json = json.dumps(categorias_labels)
    categorias_valores_json = json.dumps(categorias_valores)
    
    # Dívidas Simples com paginação (5 por página) - Mostra todas não arquivadas e que NÃO estão vinculadas a uma compra parcelada
    dividas_list = Divida.objects.filter(usuario=request.user, arquivado=False, compra_vinculada__isnull=True).order_by('data_vencimento')
    paginator_dividas = Paginator(dividas_list, 5)
    page_divida = request.GET.get('page_divida')
    dividas = paginator_dividas.get_page(page_divida)
    
    # Compras Parceladas (Agrupadas)
    compras_list = CompraParcelada.objects.filter(usuario=request.user, arquivado=False).order_by('-data_compra')
    paginator_compras = Paginator(compras_list, 5)
    page_compra = request.GET.get('page_compra')
    compras = paginator_compras.get_page(page_compra)
    
    # Empréstimos Agrupados por Pessoa
    emprestimos_list_raw = Emprestimo.objects.filter(usuario=request.user, arquivado=False).order_by('nome_pessoa', 'data_devolucao')
    emprestimos_agrupados = {}
    
    for emp in emprestimos_list_raw:
        nome = emp.nome_pessoa.strip()
        if nome not in emprestimos_agrupados:
            emprestimos_agrupados[nome] = {
                'nome': nome,
                'itens': [],
                'total_geral': 0,
                'total_restante': 0,
                'todas_pagas': True,
                'id_str': f"emp_{len(emprestimos_agrupados)}"
            }
        
        grupo = emprestimos_agrupados[nome]
        grupo['itens'].append(emp)
        grupo['total_geral'] += emp.valor
        grupo['total_restante'] += emp.restante
        if emp.status == 'PENDENTE':
            grupo['todas_pagas'] = False

    emprestimos_groups_list = list(emprestimos_agrupados.values())
    paginator_emprestimos = Paginator(emprestimos_groups_list, 5)
    page_emprestimo = request.GET.get('page_emprestimo')
    emprestimos = paginator_emprestimos.get_page(page_emprestimo)
    
    # Vendas Parceladas com paginação (5 por página) - Mostra todas não arquivadas
    vendas_list = VendaParcelada.objects.filter(usuario=request.user, arquivado=False).order_by('-data_venda')
    paginator_vendas = Paginator(vendas_list, 5)
    page_venda = request.GET.get('page_venda')
    vendas = paginator_vendas.get_page(page_venda)
    
    # Transações (Fluxo) com paginação (10 por página)
    transacoes_list = Transacao.objects.filter(usuario=request.user).order_by('-data', '-id')
    paginator_transacoes = Paginator(transacoes_list, 10)
    page_transacao = request.GET.get('page_transacao')
    transacoes = paginator_transacoes.get_page(page_transacao)
    
    context = {
        'bancos': bancos,
        'dividas': dividas,
        'emprestimos': emprestimos,
        'vendas': vendas,
        'transacoes': transacoes,
        'total_saldo': total_saldo,
        'total_credito': total_credito,
        'total_pagar': total_pagar,
        'total_receber': total_receber,
        'saldo_liquido': saldo_liquido,
        'entradas_mes': entradas_mes,
        'saidas_mes': saidas_mes,
        'categorias_labels_json': categorias_labels_json,
        'categorias_valores_json': categorias_valores_json,
        'compras': compras,
        'transacao_form': transacao_form,
        'divida_form': divida_form,
        'emprestimo_form': emprestimo_form,
        'banco_form': banco_form,
        'venda_form': venda_form,
        'categoria_form': categoria_form,
        'categorias': Categoria.objects.filter(usuario=request.user),
        'dividas_atrasadas': dividas_atrasadas,
        'emprestimos_atrasados': emprestimos_atrasados,
        'parcelas_atrasadas': parcelas_atrasadas,
    }
    return render(request, 'teddyfinanca/dashboard.html', context)

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def pagar_divida(request, id):
    from decimal import Decimal
    try:
        divida = Divida.objects.get(id=id, usuario=request.user)
        
        if request.method == 'POST':
            valor = Decimal(request.POST.get('valor_pagamento', 0))
            divida.valor_pago += valor
            if divida.restante <= 0:
                divida.status = 'PAGO'
            divida.save()
            messages.success(request, f"Pagamento de R$ {valor} registrado em '{divida.descricao}'.")
        else:
            divida.status = 'PAGO'
            divida.valor_pago = divida.valor
            divida.save()
            messages.success(request, f"Dívida '{divida.descricao}' quitada!")
            
    except Divida.DoesNotExist:
        messages.error(request, "Dívida não encontrada.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def receber_emprestimo(request, id):
    from decimal import Decimal
    try:
        emp = Emprestimo.objects.get(id=id, usuario=request.user)
        if request.method == 'POST':
            valor = Decimal(request.POST.get('valor_pagamento', 0))
            emp.valor_pago += valor
            if emp.restante <= 0:
                emp.status = 'PAGO'
            emp.save()
            messages.success(request, f"Recebimento de R$ {valor} registrado de '{emp.nome_pessoa}'.")
        else:
            emp.status = 'PAGO'
            emp.valor_pago = emp.valor
            emp.save()
            messages.success(request, f"Empréstimo de '{emp.nome_pessoa}' totalmente recebido!")
    except Emprestimo.DoesNotExist:
        messages.error(request, "Empréstimo não encontrado.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def receber_parcela(request, id):
    from .models import ParcelaVenda
    from decimal import Decimal
    try:
        parcela = ParcelaVenda.objects.get(id=id, usuario=request.user)
        if request.method == 'POST':
            valor = Decimal(request.POST.get('valor_pagamento', 0))
            parcela.valor_pago += valor
            if parcela.restante <= 0:
                parcela.status = 'PAGO'
            parcela.save()
            messages.success(request, f"Recebimento de R$ {valor} na Parcela {parcela.numero} de '{parcela.venda.cliente}'.")
        else:
            parcela.status = 'PAGO'
            parcela.valor_pago = parcela.valor
            parcela.save()
            messages.success(request, f"Parcela {parcela.numero} de '{parcela.venda.cliente}' quitada!")
    except ParcelaVenda.DoesNotExist:
        messages.error(request, "Parcela não encontrada.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def deletar_venda(request, id):
    try:
        venda = VendaParcelada.objects.get(id=id, usuario=request.user)
        venda.delete()
        messages.success(request, "Venda parcelada e todas as suas faturas foram apagadas com sucesso!")
    except VendaParcelada.DoesNotExist:
        messages.error(request, "Venda não encontrada.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def arquivar_venda(request, id):
    try:
        venda = VendaParcelada.objects.get(id=id, usuario=request.user)
        venda.arquivado = True
        venda.save()
        messages.success(request, "Venda arquivada com sucesso!")
    except VendaParcelada.DoesNotExist:
        messages.error(request, "Venda não encontrada.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def arquivar_emprestimo(request, id):
    try:
        emp = Emprestimo.objects.get(id=id, usuario=request.user)
        emp.arquivado = True
        emp.save()
        messages.success(request, "Empréstimo arquivado com sucesso!")
    except Emprestimo.DoesNotExist:
        messages.error(request, "Empréstimo não encontrado.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def arquivar_divida(request, id):
    try:
        divida = Divida.objects.get(id=id, usuario=request.user)
        divida.arquivado = True
        divida.save()
        messages.success(request, "Dívida arquivada com sucesso!")
    except Divida.DoesNotExist:
        messages.error(request, "Dívida não encontrada.")
    return redirect('teddyfinanca:dashboard')
@login_required(login_url='teddyfinanca:login')
@check_assinatura
def deletar_divida(request, id):
    try:
        divida = Divida.objects.get(id=id, usuario=request.user)
        divida.delete()
        messages.success(request, f"Dívida '{divida.descricao}' deletada com sucesso!")
    except Divida.DoesNotExist:
        messages.error(request, "Dívida não encontrada.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def deletar_emprestimo(request, id):
    try:
        emp = Emprestimo.objects.get(id=id, usuario=request.user)
        emp.delete()
        messages.success(request, f"Empréstimo '{emp.nome_pessoa}' deletado com sucesso!")
    except Emprestimo.DoesNotExist:
        messages.error(request, "Empréstimo não encontrado.")
    return redirect('teddyfinanca:dashboard')
@login_required(login_url='teddyfinanca:login')
@check_assinatura
def deletar_categoria(request, id):
    try:
        categoria = Categoria.objects.get(id=id, usuario=request.user)
        categoria.delete()
        messages.success(request, f"Categoria '{categoria.nome}' deletada!")
    except Categoria.DoesNotExist:
        messages.error(request, "Categoria não encontrada.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def deletar_banco(request, id):
    try:
        banco = Banco.objects.get(id=id, usuario=request.user)
        banco.delete()
        messages.success(request, f"Banco '{banco.nome}' deletado!")
    except Banco.DoesNotExist:
        messages.error(request, "Banco não encontrado.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def editar_banco(request, id):
    try:
        banco = Banco.objects.get(id=id, usuario=request.user)
        if request.method == 'POST':
            banco.nome = request.POST.get('nome')
            banco.saldo_atual = request.POST.get('saldo_atual')
            banco.limite_cheque_especial = request.POST.get('limite_cheque_especial')
            banco.limite_credito = request.POST.get('limite_credito')
            banco.save()
            messages.success(request, f"Banco '{banco.nome}' atualizado!")
            return redirect('teddyfinanca:dashboard')
    except Banco.DoesNotExist:
        messages.error(request, "Banco não encontrado.")
    return redirect('teddyfinanca:dashboard')

from django.http import JsonResponse

def manifest_json(request):
    manifest = {
        "name": "Teddy Finanças",
        "short_name": "Finanças",
        "description": "Aplicativo de gestão financeira.",
        "start_url": "/financeiro/painel/",
        "display": "standalone",
        "background_color": "#198754",
        "theme_color": "#198754",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    return JsonResponse(manifest)

from django.http import HttpResponse

def sw_js(request):
    sw_code = """
self.addEventListener('install', (e) => {
    // console.log('[Service Worker] Install');
});

self.addEventListener('fetch', (e) => {
    // Passar reto (não fazer cache offline pesado, só permitir que o navegador identifique o app)
});
    """
    return HttpResponse(sw_code, content_type='application/javascript')
from django.shortcuts import redirect
from datetime import date
from .models import Assinatura

def check_assinatura(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            assinatura, _ = Assinatura.objects.get_or_create(usuario=request.user)
            dias_uso = (date.today() - request.user.date_joined.date()).days
            
            # Se for ativa ou estiver nos 30 dias de teste, libera.
            # Se a assinatura estiver ativa, garantimos que não está vencida (data_expiracao).
            if assinatura.ativa and assinatura.data_expiracao and assinatura.data_expiracao < date.today():
                assinatura.ativa = False
                assinatura.save()
                
            if not assinatura.ativa and dias_uso > 30:
                return redirect('teddyfinanca:bloqueado')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required(login_url='teddyfinanca:login')
def bloqueado(request):
    from datetime import date
    assinatura, _ = Assinatura.objects.get_or_create(usuario=request.user)
    dias_uso = (date.today() - request.user.date_joined.date()).days
    if assinatura.ativa or dias_uso <= 30:
        return redirect('teddyfinanca:dashboard')
    
    return render(request, 'teddyfinanca/bloqueado.html')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def deletar_compra(request, id):
    try:
        compra = CompraParcelada.objects.get(id=id, usuario=request.user)
        compra.delete()
        messages.success(request, f"Compra '{compra.descricao}' e todas as suas parcelas foram deletadas!")
    except CompraParcelada.DoesNotExist:
        messages.error(request, "Compra não encontrada.")
    return redirect('teddyfinanca:dashboard')

@login_required(login_url='teddyfinanca:login')
@check_assinatura
def arquivar_compra(request, id):
    try:
        compra = CompraParcelada.objects.get(id=id, usuario=request.user)
        compra.arquivado = True
        compra.save()
        compra.parcelas.update(arquivado=True)
        messages.success(request, f"Compra '{compra.descricao}' arquivada!")
    except CompraParcelada.DoesNotExist:
        messages.error(request, "Compra não encontrada.")
    return redirect('teddyfinanca:dashboard')
