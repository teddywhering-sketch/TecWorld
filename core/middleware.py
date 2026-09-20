import threading

_local = threading.local()

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.user = getattr(request, 'user', None)
        response = self.get_response(request)
        _local.user = None
        return response

def get_current_user():
    return getattr(_local, 'user', None)

from django.http import HttpResponseForbidden

class BlockFinancaClientsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            if not path.startswith('/financeiro/') and not path.startswith('/admin') and not path.startswith('/portal-secreto') and not path.startswith('/static/') and not path.startswith('/media/'):
                if path != '/logout/':
                    user = request.user
                    # A user is purely Finança if they have a 'perfil' but are not staff/groups/cliente_provedor
                    is_pure_financa = False
                    if not (user.is_staff or user.is_superuser or user.groups.exists()):
                        has_provedor = False
                        try:
                            has_provedor = bool(user.cliente_provedor)
                        except Exception:
                            pass
                        
                        if not has_provedor:
                            try:
                                if user.perfil:
                                    is_pure_financa = True
                            except Exception:
                                pass
                                
                    if is_pure_financa:
                        return HttpResponseForbidden("<h1>Acesso Negado</h1><p>Sua conta pertence ao sistema Financeiro e não possui permissão para acessar o painel TecWorld.</p><p><a href='/financeiro/'>Acessar meu Financeiro</a> | <a href='/logout/'>Sair</a></p>")
                        
        return self.get_response(request)
