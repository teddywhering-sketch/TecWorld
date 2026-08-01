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

from .forms import ClienteForm, ConfirmarOSForm, FinalizarOSForm, LancamentoForm, OrcamentoForm, OrdemServicoForm, UsuarioForm
from .models import Cliente, FechamentoCaixa, Lancamento, Orcamento, OrdemServico


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
        if not self.request.user.is_staff:
            c["recentes"] = OrdemServico.objects.filter(tecnico=self.request.user, arquivada_em__isnull=True).select_related("cliente")[:6]
            return c
        ultimo_fechamento = FechamentoCaixa.objects.first()
        lancamentos = Lancamento.objects.filter(criado_em__gt=ultimo_fechamento.fechado_em) if ultimo_fechamento else Lancamento.objects.all()
        entradas = lancamentos.filter(tipo=Lancamento.Tipo.ENTRADA).aggregate(v=Sum("valor"))["v"] or Decimal()
        saidas = lancamentos.filter(tipo=Lancamento.Tipo.SAIDA).aggregate(v=Sum("valor"))["v"] or Decimal()
        atuais = OrdemServico.objects.filter(arquivada_em__isnull=True)
        c.update(os_abertas=atuais.exclude(status__in=["CONCLUIDA", "CANCELADA"]).count(), os_hoje=atuais.filter(agendamento__date=timezone.localdate()).count(), entradas=entradas, saldo=entradas-saidas, aguardando_confirmacao=atuais.filter(status=OrdemServico.Status.AGUARDANDO_CONFIRMACAO).count(), recentes=atuais.select_related("cliente", "tecnico")[:6])
        return c


class SearchableListView(LoginRequiredMixin, ListView):
    paginate_by = 12
    def get_queryset(self):
        qs = super().get_queryset(); q = self.request.GET.get("q")
        return qs.filter(nome__icontains=q) if q and self.model is Cliente else qs

class ClienteListView(OperacionalRequiredMixin, SearchableListView): model = Cliente
class ClienteCreateView(LoginRequiredMixin, OperacionalRequiredMixin, CreateView): model = Cliente; form_class = ClienteForm; success_url = reverse_lazy("cliente-list")
class ClienteUpdateView(LoginRequiredMixin, OperacionalRequiredMixin, UpdateView): model = Cliente; form_class = ClienteForm; success_url = reverse_lazy("cliente-list")


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
        form.save()
        os.status = OrdemServico.Status.AGUARDANDO_CONFIRMACAO
        os.save(update_fields=["status", "atualizado_em"])
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
