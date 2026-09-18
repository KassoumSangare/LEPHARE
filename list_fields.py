with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\vehicule_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Find JSX elements in order
pos = 0
for m in re.finditer(r'label[^>]*children:\"([^\"]+)\"|(input|select)[^}]+name:\"([^\"]+)\"', c):
    print(m.groups())
