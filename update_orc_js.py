import re

with open('templates/core/orcamento_form.html', 'r') as f:
    content = f.read()

# Add JS logic to sum totals
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
                // Check if row is not marked for deletion
                const deleteInput = row.querySelector("input[name$='-DELETE']");
                if (deleteInput && deleteInput.checked) {
                    continue;
                }
                
                const qtdInput = row.querySelector("input[name$='-quantidade']");
                const precoInput = row.querySelector("input[name$='-preco_unitario']");
                
                if (qtdInput && precoInput) {
                    const qtd = parseFloat(qtdInput.value) || 0;
                    // Replace comma with dot if user typed comma
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
        
        // Listen to changes on inputs
        itemsBody.addEventListener("input", function(e) {
            if (e.target.name && (e.target.name.includes("-quantidade") || e.target.name.includes("-preco_unitario"))) {
                calculateTotal();
            }
        });
        
        itemsBody.addEventListener("change", function(e) {
            if (e.target.name && e.target.name.includes("-DELETE")) {
                calculateTotal();
            }
        });

        addItemBtn.addEventListener("click", function() {
            const formCount = parseInt(totalFormsInput.value);
            const rowTemplates = itemsBody.getElementsByClassName("item-row");
            const templateRow = rowTemplates[rowTemplates.length - 1]; // Clone the last row
            
            const newRow = templateRow.cloneNode(true);
            
            // Update input names and ids in the new row
            const regex = new RegExp(`itens-(\\d+)-`, 'g');
            newRow.innerHTML = newRow.innerHTML.replace(regex, `itens-${formCount}-`);
            
            // Clear values
            const inputs = newRow.querySelectorAll("input, textarea, select");
            inputs.forEach(input => {
                if (input.type !== "hidden" || input.name.includes("DELETE")) {
                    if (input.type === "checkbox" || input.type === "radio") {
                        input.checked = false;
                    } else {
                        if (input.name.includes("-quantidade")) {
                            input.value = "1";
                        } else if (input.name.includes("-preco_unitario")) {
                            input.value = "";
                        } else {
                            input.value = "";
                        }
                    }
                } else if(input.name.includes("-id")) {
                    input.value = ""; // Clear PK hidden field for new row
                }
            });
            
            itemsBody.appendChild(newRow);
            totalFormsInput.value = formCount + 1;
        });
    });
</script>
"""

# Replace old script with new script
content = re.sub(r'<script>.*?</script>', js_code, content, flags=re.DOTALL)

with open('templates/core/orcamento_form.html', 'w') as f:
    f.write(content)

print("Done")
