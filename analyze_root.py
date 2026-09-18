with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_root.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Find API calls made in useEffect or callbacks
calls = set(re.findall(r'api/[a-zA-Z0-9_\-]+', c))
print("APIs called in devis_auto_root:", sorted(list(calls)))

# Look at typeContrat checks or conditionals
conditions = re.findall(r'typeContrat[^,;{}()]{0,100}', c)
print("\ntypeContrat conditions:")
for cond in conditions[:10]:
    print(" -", cond)
