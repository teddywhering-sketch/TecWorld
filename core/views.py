from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from .forms import ClienteForm, CombustivelForm, ConfirmarOSForm, FinalizarOSForm, LancamentoForm, OrcamentoForm, OrdemServicoForm, TipoServicoForm, UsuarioForm, ProdutoForm, TransferenciaEstoqueForm, ProdutoOSForm, ClienteFinalForm
from .models import Cliente, FechamentoCaixa, Lancamento, Orcamento, OrdemServico, TipoServico, Produto, EstoqueTecnico, ProdutoOS, ClienteFinal


class UserLoginView(LoginView):
    template_name = "registration/login.html"


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self): return self.request.user.is_staff

class OperacionalRequiredMixin(UserPassesTestMixin):
    def test_func(self): return self.request.user.is_staff or self.request.user.groups.filter(name="Secretaria").exists()


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

        if not is_operacional:
            atuais = atuais.filter(tecnico=self.request.user)
            qs_semana = qs_semana.filter(tecnico=self.request.user)
            qs_tipos = qs_tipos.filter(tecnico=self.request.user)
            entradas = atuais.filter(status=OrdemServico.Status.CONCLUIDA).aggregate(v=Sum('valor'))['v'] or Decimal('0.00')
            aguardando = atuais.filter(status=OrdemServico.Status.AGUARDANDO_CONFIRMACAO).count()
            
            ultimo_fechamento = FechamentoCaixa.objects.first()
            lanc_tecnico = Lancamento.objects.filter(tecnico=self.request.user)
            lanc_tecnico_os = Lancamento.objects.filter(ordem_servico__tecnico=self.request.user)
            if ultimo_fechamento:
                lanc_tecnico = lanc_tecnico.filter(criado_em__gt=ultimo_fechamento.fechado_em)
                lanc_tecnico_os = lanc_tecnico_os.filter(criado_em__gt=ultimo_fechamento.fechado_em)
            saidas = lanc_tecnico_os.filter(tipo=Lancamento.Tipo.SAIDA).aggregate(v=Sum('valor'))['v'] or Decimal('0.00')
            combustivel = lanc_tecnico.filter(tipo=Lancamento.Tipo.SAIDA, categoria="Combustível").aggregate(v=Sum('valor'))['v'] or Decimal('0.00')
            saldo = entradas - (saidas + combustivel)
        else:
            ultimo_fechamento = FechamentoCaixa.objects.first()
            lancamentos = Lancamento.objects.filter(criado_em__gt=ultimo_fechamento.fechado_em) if ultimo_fechamento else Lancamento.objects.all()
            entradas = lancamentos.filter(tipo=Lancamento.Tipo.ENTRADA).aggregate(v=Sum("valor"))["v"] or Decimal('0.00')
            saidas = lancamentos.filter(tipo=Lancamento.Tipo.SAIDA).aggregate(v=Sum("valor"))["v"] or Decimal('0.00')
            combustivel = lancamentos.filter(tipo=Lancamento.Tipo.SAIDA, categoria="Combustível").aggregate(v=Sum("valor"))["v"] or Decimal('0.00')
            saldo = entradas - saidas
            aguardando = atuais.filter(status=OrdemServico.Status.AGUARDANDO_CONFIRMACAO).count()

        c.update(
            os_abertas=atuais.exclude(status__in=["CONCLUIDA", "CANCELADA"]).count(), 
            os_hoje=atuais.filter(agendamento__date=timezone.localdate()).count(), 
            entradas=entradas, 
            saidas=saidas,
            combustivel=combustivel,
            saldo=saldo,
            aguardando_confirmacao=aguardando, 
            recentes=atuais.select_related("cliente", "tecnico").order_by('-id')[:6]
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
        
        return c


class SearchableListView(LoginRequiredMixin, ListView):
    paginate_by = 12
    def get_queryset(self):
        qs = super().get_queryset(); q = self.request.GET.get("q")
        return qs.filter(nome__icontains=q) if q and self.model is Cliente else qs

class ClienteListView(OperacionalRequiredMixin, SearchableListView): model = Cliente
class ClienteCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView): model = Cliente; form_class = ClienteForm; success_url = reverse_lazy("cliente-list")
class ClienteUpdateView(LoginRequiredMixin, OperacionalRequiredMixin, UpdateView): model = Cliente; form_class = ClienteForm; success_url = reverse_lazy("cliente-list")

class ClienteFinalListView(OperacionalRequiredMixin, SearchableListView): 
    model = ClienteFinal
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("provedor")

class ClienteFinalCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView): 
    model = ClienteFinal
    form_class = ClienteFinalForm
    template_name = "core/form.html"
    success_url = reverse_lazy("clientefinal-list")
    extra_context = {"title": "Novo Cliente Final"}

class ClienteFinalUpdateView(LoginRequiredMixin, OperacionalRequiredMixin, UpdateView): 
    model = ClienteFinal
    form_class = ClienteFinalForm
    template_name = "core/form.html"
    success_url = reverse_lazy("clientefinal-list")
    extra_context = {"title": "Editar Cliente Final"}


class OrdemListView(LoginRequiredMixin, ListView):
    model = OrdemServico; paginate_by = 12
    def get_queryset(self):
        qs = OrdemServico.objects.select_related("cliente", "tecnico")
        qs = qs.filter(arquivada_em__isnull=False) if self.request.GET.get("aba") == "arquivadas" else qs.filter(arquivada_em__isnull=True)
        return qs if (self.request.user.is_staff or self.request.user.groups.filter(name="Secretaria").exists()) else qs.filter(tecnico=self.request.user)
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs); c["aba_arquivadas"] = self.request.GET.get("aba") == "arquivadas"; return c

class OrdemDetailView(LoginRequiredMixin, DetailView):
    model = OrdemServico
    def get_queryset(self):
        qs = OrdemServico.objects.select_related("cliente", "tecnico")
        return qs if (self.request.user.is_staff or self.request.user.groups.filter(name="Secretaria").exists()) else qs.filter(tecnico=self.request.user)

class OrdemCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView): model = OrdemServico; form_class = OrdemServicoForm; success_url = reverse_lazy("ordem-list")
class OrdemUpdateView(LoginRequiredMixin, OperacionalRequiredMixin, UpdateView): model = OrdemServico; form_class = OrdemServicoForm; success_url = reverse_lazy("ordem-list")

class TipoServicoListView(LoginRequiredMixin, OperacionalRequiredMixin, ListView): model = TipoServico
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
        Lancamento.objects.get_or_create(ordem_servico=os, defaults={"descricao": f"Recebimento da {os}", "tipo": Lancamento.Tipo.ENTRADA, "categoria": "Prestação de serviço", "valor": os.valor})
        messages.success(request, f"{os} confirmada e lançada no financeiro.")
        return redirect("ordem-detail", pk=os.pk)


class OrcamentoListView(LoginRequiredMixin, OperacionalRequiredMixin, ListView): model = Orcamento; paginate_by = 12
class OrcamentoCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView):
    model = Orcamento; form_class = OrcamentoForm; success_url = reverse_lazy("orcamento-list")
    def form_valid(self, form): form.instance.responsavel = self.request.user; return super().form_valid(form)
class OrcamentoUpdateView(LoginRequiredMixin, OperacionalRequiredMixin, UpdateView): model = Orcamento; form_class = OrcamentoForm; success_url = reverse_lazy("orcamento-list")

class FinanceiroView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Lancamento; template_name = "core/financeiro.html"; paginate_by = 15
    def get_queryset(self):
        ultimo = FechamentoCaixa.objects.first()
        return Lancamento.objects.filter(criado_em__gt=ultimo.fechado_em) if ultimo else Lancamento.objects.all()
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs); qs = self.get_queryset()
        c["entradas"] = qs.filter(tipo="ENTRADA").aggregate(v=Sum("valor"))["v"] or 0; c["saidas"] = qs.filter(tipo="SAIDA").aggregate(v=Sum("valor"))["v"] or 0; c["saldo"] = c["entradas"] - c["saidas"]
        return c
class LancamentoCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView): model = Lancamento; form_class = LancamentoForm; success_url = reverse_lazy("financeiro")

class CombustivelCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
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

class FecharFinanceiroView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request):
        ultimo = FechamentoCaixa.objects.first(); qs = Lancamento.objects.filter(criado_em__gt=ultimo.fechado_em) if ultimo else Lancamento.objects.all()
        entradas = qs.filter(tipo=Lancamento.Tipo.ENTRADA).aggregate(v=Sum("valor"))["v"] or 0
        saidas = qs.filter(tipo=Lancamento.Tipo.SAIDA).aggregate(v=Sum("valor"))["v"] or 0
        FechamentoCaixa.objects.create(entradas=entradas, saidas=saidas, responsavel=request.user)
        OrdemServico.objects.filter(lancamentos__in=qs, status=OrdemServico.Status.CONCLUIDA, arquivada_em__isnull=True).update(arquivada_em=timezone.now())
        messages.success(request, "Balanço fechado e OS pagas arquivadas. O novo período financeiro inicia zerado.")
        return redirect("financeiro")

class RelatorioView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "core/relatorios.html"
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs); c["status"] = [{"nome": label, "total": OrdemServico.objects.filter(status=value).count()} for value, label in OrdemServico.Status.choices]; c["tecnicos"] = OrdemServico.objects.values("tecnico__username").annotate(total=Count("id")).order_by("-total"); return c

class UsuarioListView(LoginRequiredMixin, AdminRequiredMixin, ListView): model = User; template_name = "core/usuario_list.html"; queryset = User.objects.order_by("username")
class UsuarioCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView): model = User; form_class = UsuarioForm; template_name = "core/usuario_form.html"; success_url = reverse_lazy("usuario-list")

class ProdutoListView(LoginRequiredMixin, AdminRequiredMixin, ListView): model = Produto
class ProdutoCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView): model = Produto; form_class = ProdutoForm; template_name = "core/form.html"; success_url = reverse_lazy("produto-list"); extra_context = {"title": "Novo Produto"}
class ProdutoUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView): model = Produto; form_class = ProdutoForm; template_name = "core/form.html"; success_url = reverse_lazy("produto-list"); extra_context = {"title": "Editar Produto"}

class EstoqueTecnicoListView(LoginRequiredMixin, AdminRequiredMixin, ListView): 
    model = EstoqueTecnico
    template_name = "core/estoque_tecnico_list.html"
    def get_queryset(self): return EstoqueTecnico.objects.select_related("tecnico", "produto")

class TransferenciaEstoqueView(LoginRequiredMixin, AdminRequiredMixin, View):
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
