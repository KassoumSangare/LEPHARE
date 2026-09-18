with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_full.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for usage of typeContrat or type_contrat in full code
pos_matches = [m.start() for m in re.finditer(r'typeContrat', c)]
print("Matches for typeContrat:", len(pos_matches))
for p in pos_matches:
    print(c[max(0, p-100):min(len(c), p+200)])
    print("="*60)
