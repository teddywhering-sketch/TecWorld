from django.contrib import admin
from .models import Cliente, FechamentoCaixa, Lancamento, Orcamento, OrdemServico
admin.site.register([Cliente, Orcamento, OrdemServico, Lancamento, FechamentoCaixa])
