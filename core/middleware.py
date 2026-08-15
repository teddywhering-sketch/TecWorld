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
