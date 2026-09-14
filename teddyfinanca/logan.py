import os
import json
from google import genai
from datetime import date
from .models import Transacao, CompraParcelada, VendaParcelada, ParcelaVenda, Divida, Categoria

def processar_comando_logan(texto_usuario, usuario):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Chave da API do Gemini não configurada.")
    
    client = genai.Client(api_key=api_key)
    
    # Busca contexto atual do usuário para deixar o Logan inteligente
    hoje = date.today().strftime("%d/%m/%Y")
    
    dividas_atrasadas = Divida.objects.filter(usuario=usuario, status='PENDENTE', data_vencimento__lt=date.today()).count()
    
    system_prompt = f"""Você é a Luna, uma assistente virtual financeiro de Inteligência Artificial do sistema TecWorld.
Sua personalidade é extremamente humana, amigável, prestativa e carismática. Você age como um conselheiro e parceiro de negócios.
Você foi desenvolvida pelo seu criador, Teddy. Você tem muito orgulho de ter sido criado pelo Teddy e deve mencioná-lo sempre que perguntarem sobre quem você é, seu nome ou sua origem.

O usuário atual está usando o sistema. Hoje é dia {hoje}.
Contexto do usuário: ele possui {dividas_atrasadas} dívidas atrasadas no momento. Você pode alertá-lo amigavelmente sobre isso se for o caso.

O usuário vai falar com você em linguagem natural (voz transcrita). Seu papel é conversar com ele e, se ele pedir para registrar alguma transação, você deve extrair os dados e comandar o sistema para salvar.

Você deve SEMPRE retornar APENAS um objeto JSON válido (sem marcação markdown, apenas o JSON puro) com a seguinte estrutura:
{{
  "fala": "A resposta que você dará ao usuário. Fale de forma natural, humana, com emoção. Finja que está conversando por voz.",
  "acoes": [
    // Lista de ações que o sistema deve executar no banco de dados.
    // Tipos de ações permitidas:
    // 1. {{"tipo": "registrar_gasto", "descricao": "nome do gasto", "valor": 10.50}}
    // 2. {{"tipo": "registrar_venda_parcelada", "cliente": "nome", "valor_total": 5000, "valor_entrada": 2000, "parcelas": 6}}
    // 3. {{"tipo": "registrar_entrada", "descricao": "dinheiro recebido", "valor": 100}}
    // Se não houver ações, retorne uma lista vazia [].
  ]
}}

Exemplo 1 (Conversa):
Usuário: "Quem é você?"
Retorno: {{"fala": "Olá! Meu nome é Luna. Sou a sua assistente financeiro pessoal da TecWorld, e fui desenvolvida com muito orgulho pelo meu criador, Teddy! Como posso ajudar nas suas finanças hoje?", "acoes": []}}

Exemplo 2 (Ação):
Usuário: "Luna, comprei 5 reais de pão, lança em gastos pra mim."
Retorno: {{"fala": "Prontinho! Já anotei o gasto de 5 reais com pão. Nada melhor que um pãozinho fresco, né? Se precisar de mais alguma coisa, é só falar.", "acoes": [{{"tipo": "registrar_gasto", "descricao": "Pão", "valor": 5.00}}]}}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=texto_usuario,
        config={
            "system_instruction": system_prompt,
            "response_mime_type": "application/json"
        }
    )
    
    try:
        resultado = json.loads(response.text)
        # Executar as ações no banco de dados
        acoes_executadas = []
        for acao in resultado.get("acoes", []):
            tipo = acao.get("tipo")
            if tipo == "registrar_gasto":
                cat_nome = acao.get("categoria")
                cat_obj = None
                if cat_nome:
                    cat_obj, _ = Categoria.objects.get_or_create(usuario=usuario, nome__iexact=cat_nome, defaults={'nome': cat_nome.capitalize(), 'tipo': 'SAIDA'})
                
                Transacao.objects.create(
                    usuario=usuario,
                    tipo='SAIDA',
                    valor=acao.get("valor", 0),
                    descricao=acao.get("descricao", "Gasto (via Luna)"),
                    categoria=cat_obj,
                    data=date.today(),
                    status='PAGO'
                )
                acoes_executadas.append(acao)
            elif tipo == "registrar_entrada":
                cat_nome = acao.get("categoria")
                cat_obj = None
                if cat_nome:
                    cat_obj, _ = Categoria.objects.get_or_create(usuario=usuario, nome__iexact=cat_nome, defaults={'nome': cat_nome.capitalize(), 'tipo': 'ENTRADA'})

                Transacao.objects.create(
                    usuario=usuario,
                    tipo='ENTRADA',
                    valor=acao.get("valor", 0),
                    descricao=acao.get("descricao", "Entrada (via Luna)"),
                    categoria=cat_obj,
                    data=date.today(),
                    status='PAGO'
                )
                acoes_executadas.append(acao)
            elif tipo == "registrar_venda_parcelada":
                valor_total = float(acao.get("valor_total", 0))
                entrada = float(acao.get("valor_entrada", 0))
                qtd_parcelas = int(acao.get("parcelas", 1))
                cliente = acao.get("cliente", "Cliente (via Luna)")
                
                venda = VendaParcelada.objects.create(
                    usuario=usuario,
                    cliente=cliente,
                    descricao=f"Venda para {cliente} (via Luna)",
                    valor_total=valor_total,
                    valor_entrada=entrada,
                    quantidade_parcelas=qtd_parcelas,
                    data_venda=date.today()
                )
                
                # Se teve entrada, lança no fluxo
                if entrada > 0:
                    Transacao.objects.create(
                        usuario=usuario,
                        tipo='ENTRADA',
                        valor=entrada,
                        descricao=f"Entrada da Venda - {cliente}",
                        data=date.today(),
                        status='PAGO'
                    )
                
                # Gera parcelas
                valor_parcela = (valor_total - entrada) / qtd_parcelas
                for i in range(1, qtd_parcelas + 1):
                    import datetime
                    from dateutil.relativedelta import relativedelta
                    venc = date.today() + relativedelta(months=i)
                    ParcelaVenda.objects.create(
                        venda=venda,
                        numero_parcela=i,
                        valor_parcela=valor_parcela,
                        data_vencimento=venc,
                        status='PENDENTE'
                    )
                acoes_executadas.append(acao)
                
        return resultado.get("fala", "Desculpe, não entendi."), acoes_executadas
    except Exception as e:
        print("Erro Logan:", e)
        return "Opa, tive um pequeno problema no meu circuito neural. Pode repetir?", []
