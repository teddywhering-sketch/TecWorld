import re

with open('templates/core/ordemservico_form.html', 'r') as f:
    content = f.read()

js_code = r"""
<script>
    document.addEventListener("DOMContentLoaded", function() {
        const addItemBtn = document.getElementById("add-item-btn");
        const itemsBody = document.getElementById("items-body");
        const totalFormsInput = document.getElementById("id_itens-TOTAL_FORMS");
        const valorTotalInput = document.getElementById("id_valor");
        
        function calculateTotal() {
            let total = 0;
            const rows = itemsBody.getElementsByClassName("item-row");
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const deleteInput = row.querySelector("input[name$='-DELETE']");
                if (deleteInput && deleteInput.checked) {
                    continue;
                }
                
                const qtdInput = row.querySelector("input[name$='-quantidade']");
                const precoInput = row.querySelector("input[name$='-valor_unitario']");
                
                if (qtdInput && precoInput) {
                    const qtd = parseFloat(qtdInput.value) || 0;
                    let precoStr = precoInput.value.replace(',', '.');
                    const preco = parseFloat(precoStr) || 0;
                    total += qtd * preco;
                }
            }
            if (total > 0 || (valorTotalInput && valorTotalInput.value !== "")) {
                if (valorTotalInput) {
                    valorTotalInput.value = total.toFixed(2);
                }
            }
        }
        
        if (itemsBody) {
            itemsBody.addEventListener("input", function(e) {
                if (e.target.name && (e.target.name.includes("-quantidade") || e.target.name.includes("-valor_unitario"))) {
                    calculateTotal();
                }
            });
            
            itemsBody.addEventListener("change", function(e) {
                if (e.target.name && e.target.name.includes("-DELETE")) {
                    calculateTotal();
                }
            });
        }
        
        if(addItemBtn) {
            addItemBtn.addEventListener("click", function() {
                const formCount = parseInt(totalFormsInput.value);
                const rowTemplates = itemsBody.getElementsByClassName("item-row");
                const templateRow = rowTemplates[rowTemplates.length - 1];
                
                const newRow = templateRow.cloneNode(true);
                
                const regex = new RegExp(`itens-(\\d+)-`, 'g');
                newRow.innerHTML = newRow.innerHTML.replace(regex, `itens-${formCount}-`);
                
                const inputs = newRow.querySelectorAll("input, textarea, select");
                inputs.forEach(input => {
                    if (input.type !== "hidden" || input.name.includes("DELETE")) {
                        if (input.type === "checkbox" || input.type === "radio") {
                            input.checked = false;
                        } else {
                            if (input.name.includes("quantidade")) {
                                input.value = "1";
                            } else if (input.name.includes("valor_unitario")) {
                                input.value = "0.00";
                            } else {
                                input.value = "";
                            }
                        }
                    } else if(input.name.includes("-id")) {
                        input.value = "";
                    }
                });
                
                itemsBody.appendChild(newRow);
                totalFormsInput.value = formCount + 1;
            });
        }

        const tiposPrecos = {{ tipos_precos_json|safe|default:"{}" }};
        const tipoSelect = document.getElementById('id_tipo');
        
        if (tipoSelect && valorTotalInput) {
            tipoSelect.addEventListener('change', function() {
                const selectedId = this.value;
                if (selectedId && tiposPrecos[selectedId]) {
                    const firstDesc = document.getElementById('id_itens-0-descricao');
                    const firstValor = document.getElementById('id_itens-0-valor_unitario');
                    
                    if(firstDesc && firstDesc.value === "") {
                        firstDesc.value = tipoSelect.options[tipoSelect.selectedIndex].text;
                        if(firstValor) {
                            firstValor.value = parseFloat(tiposPrecos[selectedId]).toFixed(2);
                        }
                    } else {
                        // Se não tem item vazio, pode só atualizar o valor total base se tiver zerado os itens
                    }
                    calculateTotal();
                }
            });
        }
    });
</script>
"""

content = re.sub(r'<script>.*?</script>', js_code, content, flags=re.DOTALL)

with open('templates/core/ordemservico_form.html', 'w') as f:
    f.write(content)

print("Done")
