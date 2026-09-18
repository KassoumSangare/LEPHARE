with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\vehicule_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Let's inspect each form element in step 2
matches = re.finditer(r'children:\"([^\"]+)\"\}\)[^;]+', c)
for m in matches:
    snippet = m.group(0)[:300]
    # Filter only relevant field snippets
    if any(k in snippet for k in ['select', 'input', 'onChange', 'disabled']):
        print("FIELD:", snippet)
        print("-" * 50)
