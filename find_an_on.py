with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_root.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for definitions of an, nn, on, sn in root
# setTransportCompteAssure: an, transportCompteAssure: nn
matches = re.finditer(r'([a-zA-Z0-9_$]+)\s*,\s*([a-zA-Z0-9_$]+)\]\s*=\s*\(0,s\.useState\)\(false|\(0,s\.useState\)\(!1\)', c)
for m in matches:
    print(m.group(0))

# Also search for 'an(' or 'on(' or 'nn'
print("\n--- Searches for an( or on( ---")
for m in re.finditer(r'([a-zA-Z0-9_$]{1,3})\s*\(.*?(?:compte|marchandise|categorie|usage).*?\)', c, re.IGNORECASE):
    print(m.group(0)[:150])
