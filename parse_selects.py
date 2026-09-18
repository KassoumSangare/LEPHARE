with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Find select declarations and their names/labels
select_matches = re.finditer(r'name:\"([^\"]+)\"[^}]*onChange:([^,}]+)', c)
for m in select_matches:
    print(f"Select name: {m.group(1)} | onChange: {m.group(2)}")

# Print all labels and their corresponding inputs/selects
label_matches = re.finditer(r'children:\"([^\"]+)\"\}\)[^()]*\(\d+,\$l\.jsx\)\(\"([^\"]+)\",\{name:\"([^\"]+)\"', c)
for m in label_matches:
    print(f"Label: {m.group(1)} -> Element: {m.group(2)}, Name: {m.group(3)}")
