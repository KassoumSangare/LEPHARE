with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_root.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Search where transportCompteAssure or transportPublicMarchandise is computed or defined in root
for term in ['transportCompteAssure', 'transportPublicMarchandise', 'categorie']:
    for m in re.finditer(term, c):
        p = m.start()
        print(f"--- Found {term} at {p} ---")
        print(c[max(0, p-100):min(len(c), p+200)])
