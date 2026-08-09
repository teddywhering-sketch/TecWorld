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

class TipoServico(models.Model):
    nome = models.CharField("Nome", max_length=100, unique=True)
    ativo = models.BooleanField("Ativo", default=True)
    valor_padrao = models.DecimalField("Valor Padrão", max_digits=10, decimal_places=2, default=0.00)
    
    class Meta:
        ordering = ["nome"]
        verbose_name = "Tipo de Serviço"
        verbose_name_plural = "Tipos de Serviço"
        
    def __str__(self): return self.nome

class Orcamento(TimeStampedModel):
    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"; ENVIADO = "ENVIADO", "Enviado"; APROVADO = "APROVADO", "Aprovado"; RECUSADO = "RECUSADO", "Recusado"
    numero = models.PositiveIntegerField(unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="orcamentos")
    descricao = models.TextField()
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    desconto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    validade = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RASCUNHO)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    class Meta: ordering = ["-criado_em"]
    
    @property
    def valor_total(self):
        # Se tem itens, usa a soma dos itens como base. Se não, usa o campo valor.
        subtotal = sum(item.total for item in self.itens.all()) if self.itens.exists() else self.valor
        # Import Decimal
        from decimal import Decimal
        return max(Decimal('0.00'), subtotal - self.desconto)

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = (Orcamento.objects.order_by("-numero").first().numero + 1) if Orcamento.objects.exists() else 1
        super().save(*args, **kwargs)
    def __str__(self): return f"ORC-{self.numero:05d}"

class OrcamentoItem(models.Model):
    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name="itens")
    descricao = models.CharField(max_length=255)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    
    @property
    def total(self):
        return self.quantidade * self.preco_unitario

class ClienteFinal(TimeStampedModel):
    provedor = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="clientes_finais")
    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    class Meta: ordering = ["nome"]
    def __str__(self): return f"{self.nome} ({self.provedor.nome})"

class OrdemServico(TimeStampedModel):
    class Status(models.TextChoices):
        ABERTA = "ABERTA", "Aberta"; AGENDADA = "AGENDADA", "Agendada"; EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"; AGUARDANDO_CONFIRMACAO = "AGUARDANDO_CONFIRMACAO", "Aguardando confirmação"; CONCLUIDA = "CONCLUIDA", "Concluída"; CANCELADA = "CANCELADA", "Cancelada"
    numero = models.PositiveIntegerField(unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ordens")
    cliente_final = models.ForeignKey(ClienteFinal, on_delete=models.SET_NULL, blank=True, null=True)
    tipo = models.ForeignKey(TipoServico, on_delete=models.PROTECT, verbose_name="Tipo de Serviço")
    cliente_instalado = models.BooleanField(default=False)
    nome_cliente_instalado = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.ABERTA)
    tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordens_tecnicas")
    agendamento = models.DateTimeField(null=True, blank=True)
    iniciado_em = models.DateTimeField(null=True, blank=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)
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
    
    @property
    def tempo_gasto(self):
        if self.iniciado_em and self.finalizado_em:
            diff = self.finalizado_em - self.iniciado_em
            total_seconds = int(diff.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0: return f"{hours}h {minutes}m"
            return f"{minutes} min"
        return ""

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
    tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="lancamentos")
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

class Produto(TimeStampedModel):
    nome = models.CharField(max_length=150, unique=True)
    unidade = models.CharField("Unidade de medida", max_length=20, default="UN")
    estoque_base = models.IntegerField("Estoque na Sede", default=0)
    class Meta: ordering = ["nome"]
    def __str__(self): return f"{self.nome} ({self.unidade})"

class EstoqueTecnico(TimeStampedModel):
    tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="estoque")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.IntegerField(default=0)
    class Meta: 
        unique_together = ("tecnico", "produto")
        ordering = ["tecnico__username", "produto__nome"]
    def __str__(self): return f"{self.quantidade}x {self.produto.nome} com {self.tecnico.username}"

class ProdutoOS(models.Model):
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="materiais_utilizados")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.IntegerField()
    registrado_em = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["registrado_em"]
    def __str__(self): return f"{self.quantidade}x {self.produto.nome}"

class ConfiguracaoSistema(models.Model):
    logo = models.ImageField("Logo do Sistema", upload_to="logos/", null=True, blank=True)
    class Meta:
        verbose_name = "Configuração do Sistema"
        verbose_name_plural = "Configurações do Sistema"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
