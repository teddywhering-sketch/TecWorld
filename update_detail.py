import re

with open('templates/core/ordemservico_detail.html', 'r') as f:
    content = f.read()

items_html = """
            {% if object.itens.all %}
            <h6 class="mt-4 border-bottom pb-2">Itens da Ordem de Serviço</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Descrição</th>
                            <th>Qtd</th>
                            <th>Valor Unit.</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in object.itens.all %}
                        <tr>
                            <td>{{ item.descricao }}</td>
                            <td>{{ item.quantidade }}</td>
                            <td>R$ {{ item.valor_unitario|floatformat:2 }}</td>
                            <td>R$ {{ item.total|floatformat:2 }}</td>
                        </tr>
                        {% endfor %}
                        <tr class="fw-bold bg-light">
                            <td colspan="3" class="text-end">Valor Total:</td>
                            <td>R$ {{ object.valor|floatformat:2 }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            {% endif %}
            
            <h6 class="mt-4 border-bottom pb-2">Descrição</h6>
"""

content = content.replace('<h6 class="mt-4 border-bottom pb-2">Descrição</h6>', items_html)

with open('templates/core/ordemservico_detail.html', 'w') as f:
    f.write(content)

print("Done")
