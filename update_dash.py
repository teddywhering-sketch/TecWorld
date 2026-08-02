import re

with open('templates/core/dashboard.html', 'r') as f:
    content = f.read()

content = content.replace('col-md-6 col-xl"', 'col-md-4 col-xl-3"')
content = content.replace("col-md-6 col-xl\n", "col-md-4 col-xl-3\n")
content = content.replace("col-md-6 col-xl>", "col-md-4 col-xl-3>")

card_html = """
    <div class="col-md-4 col-xl-3">
        <div class="card p-3 border-0 shadow-sm h-100 bg-primary bg-opacity-10" style="border-radius: 16px;">
            <div class="d-flex align-items-center">
                <div class="text-primary bg-white bg-opacity-75 rounded-circle d-flex align-items-center justify-content-center" style="width: 45px; height: 45px; flex-shrink: 0;">
                    <i class="bi bi-wallet2 fs-5"></i>
                </div>
                <div class="ms-2">
                    <small class="text-primary fw-semibold" style="font-size: 0.8rem;">{% if is_operacional %}Saldo Total{% else %}Seu Saldo{% endif %}</small>
                    <h4 class="mt-1 mb-0 fw-bold text-primary">R$ {{ saldo|floatformat:2 }}</h4>
                </div>
            </div>
        </div>
    </div>
"""

# Insert before <div class="row g-4 mb-4">
content = content.replace('<div class="row g-4 mb-4">', card_html + '</div>\n\n<div class="row g-4 mb-4">')
# Fix the extra closing div
content = content.replace('</div>\n\n    ' + card_html, card_html)

# Let's be safer:
with open('templates/core/dashboard.html', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    lines[i] = line.replace('col-md-6 col-xl"', 'col-md-4 col-xl-3"').replace('col-md-6 col-xl>', 'col-md-4 col-xl-3>').replace('col-md-6 col-xl\n', 'col-md-4 col-xl-3\n')
    if 'class="row g-4 mb-4"' in line:
        # Insert before the closing div of the previous row? No, just insert the card before the previous row's closing </div>
        pass

with open('templates/core/dashboard.html', 'w') as f:
    f.writelines(lines)

