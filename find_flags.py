with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\vehicule_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for definitions of te, re (condition flags for displaying checkboxes)
matches = re.finditer(r'([a-zA-Z0-9_$]+)\s*=\s*(?:1|2|3|4|5|6|7|8|9|10|[^\n;]*categorie|[^\n;]*tarif|[^\n;]*usage)[^\n;]*', c)
for m in matches:
    print(m.group(0)[:150])
