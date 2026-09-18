with open(r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

import re

# Find occurrences of auto specific terms: energie, immatriculation, genrevehicule, puissance, cylindree
for kw in ['genrevehicule', 'immatriculation', 'assistanceautomobile', 'securiteroutiereparcompagnie']:
    matches = [m.start() for m in re.finditer(kw, code)]
    print(f"Keyword '{kw}' found at: {matches[:3]}")

# Let's inspect around genrevehicule
if matches:
    pos = matches[0]
    start = max(0, pos - 10000)
    end = min(len(code), pos + 25000)
    with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_vehicule.js', 'w', encoding='utf-8') as out:
        out.write(code[start:end])
    print("Written devis_auto_vehicule.js around genrevehicule, len:", end - start)
