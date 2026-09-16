from django.urls import path
from . import views
from . import game_views


app_name = 'teddyfinanca'

urlpatterns = [
    path('login/', views.financeiro_login, name='login'),
    path('debug/', views.debug_git),
    path('cadastro/', views.financeiro_cadastro, name='cadastro'),
    path('logout/', views.financeiro_logout, name='logout'),
    path('bloqueado/', views.bloqueado, name='bloqueado'),
    path('painel/', views.dashboard, name='dashboard'),
    path('divida/<int:id>/pagar/', views.pagar_divida, name='pagar_divida'),
    path('divida/<int:id>/deletar/', views.deletar_divida, name='deletar_divida'),
    path('emprestimo/<int:id>/receber/', views.receber_emprestimo, name='receber_emprestimo'),
    path('emprestimo/<int:id>/deletar/', views.deletar_emprestimo, name='deletar_emprestimo'),
    path('parcela/<int:id>/receber/', views.receber_parcela, name='receber_parcela'),
    path('perfil/salvar/', views.salvar_perfil, name='salvar_perfil'),
    path('recibo/venda/<int:id>/', views.recibo_venda, name='recibo_venda'),
    path('recibo/emprestimo/<int:id>/', views.recibo_emprestimo, name='recibo_emprestimo'),
    path('venda/<int:id>/deletar/', views.deletar_venda, name='deletar_venda'),
    path('venda/<int:id>/arquivar/', views.arquivar_venda, name='arquivar_venda'),
    path('categoria/<int:id>/deletar/', views.deletar_categoria, name='deletar_categoria'),
    path('emprestimo/<int:id>/arquivar/', views.arquivar_emprestimo, name='arquivar_emprestimo'),
    path('divida/<int:id>/arquivar/', views.arquivar_divida, name='arquivar_divida'),
    path('manifest.json', views.manifest_json, name='manifest'),
    path('sw.js', views.sw_js, name='sw'),
    path('banco/<int:id>/deletar/', views.deletar_banco, name='deletar_banco'),
    path('banco/<int:id>/editar/', views.editar_banco, name='editar_banco'),
    path('compra/<int:id>/deletar/', views.deletar_compra, name='deletar_compra'),
    path('compra/<int:id>/arquivar/', views.arquivar_compra, name='arquivar_compra'),
    path('api/connect-token/', views.get_connect_token, name='get_connect_token'),
    path('api/webhooks/pluggy/', views.pluggy_webhook, name='pluggy_webhook'),
    path('api/webhooks/pluggy', views.pluggy_webhook, name='pluggy_webhook_no_slash'),
    path('api/logan/', views.api_logan, name='api_logan'),
    path('api/banco/vincular/', views.vincular_banco_pluggy, name='vincular_banco_pluggy'),
    path('limpar-pluggy/', views.limpar_pluggy_vps, name='limpar_pluggy_vps'),

    path('game/ping/', game_views.ping_presenca, name='game_ping'),
    path('game/convidar/<int:adversario_id>/', game_views.convidar_jogador, name='game_convidar'),
    path('game/aceitar/<int:jogo_id>/', game_views.aceitar_convite, name='game_aceitar'),
    path('game/recusar/<int:jogo_id>/', game_views.recusar_convite, name='game_recusar'),
    path('game/jogar/<int:jogo_id>/', game_views.jogar_turno, name='game_jogar'),
    path('game/status/<int:jogo_id>/', game_views.status_jogo, name='game_status'),
    path('game/chat_global/', game_views.enviar_chat_global, name='game_chat_global'),
    path('game/chat_privado/<int:jogo_id>/', game_views.enviar_chat_privado, name='game_chat_privado'),
]

