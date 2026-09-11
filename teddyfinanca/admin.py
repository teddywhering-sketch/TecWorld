from django.contrib import admin
from .models import Banco, Categoria, Transacao, VendaParcelada, Emprestimo, Divida

admin.site.register(Banco)
admin.site.register(Categoria)
admin.site.register(Transacao)
admin.site.register(VendaParcelada)
admin.site.register(Emprestimo)
admin.site.register(Divida)
