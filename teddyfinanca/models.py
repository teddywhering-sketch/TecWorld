from django.db import models
from django.utils import timezone
from datetime import date
from django.contrib.auth.models import User

class Banco(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    nome = models.CharField(max_length=100, verbose_name="Nome do Banco")
    saldo_atual = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo Atual")
    limite_cheque_especial = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Limite Cheque Especial")
    limite_credito = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Limite de Crédito")

    def __str__(self):
        return f"{self.nome} (Saldo: R$ {self.saldo_atual})"

    @property
    def disponivel(self):
        return self.saldo_atual + self.limite_cheque_especial

class Categoria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    TIPO_CHOICES = (
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
        ('AMBOS', 'Ambos'),
    )
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='AMBOS')

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

class Transacao(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    TIPO_CHOICES = (
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    )
    STATUS_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
    )
    FORMA_PAGAMENTO_CHOICES = (
        ('DEBITO', 'Conta/Débito'),
        ('CREDITO', 'Cartão de Crédito'),
    )
    banco = models.ForeignKey(Banco, on_delete=models.SET_NULL, null=True, blank=True, related_name='transacoes')
    forma_pagamento = models.CharField(max_length=10, choices=FORMA_PAGAMENTO_CHOICES, default='DEBITO')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    descricao = models.CharField(max_length=255, verbose_name="Descrição")
    data = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PAGO')
    
    # Campos para vincular transações geradas automaticamente
    venda_origem = models.ForeignKey('VendaParcelada', on_delete=models.SET_NULL, null=True, blank=True)
    emprestimo_origem = models.ForeignKey('Emprestimo', on_delete=models.SET_NULL, null=True, blank=True)
    divida_origem = models.ForeignKey('Divida', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Transação"
        verbose_name_plural = "Transações"

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor}"

class VendaParcelada(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    cliente = models.CharField(max_length=200)
    descricao = models.TextField(verbose_name="Descrição da Venda")
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    entrada = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Valor de Entrada")
    quantidade_parcelas = models.PositiveIntegerField()
    data_venda = models.DateField(default=timezone.now)
    arquivado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Venda Parcelada"
        verbose_name_plural = "Vendas Parceladas"

    @property
    def todas_parcelas_pagas(self):
        return self.parcelas.exists() and not self.parcelas.filter(status='PENDENTE').exists()

    @property
    def valor_restante(self):
        from django.db.models import Sum
        pendentes = self.parcelas.filter(status='PENDENTE')
        total = pendentes.aggregate(total=Sum('valor'))['total'] or 0
        pago = pendentes.aggregate(pago=Sum('valor_pago'))['pago'] or 0
        return total - pago

    def __str__(self):
        return f"Venda para {self.cliente} - R$ {self.valor_total}"

class ParcelaVenda(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    venda = models.ForeignKey(VendaParcelada, on_delete=models.CASCADE, related_name='parcelas')
    numero = models.PositiveIntegerField()
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=(('PENDENTE', 'Pendente'), ('PAGO', 'Pago')), default='PENDENTE')

    class Meta:
        ordering = ['data_vencimento']

    @property
    def dias_para_vencer(self):
        if self.status == 'PAGO':
            return 0
        hoje = date.today()
        return (self.data_vencimento - hoje).days

    @property
    def restante(self):
        return self.valor - self.valor_pago

    def __str__(self):
        return f"Parcela {self.numero} de {self.venda.cliente}"

class Emprestimo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    STATUS_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago/Devolvido'),
    )
    nome_pessoa = models.CharField(max_length=150, verbose_name="Amigo/Familiar")
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    data_emprestimo = models.DateField(default=timezone.now)
    data_devolucao = models.DateField(verbose_name="Data de Devolução Prometida")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    observacao = models.TextField(blank=True, null=True)
    arquivado = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Empréstimos"

    @property
    def dias_para_receber(self):
        if self.status == 'PAGO':
            return 0
        hoje = date.today()
        diferenca = (self.data_devolucao - hoje).days
        return diferenca

    @property
    def restante(self):
        return self.valor - self.valor_pago

    def __str__(self):
        return f"Empréstimo: {self.nome_pessoa} - R$ {self.valor}"

class Divida(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    STATUS_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
    )
    TIPO_RECORRENCIA_CHOICES = (
        ('UNICA', 'Única'),
        ('RECORRENTE', 'Fixa Mensal (Recorrente)'),
    )
    descricao = models.CharField(max_length=255, verbose_name="Descrição da Dívida")
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    data_vencimento = models.DateField()
    tipo_recorrencia = models.CharField(max_length=15, choices=TIPO_RECORRENCIA_CHOICES, default='UNICA')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    arquivado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Dívida"
        verbose_name_plural = "Dívidas"

    @property
    def dias_para_vencer(self):
        if self.status == 'PAGO':
            return 0
        hoje = date.today()
        diferenca = (self.data_vencimento - hoje).days
        return diferenca

    @property
    def restante(self):
        return self.valor - self.valor_pago

    def __str__(self):
        return f"Dívida: {self.descricao} - R$ {self.valor}"

class Assinatura(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='assinatura_financa')
    ativa = models.BooleanField(default=False)
    data_expiracao = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"Assinatura: {self.usuario.username} - Ativa: {self.ativa}"
