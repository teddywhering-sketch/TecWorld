from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from .models import PresencaOnline, JogoVelha, ChatGlobal, ChatPrivado

@login_required
def ping_presenca(request):
    user = request.user
    # Update presence
    pres, created = PresencaOnline.objects.get_or_create(user=user)
    pres.ultima_atividade = timezone.now()
    pres.save()
    
    # Get active online users (active in last 30 seconds)
    cutoff = timezone.now() - timedelta(seconds=30)
    online_users = PresencaOnline.objects.filter(ultima_atividade__gte=cutoff).exclude(user=user)
    
    users_data = [{'id': p.user.id, 'nome': p.user.get_full_name() or p.user.username} for p in online_users]
    
    # Get pending invites for this user
    convites_raw = JogoVelha.objects.filter(jogador2=user, status=0).order_by('-id')
    seen = set()
    convites_data = []
    for c in convites_raw:
        if c.jogador1_id not in seen:
            seen.add(c.jogador1_id)
            convites_data.append({'id': c.id, 'nome': c.jogador1.get_full_name() or c.jogador1.username})
    
    # Get active games for this user (where status__in=[1, 2, 3, 4])
    jogo_ativo = JogoVelha.objects.filter(
        status__in=[1, 2, 3, 4]
    ).filter(jogador1=user).union(
        JogoVelha.objects.filter(status__in=[1, 2, 3, 4]).filter(jogador2=user)
    ).first()
    
    jogo_data = None
    if jogo_ativo:
        adversario = jogo_ativo.jogador2 if jogo_ativo.jogador1 == user else jogo_ativo.jogador1
        jogo_data = {
            'id': jogo_ativo.id,
            'adversario': adversario.get_full_name() or adversario.username,
            'adversario_id': adversario.id,
            'tabuleiro': jogo_ativo.tabuleiro,
            'meu_turno': jogo_ativo.turno == user,
            'minha_peca': 'X' if jogo_ativo.jogador1 == user else 'O',
            'status': jogo_ativo.status,
            'p1': jogo_ativo.jogador1 == user
        }
        
        chat_privado = ChatPrivado.objects.filter(jogo=jogo_ativo)[:20]
        chat_privado_data = [{'user': c.user.get_full_name() or c.user.username, 'msg': c.mensagem, 'me': c.user == user} for c in chat_privado][::-1]
    else:
        chat_privado_data = []

    chat_global = ChatGlobal.objects.all()[:20]
    chat_global_data = [{'user': c.user.get_full_name() or c.user.username, 'msg': c.mensagem, 'me': c.user == user} for c in chat_global][::-1]

    # Get global ranking
    ranking_raw = PresencaOnline.objects.filter(vitorias__gt=0).order_by('-vitorias')[:3]
    ranking_data = [{'nome': r.user.get_full_name() or r.user.username, 'v': r.vitorias} for r in ranking_raw]

    return JsonResponse({
        'online': users_data,
        'convites': convites_data,
        'jogo_ativo': jogo_data,
        'my_score': {'v': pres.vitorias, 'd': pres.derrotas},
        'chat_global': chat_global_data,
        'chat_privado': chat_privado_data,
        'ranking': ranking_data
    })

@login_required
def convidar_jogador(request, adversario_id):
    adversario = User.objects.get(id=adversario_id)
    # create new game or return existing
    jogo = JogoVelha.objects.filter(jogador1=request.user, jogador2=adversario, status=0).first()
    if not jogo:
        jogo = JogoVelha.objects.create(
            jogador1=request.user,
            jogador2=adversario,
            status=0 # waiting
        )
    # Get global ranking
    ranking_raw = PresencaOnline.objects.filter(vitorias__gt=0).order_by('-vitorias')[:3]
    ranking_data = [{'nome': r.user.get_full_name() or r.user.username, 'v': r.vitorias} for r in ranking_raw]

    return JsonResponse({'status': 'ok', 'jogo_id': jogo.id})

@login_required
def aceitar_convite(request, jogo_id):
    jogo = JogoVelha.objects.get(id=jogo_id, jogador2=request.user)
    jogo.status = 1 # playing
    jogo.turno = jogo.jogador1 # p1 starts
    jogo.save()
    # Get global ranking
    ranking_raw = PresencaOnline.objects.filter(vitorias__gt=0).order_by('-vitorias')[:3]
    ranking_data = [{'nome': r.user.get_full_name() or r.user.username, 'v': r.vitorias} for r in ranking_raw]

    return JsonResponse({'status': 'ok'})

@login_required
def recusar_convite(request, jogo_id):
    try:
        jogo = JogoVelha.objects.get(id=jogo_id)
        if request.user in [jogo.jogador1, jogo.jogador2]:
            jogo.status = 5 # refused
            jogo.save()
    except JogoVelha.DoesNotExist:
        pass
    return JsonResponse({'status': 'ok'})

def check_vencedor(tabuleiro):
    win_conditions = [
        [0,1,2], [3,4,5], [6,7,8], # horizontal
        [0,3,6], [1,4,7], [2,5,8], # vertical
        [0,4,8], [2,4,6]           # diagonal
    ]
    for c in win_conditions:
        if tabuleiro[c[0]] != ' ' and tabuleiro[c[0]] == tabuleiro[c[1]] == tabuleiro[c[2]]:
            return tabuleiro[c[0]]
    if ' ' not in tabuleiro:
        return 'D' # draw
    return None

@login_required
def jogar_turno(request, jogo_id):
    pos = int(request.POST.get('pos'))
    jogo = JogoVelha.objects.get(id=jogo_id)
    if jogo.status != 1 or jogo.turno != request.user:
        return JsonResponse({'status': 'error'})
        
    tab_list = list(jogo.tabuleiro)
    if tab_list[pos] != ' ':
        return JsonResponse({'status': 'error'})
        
    peca = 'X' if jogo.jogador1 == request.user else 'O'
    tab_list[pos] = peca
    jogo.tabuleiro = "".join(tab_list)
    
    vencedor = check_vencedor(jogo.tabuleiro)
    
    if vencedor in ['X', 'O']:
        p1_pres, _ = PresencaOnline.objects.get_or_create(user=jogo.jogador1)
        p2_pres, _ = PresencaOnline.objects.get_or_create(user=jogo.jogador2)
        
    if vencedor == 'X':
        jogo.status = 2
        p1_pres.vitorias += 1; p1_pres.save()
        p2_pres.derrotas += 1; p2_pres.save()
    elif vencedor == 'O':
        jogo.status = 3
        p2_pres.vitorias += 1; p2_pres.save()
        p1_pres.derrotas += 1; p1_pres.save()
    elif vencedor == 'D':
        jogo.status = 4
    else:
        jogo.turno = jogo.jogador2 if jogo.jogador1 == request.user else jogo.jogador1
        
    jogo.save()
    # Get global ranking
    ranking_raw = PresencaOnline.objects.filter(vitorias__gt=0).order_by('-vitorias')[:3]
    ranking_data = [{'nome': r.user.get_full_name() or r.user.username, 'v': r.vitorias} for r in ranking_raw]

    return JsonResponse({'status': 'ok'})

@login_required
def status_jogo(request, jogo_id):
    jogo = JogoVelha.objects.get(id=jogo_id)
    # Get global ranking
    ranking_raw = PresencaOnline.objects.filter(vitorias__gt=0).order_by('-vitorias')[:3]
    ranking_data = [{'nome': r.user.get_full_name() or r.user.username, 'v': r.vitorias} for r in ranking_raw]

    return JsonResponse({
        'status_id': jogo.status,
        'tabuleiro': jogo.tabuleiro,
        'meu_turno': jogo.turno == request.user,
        'adversario_recusou': jogo.status == 5
    })

@login_required
def enviar_chat_global(request):
    msg = request.POST.get('msg', '').strip()
    if msg:
        ChatGlobal.objects.create(user=request.user, mensagem=msg)
    # Get global ranking
    ranking_raw = PresencaOnline.objects.filter(vitorias__gt=0).order_by('-vitorias')[:3]
    ranking_data = [{'nome': r.user.get_full_name() or r.user.username, 'v': r.vitorias} for r in ranking_raw]

    return JsonResponse({'status': 'ok'})

@login_required
def enviar_chat_privado(request, jogo_id):
    msg = request.POST.get('msg', '').strip()
    if msg:
        jogo = JogoVelha.objects.get(id=jogo_id)
        if request.user in [jogo.jogador1, jogo.jogador2]:
            ChatPrivado.objects.create(jogo=jogo, user=request.user, mensagem=msg)
    # Get global ranking
    ranking_raw = PresencaOnline.objects.filter(vitorias__gt=0).order_by('-vitorias')[:3]
    ranking_data = [{'nome': r.user.get_full_name() or r.user.username, 'v': r.vitorias} for r in ranking_raw]

    return JsonResponse({'status': 'ok'})

@login_required
def reiniciar_jogo(request, jogo_id):
    jogo = JogoVelha.objects.get(id=jogo_id)
    if jogo.status in [2, 3, 4] and request.user in [jogo.jogador1, jogo.jogador2]:
        jogo.tabuleiro = '         '
        jogo.status = 1
        # Troca os jogadores para alternar quem começa (quem é X)
        jogo.jogador1, jogo.jogador2 = jogo.jogador2, jogo.jogador1
        jogo.save()
    return JsonResponse({'status': 'ok'})
