with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_full.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

print("--- RECHERCHE DE TOUS LES SELECTS ET INPUTS ---")
for m in re.finditer(r'label[^>]*children:\"([^\"]+)\"|name:\"([^\"]+)\"[^}]*onChange:([^,}]+)', c):
    print(m.groups())
