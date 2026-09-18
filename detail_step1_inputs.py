with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\contrat_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Let's inspect each select and input in step 1 with their labels and full JSX
matches = re.finditer(r'label[^>]*children:\"([^\"]+)\"\}\),(.*?)(?=\(\d+,\$l\.jsx\)\(\"label\"|\Z)', c, re.DOTALL)
for m in matches:
    label = m.group(1)
    content = m.group(2)[:400]
    print(f"=== LABEL: {label} ===")
    print(content)
    print("\n" + "="*50)
