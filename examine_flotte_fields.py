with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\flotte_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for selects and labels in Flotte step Y$
matches = re.finditer(r'label[^>]*children:\"([^\"]+)\"\}\),(.*?)(?=\(\d+,\$l\.jsx\)\(\"label\"|\Z)', c, re.DOTALL)
for m in matches:
    label = m.group(1)
    content = m.group(2)[:300]
    print(f"FLOTTE FIELD: {label}")
    name_m = re.search(r'name:\"([^\"]+)\"', content)
    if name_m:
        print("  -> Name:", name_m.group(1))
    print("  -> Code:", content[:150].replace('\n', ' '))
    print("-" * 50)
