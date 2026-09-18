with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\vehicule_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Find all form controls and their surrounding html/props
matches = re.finditer(r'\(\d+,\$l\.jsxs?\)\(\"div\",\{className:\"[^\"]*\",children:\[\(\d+,\$l\.jsx\)\(\"label\",\{[^}]*children:\"([^\"]+)\"\}\),(.*?)(?=\(\d+,\$l\.jsxs?\)\(\"div\"|\Z)', c, re.DOTALL)

for m in matches:
    label = m.group(1)
    field_code = m.group(2)[:300]
    # Check if disabled prop is used
    disabled_match = re.search(r'disabled:([^,}]+)', field_code)
    disabled_info = disabled_match.group(1) if disabled_match else "none"
    name_match = re.search(r'name:\"([^\"]+)\"', field_code)
    field_name = name_match.group(1) if name_match else "unknown"
    print(f"LABEL: {label.encode('ascii', 'ignore').decode()} | NAME: {field_name} | DISABLED: {disabled_info}")
