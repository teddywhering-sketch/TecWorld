from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views
urlpatterns = [
 path("", views.DashboardView.as_view(), name="dashboard"), path("login/", views.UserLoginView.as_view(), name="login"), path("logout/", LogoutView.as_view(), name="logout"),
 path("clientes/", views.ClienteListView.as_view(), name="cliente-list"), path("clientes/novo/", views.ClienteCreateView.as_view(), name="cliente-create"), path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente-update"),
 path("clientes-finais/", views.ClienteFinalListView.as_view(), name="clientefinal-list"), path("clientes-finais/novo/", views.ClienteFinalCreateView.as_view(), name="clientefinal-create"), path("clientes-finais/<int:pk>/editar/", views.ClienteFinalUpdateView.as_view(), name="clientefinal-update"),
 path("ordens/", views.OrdemListView.as_view(), name="ordem-list"), path("ordens/nova/", views.OrdemCreateView.as_view(), name="ordem-create"), path("ordens/<int:pk>/", views.OrdemDetailView.as_view(), name="ordem-detail"), path("ordens/<int:pk>/editar/", views.OrdemUpdateView.as_view(), name="ordem-update"), path("ordens/<int:pk>/iniciar/", views.IniciarOSView.as_view(), name="ordem-iniciar"), path("ordens/<int:pk>/finalizar/", views.FinalizarOSView.as_view(), name="ordem-finalizar"), path("ordens/<int:pk>/confirmar/", views.ConfirmarOSView.as_view(), name="ordem-confirmar"),
 path("ordens/tipos/", views.TipoServicoListView.as_view(), name="tipo-servico-list"), path("ordens/tipos/novo/", views.TipoServicoCreateView.as_view(), name="tipo-servico-create"), path("ordens/tipos/<int:pk>/editar/", views.TipoServicoUpdateView.as_view(), name="tipo-servico-update"),
 path("orcamentos/", views.OrcamentoListView.as_view(), name="orcamento-list"), path("orcamentos/novo/", views.OrcamentoCreateView.as_view(), name="orcamento-create"), path("orcamentos/<int:pk>/editar/", views.OrcamentoUpdateView.as_view(), name="orcamento-update"),
 path("financeiro/", views.FinanceiroView.as_view(), name="financeiro"), path("financeiro/novo/", views.LancamentoCreateView.as_view(), name="lancamento-create"), path("financeiro/combustivel/", views.CombustivelCreateView.as_view(), name="lancar-combustivel"), path("relatorios/", views.RelatorioView.as_view(), name="relatorios"),
 path("financeiro/fechar/", views.FecharFinanceiroView.as_view(), name="financeiro-fechar"),
 
 path("produtos/", views.ProdutoListView.as_view(), name="produto-list"),
 path("produtos/novo/", views.ProdutoCreateView.as_view(), name="produto-create"),
 path("produtos/<int:pk>/editar/", views.ProdutoUpdateView.as_view(), name="produto-update"),
 path("estoque/", views.EstoqueTecnicoListView.as_view(), name="estoque-tecnico-list"),
 path("estoque/transferir/", views.TransferenciaEstoqueView.as_view(), name="estoque-transferir"),
 path("ordens/<int:pk>/baixa-material/", views.BaixaMaterialOSView.as_view(), name="ordem-baixa-material"),

 path("usuarios/", views.UsuarioListView.as_view(), name="usuario-list"), path("usuarios/novo/", views.UsuarioCreateView.as_view(), name="usuario-create"),
 path("senha/", views.MinhaSenhaView.as_view(), name="minha-senha"), path("usuarios/<int:pk>/senha/", views.UsuarioSenhaView.as_view(), name="usuario-senha"),
 path("configuracoes/", views.ConfiguracaoSistemaUpdateView.as_view(), name="configuracao-sistema"),
]
