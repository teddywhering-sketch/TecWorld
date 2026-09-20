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
                    if user.groups.filter(name="Finança").exists():
                        return HttpResponseForbidden("<h1>Acesso Negado</h1><p>Sua conta pertence ao sistema Financeiro e não possui permissão para acessar o painel TecWorld.</p><p><a href='/financeiro/'>Acessar meu Financeiro</a> | <a href='/logout/'>Sair</a></p>")
                        
        return self.get_response(request)

import traceback
import datetime
from django.conf import settings


import traceback
import datetime
from django.conf import settings

class ErrorLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            if hasattr(response, 'render') and callable(response.render):
                try:
                    response.render()
                except Exception as e:
                    self.log_error(request, e)
                    raise
            return response
        except Exception as e:
            self.log_error(request, e)
            raise

    def log_error(self, request, exception):
        try:
            with open('/tmp/error_log.txt', 'a') as f:
                f.write(f"
[{datetime.datetime.now()}] {request.method} {request.path}
")
                f.write("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
        except:
            pass

    def process_exception(self, request, exception):
        self.log_error(request, exception)
        return None
