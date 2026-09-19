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
    
    # Integração Pluggy
    pluggy_item_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="ID Conexão Pluggy (Item)")
    pluggy_account_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="ID Conta Pluggy (Account)")

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
    
    # Integração Pluggy
    pluggy_transaction_id = models.CharField(max_length=255, null=True, blank=True, unique=True, verbose_name="ID Transação Pluggy")

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
    telefone_cliente = models.CharField(max_length=25, blank=True, null=True, verbose_name="WhatsApp do Cliente")
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

class Venda(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    cliente = models.CharField(max_length=200)
    descricao = models.TextField(verbose_name="Descrição da Venda")
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    banco = models.ForeignKey('Banco', on_delete=models.SET_NULL, null=True, verbose_name="Receber em qual Banco?")
    data_venda = models.DateField(default=timezone.now, verbose_name="Data da Venda")
    data_vencimento = models.DateField(default=timezone.now, verbose_name="Data para Receber")
    status = models.CharField(max_length=10, choices=(('PENDENTE', 'Pendente'), ('PAGO', 'Pago')), default='PENDENTE')
    arquivado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Venda"
        verbose_name_plural = "Vendas"

    @property
    def dias_para_vencer(self):
        if self.status == 'PAGO':
            return 0
        from datetime import date
        hoje = date.today()
        diferenca = (self.data_vencimento - hoje).days
        return diferenca

    @property
    def restante(self):
        return self.valor - self.valor_pago

    def __str__(self):
        return f"Venda para {self.cliente} - R$ {self.valor}"

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
    telefone_contato = models.CharField(max_length=25, blank=True, null=True, verbose_name="WhatsApp do Contato")
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

class CompraParcelada(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    descricao = models.CharField(max_length=255, verbose_name="Nome da Compra")
    observacao = models.TextField(null=True, blank=True, verbose_name="Descrição (Opcional)")
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    entrada = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    quantidade_parcelas = models.PositiveIntegerField()
    data_compra = models.DateField(default=timezone.now)
    arquivado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Compra Parcelada"
        verbose_name_plural = "Compras Parceladas"

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

    @property
    def progresso(self):
        if self.valor_total <= 0:
            return 100
        restante = self.valor_restante
        pago = self.valor_total - restante
        return int((pago / self.valor_total) * 100)

    def __str__(self):
        return f"Compra: {self.descricao} - {self.quantidade_parcelas}x"

class Divida(models.Model):
    compra_vinculada = models.ForeignKey(CompraParcelada, on_delete=models.CASCADE, null=True, blank=True, related_name='parcelas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    STATUS_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
    )
    TIPO_RECORRENCIA_CHOICES = (
        ('UNICA', 'Única'),
        ('RECORRENTE', 'Fixa Mensal (Recorrente)'),
    )
    descricao = models.CharField(max_length=255, verbose_name="Nome da Dívida")
    observacao = models.TextField(null=True, blank=True, verbose_name="Descrição (Opcional)")
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

class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    nome_completo = models.CharField(max_length=200, blank=True, null=True)
    cpf = models.CharField(max_length=20, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

# --- Jogo da Velha (Easter Egg / Multiplayer) ---
class JogoVelha(models.Model):
    jogador1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jogos_velha_p1')
    jogador2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jogos_velha_p2')
    status = models.IntegerField(default=0) # 0=esperando, 1=jogando, 2=p1 venceu, 3=p2 venceu, 4=empate, 5=recusado
    tabuleiro = models.CharField(max_length=9, default='         ')
    turno = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jogos_velha_turnos', null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

class PresencaOnline(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ultima_atividade = models.DateTimeField(auto_now=True)
    vitorias = models.IntegerField(default=0)
    derrotas = models.IntegerField(default=0)

class ChatGlobal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mensagem = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-criado_em']

class ChatPrivado(models.Model):
    jogo = models.ForeignKey(JogoVelha, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mensagem = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-criado_em']
