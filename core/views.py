from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum, Q
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, DeleteView

from .forms import ClienteForm, CombustivelForm, ConfirmarOSForm, FinalizarOSForm, LancamentoForm, OrcamentoForm, OrcamentoItemFormSet, OrdemServicoForm, ItemOSFormSet, TipoServicoForm, UsuarioForm, ProdutoForm, TransferenciaEstoqueForm, ProdutoOSForm, ClienteFinalForm
from .models import Cliente, FechamentoCaixa, Lancamento, Orcamento, OrdemServico, TipoServico, Produto, EstoqueTecnico, ProdutoOS, ClienteFinal, LogTransacao


class UserLoginView(LoginView):
    template_name = "registration/login.html"


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self): return self.request.user.is_staff

class OperacionalRequiredMixin(UserPassesTestMixin):
    def test_func(self): return self.request.user.is_staff or self.request.user.groups.filter(name="Secretaria").exists()

class ProvedorOrOperacionalRequiredMixin(UserPassesTestMixin):
    def test_func(self): 
        user = self.request.user
        return user.is_staff or user.groups.filter(name__in=["Secretaria", "Provedor"]).exists()


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        
        import json
        from django.db.models.functions import ExtractWeekDay
        from decimal import Decimal
        
        atuais = OrdemServico.objects.filter(arquivada_em__isnull=True)
        qs_semana = OrdemServico.objects.annotate(weekday=ExtractWeekDay('criado_em'))
        qs_tipos = OrdemServico.objects.all()

        is_operacional = self.request.user.is_staff or self.request.user.groups.filter(name="Secretaria").exists()
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()

        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                atuais = atuais.filter(cliente=cliente)
                qs_semana = qs_semana.filter(cliente=cliente)
                qs_tipos = qs_tipos.filter(cliente=cliente)
            else:
                atuais = atuais.none()
                qs_semana = qs_semana.none()
                qs_tipos = qs_tipos.none()
            entradas = Decimal('0.00')
            saidas = Decimal('0.00')
            combustivel = Decimal('0.00')
            saldo = Decimal('0.00')
            aguardando = atuais.filter(status=OrdemServico.Status.AGUARDANDO_CONFIRMACAO).count()
            qs_listas = atuais
            c.update({'ganho_os': 0, 'desc_combustivel': 0, 'desc_saidas': 0})
        elif not is_operacional:
            atuais = atuais.filter(Q(tecnico=self.request.user) | Q(tecnico__isnull=True))
            qs_semana = qs_semana.filter(tecnico=self.request.user)
            qs_tipos = qs_tipos.filter(tecnico=self.request.user)
            entradas = atuais.filter(status=OrdemServico.Status.CONCLUIDA).aggregate(v=Sum('valor'))['v'] or Decimal('0.00')
            aguardando = atuais.filter(status=OrdemServico.Status.AGUARDANDO_CONFIRMACAO).count()
            
            ultimo_fechamento = FechamentoCaixa.objects.first()
            lanc_tecnico = Lancamento.objects.filter(tecnico=self.request.user)
            if ultimo_fechamento:
                lanc_tecnico = lanc_tecnico.filter(criado_em__gt=ultimo_fechamento.fechado_em)
                
            combustivel = lanc_tecnico.filter(tipo=Lancamento.Tipo.SAIDA, categoria__icontains="combust").aggregate(v=Sum('valor'))['v'] or Decimal('0.00')
            saidas = lanc_tecnico.filter(tipo=Lancamento.Tipo.SAIDA).exclude(categoria__icontains="combust").aggregate(v=Sum('valor'))['v'] or Decimal('0.00')
            
            ganho_os = float(entradas)
            desc_combustivel = float(combustivel)
            desc_saidas = float(saidas)
            saldo = ganho_os - desc_combustivel - desc_saidas
            
            c.update({
                'ganho_os': ganho_os,
                'desc_combustivel': desc_combustivel,
                'desc_saidas': desc_saidas,
            })
            qs_listas = atuais.filter(Q(tecnico=self.request.user) | Q(tecnico__isnull=True))
        else:
            ultimo_fechamento = FechamentoCaixa.objects.first()
            lancamentos = Lancamento.objects.filter(criado_em__gt=ultimo_fechamento.fechado_em) if ultimo_fechamento else Lancamento.objects.all()
            entradas = lancamentos.filter(tipo=Lancamento.Tipo.ENTRADA).aggregate(v=Sum("valor"))["v"] or Decimal('0.00')
            saidas = lancamentos.filter(tipo=Lancamento.Tipo.SAIDA).aggregate(v=Sum("valor"))["v"] or Decimal('0.00')
            combustivel = lancamentos.filter(tipo=Lancamento.Tipo.SAIDA, categoria="Combustível").aggregate(v=Sum("valor"))["v"] or Decimal('0.00')
            saldo = entradas - saidas
            aguardando = atuais.filter(status=OrdemServico.Status.AGUARDANDO_CONFIRMACAO).count()
            qs_listas = atuais

        c.update(
            os_abertas=atuais.exclude(status__in=["CONCLUIDA", "CANCELADA"]).count(), 
            os_hoje=atuais.filter(agendamento__date=timezone.localdate()).count(), 
            entradas=entradas, 
            saidas=saidas,
            combustivel=combustivel,
            saldo=saldo,
            aguardando_confirmacao=aguardando, 
            os_abertas_list=qs_listas.filter(status__in=["ABERTA", "AGENDADA"]).select_related("cliente", "tecnico").order_by('-id')[:5],
            os_aguardando_list=qs_listas.filter(status__in=["EM_ANDAMENTO", "AGUARDANDO_CONFIRMACAO"]).select_related("cliente", "tecnico").order_by('-id')[:5],
            os_concluidas_list=qs_listas.filter(status="CONCLUIDA").select_related("cliente", "tecnico").order_by('-id')[:5]
        )
        
        qs_tipos = qs_tipos.values('tipo__nome').annotate(total=Count('id')).order_by('-total')
        c['grafico_tipos'] = json.dumps({'labels': [t['tipo__nome'] or 'Sem Tipo' for t in qs_tipos], 'data': [t['total'] for t in qs_tipos]})
        
        qs_semana = qs_semana.values('weekday').annotate(total=Count('id'))
        dias = {2: 'Segunda', 3: 'Terça', 4: 'Quarta', 5: 'Quinta', 6: 'Sexta', 7: 'Sábado', 1: 'Domingo'}
        semana_counts = {d: 0 for d in dias.values()}
        for item in qs_semana:
            if item['weekday'] in dias:
                semana_counts[dias[item['weekday']]] += item['total']
        c['grafico_semana'] = json.dumps({'labels': list(semana_counts.keys()), 'data': list(semana_counts.values())})
        
        c['tabela_precos'] = TipoServico.objects.filter(ativo=True).order_by('nome')
        
        return c


class SearchableListView(LoginRequiredMixin, ListView):
    paginate_by = 10
    def get_queryset(self):
        qs = super().get_queryset(); q = self.request.GET.get("q")
        return qs.filter(nome__icontains=q) if q and self.model is Cliente else qs

class ClienteListView(OperacionalRequiredMixin, SearchableListView): model = Cliente
class ClienteCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView): model = Cliente; form_class = ClienteForm; success_url = reverse_lazy("cliente-list")
class ClienteUpdateView(LoginRequiredMixin, OperacionalRequiredMixin, UpdateView): model = Cliente; form_class = ClienteForm; success_url = reverse_lazy("cliente-list")

class ClienteFinalListView(ProvedorOrOperacionalRequiredMixin, SearchableListView): 
    model = ClienteFinal
    def get_queryset(self):
        qs = super().get_queryset().select_related("provedor")
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                qs = qs.filter(provedor=cliente)
            else:
                qs = qs.none()
        return qs

class ClienteFinalCreateView(LoginRequiredMixin, ProvedorOrOperacionalRequiredMixin, CreateView): 
    model = ClienteFinal
    form_class = ClienteFinalForm
    template_name = "core/form.html"
    success_url = reverse_lazy("clientefinal-list")
    extra_context = {"title": "Novo Cliente Final"}
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                form.fields['provedor'].queryset = Cliente.objects.filter(id=cliente.id)
                form.fields['provedor'].initial = cliente
            else:
                form.fields['provedor'].queryset = Cliente.objects.none()
        return form

class ClienteFinalUpdateView(LoginRequiredMixin, ProvedorOrOperacionalRequiredMixin, UpdateView): 
    model = ClienteFinal
    form_class = ClienteFinalForm
    template_name = "core/form.html"
    success_url = reverse_lazy("clientefinal-list")
    extra_context = {"title": "Editar Cliente Final"}
    
    def get_queryset(self):
        qs = super().get_queryset()
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            return qs.filter(provedor=cliente) if cliente else qs.none()
        return qs
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                form.fields['provedor'].queryset = Cliente.objects.filter(id=cliente.id)
            else:
                form.fields['provedor'].queryset = Cliente.objects.none()
        return form


class OrdemListView(LoginRequiredMixin, ListView):
    model = OrdemServico
    paginate_by = 10
    
    def get_queryset(self):
        qs = OrdemServico.objects.select_related("cliente", "tecnico")
        is_operacional = self.request.user.is_staff or self.request.user.groups.filter(name="Secretaria").exists()
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                qs = qs.filter(cliente=cliente)
            else:
                qs = qs.none()
        elif not is_operacional:
            qs = qs.filter(Q(tecnico=self.request.user) | Q(tecnico__isnull=True))
            
        aba = self.request.GET.get("aba", "abertas")
        if aba == "arquivadas":
            qs = qs.filter(arquivada_em__isnull=False)
        else:
            qs = qs.filter(arquivada_em__isnull=True)
            if aba == "abertas":
                qs = qs.filter(status__in=["ABERTA", "AGENDADA"])
            elif aba == "aguardando":
                qs = qs.filter(status__in=["EM_ANDAMENTO", "AGUARDANDO_CONFIRMACAO"])
            elif aba == "concluidas":
                qs = qs.filter(status="CONCLUIDA")
                
        return qs.order_by('-id')

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        aba = self.request.GET.get("aba", "abertas")
        c["aba_atual"] = aba
        
        is_operacional = self.request.user.is_staff or self.request.user.groups.filter(name="Secretaria").exists()
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        qs_base = OrdemServico.objects.filter(arquivada_em__isnull=True)
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                qs_base = qs_base.filter(cliente=cliente)
                c["count_arquivadas"] = OrdemServico.objects.filter(cliente=cliente, arquivada_em__isnull=False).count()
            else:
                qs_base = qs_base.none()
                c["count_arquivadas"] = 0
        elif not is_operacional:
            qs_base = qs_base.filter(Q(tecnico=self.request.user) | Q(tecnico__isnull=True))
            c["count_arquivadas"] = 0
        else:
            c["count_arquivadas"] = OrdemServico.objects.filter(arquivada_em__isnull=False).count()
            
        c["count_abertas"] = qs_base.filter(status__in=["ABERTA", "AGENDADA"]).count()
        c["count_aguardando"] = qs_base.filter(status__in=["EM_ANDAMENTO", "AGUARDANDO_CONFIRMACAO"]).count()
        c["count_concluidas"] = qs_base.filter(status="CONCLUIDA").count()
        
        if is_operacional:
            from django.contrib.auth.models import User
            from django.db.models import Sum
            from decimal import Decimal
            import math
            tecnicos = User.objects.filter(ordens_tecnicas__in=qs_base).distinct()
            resumo_tecnicos_os = []
            
            ultimo = FechamentoCaixa.objects.first()
            qs_lanc = Lancamento.objects.filter(criado_em__gt=ultimo.fechado_em) if ultimo else Lancamento.objects.all()
            
            for t in tecnicos:
                ordens_concluidas = qs_base.filter(tecnico=t, status="CONCLUIDA")
                valor_ordens = ordens_concluidas.aggregate(v=Sum("valor"))["v"] or Decimal("0.00")
                
                combustivel_t = qs_lanc.filter(tecnico=t, tipo="SAIDA", categoria__icontains="combust").aggregate(v=Sum("valor"))["v"] or Decimal("0.00")
                
                ganho_os = float(valor_ordens)
                custo_combustivel = float(combustivel_t)
                saldo_tecnico = ganho_os - custo_combustivel
                
                resumo_tecnicos_os.append({
                    "tecnico": t.get_full_name() or t.username,
                    "valor_ordens": float(valor_ordens),
                    "ganho_os": ganho_os,
                    "combustivel_total": float(combustivel_t),
                    "custo_combustivel": custo_combustivel,
                    "saldo": saldo_tecnico
                })
            c["resumo_tecnicos_os"] = resumo_tecnicos_os

        return c

class OrdemDetailView(LoginRequiredMixin, DetailView):
    model = OrdemServico
    def get_queryset(self):
        qs = OrdemServico.objects.select_related("cliente", "tecnico")
        is_operacional = self.request.user.is_staff or self.request.user.groups.filter(name="Secretaria").exists()
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            return qs.filter(cliente=cliente) if cliente else qs.none()
        elif is_operacional:
            return qs
        else:
            return qs.filter(Q(tecnico=self.request.user) | Q(tecnico__isnull=True))

class OrdemCreateView(LoginRequiredMixin, ProvedorOrOperacionalRequiredMixin, CreateView):
    model = OrdemServico; form_class = OrdemServicoForm; success_url = reverse_lazy("ordem-list")
    def get_initial(self):
        initial = super().get_initial()
        if 'cliente' in self.request.GET: initial['cliente'] = self.request.GET['cliente']
        if 'descricao' in self.request.GET: initial['descricao'] = self.request.GET['descricao']
        if 'valor' in self.request.GET: initial['valor'] = self.request.GET['valor']
        return initial

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

    def get_form(self, form_class=None):
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
        return form

class OrdemUpdateView(LoginRequiredMixin, ProvedorOrOperacionalRequiredMixin, UpdateView): 
    model = OrdemServico; form_class = OrdemServicoForm; success_url = reverse_lazy("ordem-list")
    
    def get_queryset(self):
        qs = super().get_queryset()
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            return qs.filter(cliente=cliente) if cliente else qs.none()
        return qs


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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                form.fields['cliente'].queryset = Cliente.objects.filter(id=cliente.id)
                form.fields['cliente_final'].queryset = ClienteFinal.objects.filter(provedor=cliente)
            else:
                form.fields['cliente'].queryset = Cliente.objects.none()
                form.fields['cliente_final'].queryset = ClienteFinal.objects.none()
        return form

class OrdemDeleteView(LoginRequiredMixin, ProvedorOrOperacionalRequiredMixin, DeleteView):
    model = OrdemServico
    success_url = reverse_lazy("ordem-list")

    def get_queryset(self):
        qs = super().get_queryset().filter(status="ABERTA")
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                qs = qs.filter(cliente=cliente)
            else:
                qs = qs.none()
        return qs

class TipoServicoListView(LoginRequiredMixin, OperacionalRequiredMixin, ListView): model = TipoServico; paginate_by = 10
class TipoServicoCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView): model = TipoServico; form_class = TipoServicoForm; success_url = reverse_lazy("tipo-servico-list"); extra_context = {"title": "Novo Tipo de Serviço"}
class TipoServicoUpdateView(LoginRequiredMixin, OperacionalRequiredMixin, UpdateView): model = TipoServico; form_class = TipoServicoForm; success_url = reverse_lazy("tipo-servico-list"); extra_context = {"title": "Editar Tipo de Serviço"}

class IniciarOSView(LoginRequiredMixin, View):
    def post(self, request, pk):
        os = OrdemServico.objects.filter(pk=pk, tecnico=request.user).exclude(status__in=[OrdemServico.Status.CONCLUIDA, OrdemServico.Status.CANCELADA]).first()
        if not os: raise PermissionDenied
        os.status = OrdemServico.Status.EM_ANDAMENTO
        os.iniciado_em = timezone.now()
        os.save(update_fields=["status", "iniciado_em", "atualizado_em"])
        messages.success(request, f"Atendimento da {os} iniciado. Cronômetro rodando!")
        return redirect("ordem-detail", pk=os.pk)

class FinalizarOSView(LoginRequiredMixin, View):
    def get_object(self, request, pk):
        os = OrdemServico.objects.filter(pk=pk, tecnico=request.user).exclude(status__in=[OrdemServico.Status.CONCLUIDA, OrdemServico.Status.CANCELADA]).first()
        if not os: raise PermissionDenied
        return os
    def get(self, request, pk):
        os = self.get_object(request, pk)
        return render(request, "core/finalizar_os.html", {"object": os, "form": FinalizarOSForm(instance=os)})
    def post(self, request, pk):
        os = self.get_object(request, pk)
        form = FinalizarOSForm(request.POST, request.FILES, instance=os)
        if not form.is_valid():
            return render(request, "core/finalizar_os.html", {"object": os, "form": form})
        form.save(commit=False)
        os.status = OrdemServico.Status.AGUARDANDO_CONFIRMACAO
        if not os.finalizado_em:
            os.finalizado_em = timezone.now()
        os.save(update_fields=["status", "finalizado_em", "atualizado_em", "nome_cliente_instalado", "solucao", "foto_1", "foto_2", "foto_3"])
        messages.success(request, f"{os} enviada para confirmação do administrador.")
        return redirect("ordem-detail", pk=os.pk)

class ConfirmarOSView(LoginRequiredMixin, OperacionalRequiredMixin, View):
    def get_object(self, pk):
        os = OrdemServico.objects.filter(pk=pk, status=OrdemServico.Status.AGUARDANDO_CONFIRMACAO).first()
        if not os:
            raise PermissionDenied
        return os
    def get(self, request, pk):
        os = self.get_object(pk)
        return render(request, "core/confirmar_os.html", {"object": os, "form": ConfirmarOSForm(instance=os)})
    def post(self, request, pk):
        os = self.get_object(pk)
        form = ConfirmarOSForm(request.POST, request.FILES, instance=os)
        if not form.is_valid():
            return render(request, "core/confirmar_os.html", {"object": os, "form": form})
        form.save()
        os.status = OrdemServico.Status.CONCLUIDA
        os.save(update_fields=["status", "atualizado_em"])
        Lancamento.objects.get_or_create(ordem_servico=os, defaults={"descricao": f"Recebimento da {os}", "tipo": Lancamento.Tipo.ENTRADA, "categoria": "Prestação de serviço", "valor": os.valor, "tecnico": os.tecnico})
        messages.success(request, f"{os} confirmada e lançada no financeiro.")
        return redirect("ordem-detail", pk=os.pk)


class OrcamentoListView(LoginRequiredMixin, ProvedorOrOperacionalRequiredMixin, ListView): 
    model = Orcamento
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                qs = qs.filter(cliente=cliente)
            else:
                qs = qs.none()
        return qs
class OrcamentoCreateView(LoginRequiredMixin, ProvedorOrOperacionalRequiredMixin, CreateView):
    model = Orcamento
    form_class = OrcamentoForm
    success_url = reverse_lazy("orcamento-list")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['produtos_catalogo'] = Produto.objects.all()
        if self.request.POST:
            data['itens'] = OrcamentoItemFormSet(self.request.POST)
        else:
            data['itens'] = OrcamentoItemFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        itens = context['itens']
        form.instance.responsavel = self.request.user
        if itens.is_valid():
            self.object = form.save()
            itens.instance = self.object
            itens.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_form(self, form_class=None):
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
        return form

class OrcamentoUpdateView(LoginRequiredMixin, ProvedorOrOperacionalRequiredMixin, UpdateView):
    model = Orcamento
    form_class = OrcamentoForm
    success_url = reverse_lazy("orcamento-list")

    def get_queryset(self):
        qs = super().get_queryset()
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            return qs.filter(cliente=cliente) if cliente else qs.none()
        return qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['produtos_catalogo'] = Produto.objects.all()
        if self.request.POST:
            data['itens'] = OrcamentoItemFormSet(self.request.POST, instance=self.object)
        else:
            data['itens'] = OrcamentoItemFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        itens = context['itens']
        if itens.is_valid():
            self.object = form.save()
            itens.instance = self.object
            itens.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            if cliente:
                form.fields['cliente'].queryset = Cliente.objects.filter(id=cliente.id)
                form.fields['cliente_final'].queryset = ClienteFinal.objects.filter(provedor=cliente)
            else:
                form.fields['cliente'].queryset = Cliente.objects.none()
                form.fields['cliente_final'].queryset = ClienteFinal.objects.none()
        return form

from django.views import View

class GerarOSFromOrcamentoView(LoginRequiredMixin, OperacionalRequiredMixin, View):
    def post(self, request, pk):
        orcamento = get_object_or_404(Orcamento, pk=pk)
        if orcamento.status == Orcamento.Status.APROVADO:
            descricao_os = orcamento.descricao + "\n\n--- ITENS ---\n"
            for item in orcamento.itens.all():
                descricao_os += f"- {item.quantidade}x {item.descricao} (R$ {item.preco_unitario})\n"
            
            from urllib.parse import urlencode
            params = urlencode({
                'cliente': orcamento.cliente_id,
                'descricao': descricao_os,
                'valor': orcamento.valor_total,
            })
            messages.info(request, "Preencha os dados restantes para gerar a OS.")
            return redirect(f"{reverse('ordem-create')}?{params}")
        messages.error(request, "Apenas orçamentos aprovados podem gerar OS.")
        return redirect("orcamento-list")

class OrcamentoPrintView(LoginRequiredMixin, ProvedorOrOperacionalRequiredMixin, DetailView):
    model = Orcamento
    template_name = "core/orcamento_print.html"
    
    def get_queryset(self):
        qs = super().get_queryset()
        is_provedor = self.request.user.groups.filter(name="Provedor").exists()
        if is_provedor:
            cliente = getattr(self.request.user, 'cliente_provedor', None)
            return qs.filter(cliente=cliente) if cliente else qs.none()
        return qs

class FinanceiroView(LoginRequiredMixin, OperacionalRequiredMixin, ListView):
    model = Lancamento; template_name = "core/financeiro.html"; paginate_by = 10
    def get_queryset(self):
        ultimo = FechamentoCaixa.objects.first()
        return Lancamento.objects.filter(criado_em__gt=ultimo.fechado_em) if ultimo else Lancamento.objects.all()
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs); qs = self.get_queryset()
        c["entradas"] = qs.filter(tipo="ENTRADA").aggregate(v=Sum("valor"))["v"] or 0; c["saidas"] = qs.filter(tipo="SAIDA").aggregate(v=Sum("valor"))["v"] or 0; c["saldo"] = c["entradas"] - c["saidas"]
        
        from django.contrib.auth.models import User
        tecnicos = User.objects.filter(lancamentos__in=qs).distinct()
        resumo_tecnicos = []
        for t in tecnicos:
            qs_t = qs.filter(tecnico=t)
            entradas_t = qs_t.filter(tipo="ENTRADA").aggregate(v=Sum("valor"))["v"] or 0
            saidas_t = qs_t.filter(tipo="SAIDA").exclude(categoria__icontains="combust").aggregate(v=Sum("valor"))["v"] or 0
            combustivel_t = qs_t.filter(tipo="SAIDA", categoria__icontains="combust").aggregate(v=Sum("valor"))["v"] or 0
            
            ganho = float(entradas_t)
            desconto_combustivel = float(combustivel_t)
            descontos_outros = float(saidas_t)
            saldo_receber = ganho - desconto_combustivel - descontos_outros
            
            resumo_tecnicos.append({
                "tecnico": t.get_full_name() or t.username,
                "entradas": entradas_t,
                "saidas": saidas_t,
                "combustivel": combustivel_t,
                "ganho": ganho,
                "desconto_combustivel": desconto_combustivel,
                "saldo_receber": saldo_receber
            })
        c["resumo_tecnicos"] = resumo_tecnicos
        return c
class LancamentoCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView): model = Lancamento; form_class = LancamentoForm; success_url = reverse_lazy("financeiro")

class CombustivelCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView):
    model = Lancamento
    form_class = CombustivelForm
    template_name = "core/form.html"
    success_url = reverse_lazy("financeiro")
    extra_context = {"title": "Lançar Combustível"}
    def form_valid(self, form):
        form.instance.tipo = Lancamento.Tipo.SAIDA
        form.instance.categoria = "Combustível"
        messages.success(self.request, "Gasto de combustível lançado com sucesso.")
        return super().form_valid(form)

class AdiantamentoCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView):
    model = Lancamento
    from .forms import AdiantamentoForm
    form_class = AdiantamentoForm
    template_name = "core/form.html"
    success_url = reverse_lazy("financeiro")
    extra_context = {"title": "Lançar Pagamento / Adiantamento"}
    def form_valid(self, form):
        form.instance.tipo = Lancamento.Tipo.SAIDA
        form.instance.categoria = "Adiantamento / Pagamento"
        messages.success(self.request, "Pagamento/Adiantamento ao técnico lançado com sucesso.")
        return super().form_valid(form)

class FecharFinanceiroView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request):
        ultimo = FechamentoCaixa.objects.first(); qs = Lancamento.objects.filter(criado_em__gt=ultimo.fechado_em) if ultimo else Lancamento.objects.all()
        entradas = qs.filter(tipo=Lancamento.Tipo.ENTRADA).aggregate(v=Sum("valor"))["v"] or 0
        saidas = qs.filter(tipo=Lancamento.Tipo.SAIDA).aggregate(v=Sum("valor"))["v"] or 0
        FechamentoCaixa.objects.create(entradas=entradas, saidas=saidas, responsavel=request.user)
        for os in OrdemServico.objects.filter(status=OrdemServico.Status.CONCLUIDA, arquivada_em__isnull=True):
            os.arquivada_em = timezone.now()
            os.save(update_fields=["arquivada_em"])
        messages.success(request, "Período fechado com sucesso! Saldo zerado visualmente.")
        return redirect("financeiro")

class LogTransacaoListView(LoginRequiredMixin, ListView):
    model = LogTransacao
    template_name = "core/log_transacao.html"
    paginate_by = 50
    def get_queryset(self):
        qs = super().get_queryset()
        if not (self.request.user.is_staff or self.request.user.groups.filter(name="Secretaria").exists()):
            # Técnicos só vêem os próprios logs ou logs de coisas relacionadas a eles
            # Como a descrição pode conter o nome, deixamos ver logs onde foram o autor ou o nome deles tá lá
            qs = qs.filter(models.Q(usuario=self.request.user) | models.Q(descricao__icontains=self.request.user.username))
        return qs


class RelatorioView(LoginRequiredMixin, OperacionalRequiredMixin, TemplateView):
    template_name = "core/relatorios.html"
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs); c["status"] = [{"nome": label, "total": OrdemServico.objects.filter(status=value).count()} for value, label in OrdemServico.Status.choices]; c["tecnicos"] = OrdemServico.objects.values("tecnico__username").annotate(total=Count("id")).order_by("-total"); return c

class UsuarioListView(LoginRequiredMixin, AdminRequiredMixin, ListView): model = User; template_name = "core/usuario_list.html"; queryset = User.objects.order_by("username"); paginate_by = 10
class UsuarioCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView): model = User; form_class = UsuarioForm; template_name = "core/usuario_form.html"; success_url = reverse_lazy("usuario-list")

class ProdutoListView(LoginRequiredMixin, OperacionalRequiredMixin, ListView): model = Produto; paginate_by = 10
class ProdutoCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView): model = Produto; form_class = ProdutoForm; template_name = "core/form.html"; success_url = reverse_lazy("produto-list"); extra_context = {"title": "Novo Produto"}
class ProdutoUpdateView(LoginRequiredMixin, OperacionalRequiredMixin, UpdateView): model = Produto; form_class = ProdutoForm; template_name = "core/form.html"; success_url = reverse_lazy("produto-list"); extra_context = {"title": "Editar Produto"}

class EstoqueTecnicoListView(LoginRequiredMixin, OperacionalRequiredMixin, ListView):
    paginate_by = 10
    model = EstoqueTecnico
    template_name = "core/estoque_tecnico_list.html"
    def get_queryset(self): return EstoqueTecnico.objects.select_related("tecnico", "produto")

class TransferenciaEstoqueView(LoginRequiredMixin, OperacionalRequiredMixin, View):
    def get(self, request):
        return render(request, "core/form.html", {"form": TransferenciaEstoqueForm(), "title": "Transferir Estoque"})
    def post(self, request):
        form = TransferenciaEstoqueForm(request.POST)
        if form.is_valid():
            produto = form.cleaned_data["produto"]
            tecnico = form.cleaned_data["tecnico"]
            quantidade = form.cleaned_data["quantidade"]
            if produto.estoque_base < quantidade:
                messages.error(request, f"Estoque insuficiente na Sede. Saldo atual: {produto.estoque_base}")
                return render(request, "core/form.html", {"form": form, "title": "Transferir Estoque"})
            
            produto.estoque_base -= quantidade
            produto.save()
            
            estoque, created = EstoqueTecnico.objects.get_or_create(tecnico=tecnico, produto=produto)
            estoque.quantidade += quantidade
            estoque.save()
            
            messages.success(request, f"{quantidade} {produto.unidade} de {produto.nome} transferidos para {tecnico.username}.")
            return redirect("estoque-tecnico-list")
        return render(request, "core/form.html", {"form": form, "title": "Transferir Estoque"})

class BaixaMaterialOSView(LoginRequiredMixin, View):
    def get_object(self, request, pk):
        os = OrdemServico.objects.filter(pk=pk, tecnico=request.user).first()
        if not os: raise PermissionDenied
        return os
    def get(self, request, pk):
        os = self.get_object(request, pk)
        return render(request, "core/baixa_material_os.html", {"object": os, "form": ProdutoOSForm()})
    def post(self, request, pk):
        os = self.get_object(request, pk)
        form = ProdutoOSForm(request.POST)
        if form.is_valid():
            produto = form.cleaned_data["produto"]
            quantidade = form.cleaned_data["quantidade"]
            estoque = EstoqueTecnico.objects.filter(tecnico=request.user, produto=produto).first()
            if not estoque or estoque.quantidade < quantidade:
                messages.error(request, f"Você não possui {quantidade} {produto.unidade} de {produto.nome} no seu estoque. Saldo: {estoque.quantidade if estoque else 0}")
                return render(request, "core/baixa_material_os.html", {"object": os, "form": form})
            
            estoque.quantidade -= quantidade
            estoque.save()
            
            ProdutoOS.objects.create(ordem_servico=os, produto=produto, quantidade=quantidade)
            messages.success(request, f"{quantidade} {produto.unidade} de {produto.nome} baixados na OS.")
            return redirect("ordem-detail", pk=os.pk)
        return render(request, "core/baixa_material_os.html", {"object": os, "form": form})

class MinhaSenhaView(LoginRequiredMixin, PasswordChangeView):
    template_name = "core/senha_form.html"; form_class = PasswordChangeForm; success_url = reverse_lazy("dashboard")

class UsuarioSenhaView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request, pk):
        return render(request, "core/senha_form.html", {"form": SetPasswordForm(User.objects.get(pk=pk)), "usuario_alvo": User.objects.get(pk=pk)})
    def post(self, request, pk):
        usuario = User.objects.get(pk=pk); form = SetPasswordForm(usuario, request.POST)
        if form.is_valid():
            form.save(); messages.success(request, f"Senha de {usuario.username} atualizada."); return redirect("usuario-list")
        return render(request, "core/senha_form.html", {"form": form, "usuario_alvo": usuario})

from .models import ConfiguracaoSistema

class ConfiguracaoSistemaUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ConfiguracaoSistema
    template_name = "core/form.html"
    fields = ['logo']
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        return ConfiguracaoSistema.load()

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["titulo"] = "Configurações do Sistema"
        return c

class PuxarOSView(LoginRequiredMixin, View):
    def post(self, request, pk):
        os = OrdemServico.objects.filter(pk=pk, tecnico__isnull=True).exclude(status__in=[OrdemServico.Status.CONCLUIDA, OrdemServico.Status.CANCELADA]).first()
        if not os:
            raise PermissionDenied
        os.tecnico = request.user
        os.save(update_fields=["tecnico", "atualizado_em"])
        messages.success(request, f"Você assumiu a OS {os}.")
        return redirect("ordem-detail", pk=os.pk)
