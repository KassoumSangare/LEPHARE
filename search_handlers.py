with open(r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

import re

# Find occurrences of devis automobile or contract type triggers
matches = [m.start() for m in re.finditer(r'type_contrat', code)]
print("Matches for type_contrat:", len(matches))

for i, pos in enumerate(matches[:5]):
    print(f"\n--- MATCH {i} around {pos} ---")
    start = max(0, pos - 400)
    end = min(len(code), pos + 1000)
    print(code[start:end])
