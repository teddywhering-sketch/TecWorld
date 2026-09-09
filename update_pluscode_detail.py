import re

with open('templates/core/ordemservico_detail.html', 'r') as f:
    content = f.read()

old_html = '<p><b>Status</b><br><span class="badge {% if object.status == \'CONCLUIDA\' %}text-bg-success{% else %}text-bg-primary{% endif %}">{{ object.get_status_display }}</span></p>'

new_html = old_html + '''
            
            {% if object.plus_code %}
            <p><b>Localização</b><br>
                <a href="https://www.google.com/maps/search/?api=1&query={{ object.plus_code|urlencode }}" target="_blank" class="btn btn-sm btn-outline-primary mt-1">
                    <i class="bi bi-geo-alt"></i> Abrir no Mapa
                </a>
            </p>
            {% endif %}'''

content = content.replace(old_html, new_html)

with open('templates/core/ordemservico_detail.html', 'w') as f:
    f.write(content)

print("Done")
