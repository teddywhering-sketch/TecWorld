from decimal import Decimal
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

class TimeStampedModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Cliente(TimeStampedModel):
    nome = models.CharField("nome / razão social", max_length=150)
    documento = models.CharField("CPF/CNPJ", max_length=18, blank=True)
    telefone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    endereco = models.CharField(max_length=255)
    observacoes = models.TextField(blank=True)
    class Meta:
        ordering = ["nome"]
    def __str__(self): return self.nome

class Orcamento(TimeStampedModel):
    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"; ENVIADO = "ENVIADO", "Enviado"; APROVADO = "APROVADO", "Aprovado"; RECUSADO = "RECUSADO", "Recusado"
    numero = models.PositiveIntegerField(unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="orcamentos")
    descricao = models.TextField()
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    validade = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RASCUNHO)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    class Meta: ordering = ["-criado_em"]
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = (Orcamento.objects.order_by("-numero").first().numero + 1) if Orcamento.objects.exists() else 1
        super().save(*args, **kwargs)
    def __str__(self): return f"ORC-{self.numero:05d}"

class OrdemServico(TimeStampedModel):
    class Tipo(models.TextChoices):
        INSTALACAO = "INSTALACAO", "Instalação fibra"; MANUTENCAO = "MANUTENCAO", "Manutenção"; REDE = "REDE", "Rede / pontos"; VISITA = "VISITA", "Visita técnica"
    class Status(models.TextChoices):
        ABERTA = "ABERTA", "Aberta"; AGENDADA = "AGENDADA", "Agendada"; EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"; AGUARDANDO_CONFIRMACAO = "AGUARDANDO_CONFIRMACAO", "Aguardando confirmação"; CONCLUIDA = "CONCLUIDA", "Concluída"; CANCELADA = "CANCELADA", "Cancelada"
    numero = models.PositiveIntegerField(unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ordens")
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    cliente_instalado = models.BooleanField(default=False)
    nome_cliente_instalado = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.ABERTA)
    tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordens_tecnicas")
    agendamento = models.DateTimeField(null=True, blank=True)
    descricao = models.TextField()
    anexo_inicial = models.FileField(upload_to="ordens/anexos/%Y/%m/", blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png", "webp"])])
    comprovante_pagamento = models.FileField(upload_to="ordens/pagamentos/%Y/%m/", blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png", "webp"])])
    arquivada_em = models.DateTimeField(blank=True, null=True)
    solucao = models.TextField(blank=True)
    foto_1 = models.ImageField(upload_to="ordens/%Y/%m/", blank=True, null=True)
    foto_2 = models.ImageField(upload_to="ordens/%Y/%m/", blank=True, null=True)
    foto_3 = models.ImageField(upload_to="ordens/%Y/%m/", blank=True, null=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    class Meta: ordering = ["-criado_em"]
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = (OrdemServico.objects.order_by("-numero").first().numero + 1) if OrdemServico.objects.exists() else 1
        super().save(*args, **kwargs)
    def __str__(self): return f"OS-{self.numero:05d}"

class Lancamento(TimeStampedModel):
    class Tipo(models.TextChoices): ENTRADA = "ENTRADA", "Entrada"; SAIDA = "SAIDA", "Saída"
    data = models.DateField(default=timezone.localdate)
    descricao = models.CharField(max_length=200)
    tipo = models.CharField(max_length=7, choices=Tipo.choices)
    categoria = models.CharField(max_length=80)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.SET_NULL, null=True, blank=True, related_name="lancamentos")
    class Meta: ordering = ["-data", "-criado_em"]
    def __str__(self): return self.descricao

class FechamentoCaixa(models.Model):
    fechado_em = models.DateTimeField(auto_now_add=True)
    entradas = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    saidas = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    class Meta: ordering = ["-fechado_em"]
    @property
    def saldo(self): return self.entradas - self.saidas
