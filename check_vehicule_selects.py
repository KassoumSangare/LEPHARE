with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_vehicule.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for select tags or onChange in devis_auto_vehicule.js
selects = re.findall(r'name:\"([^\"]+)\"[^}]*onChange:([^,}]+)', c)
print("Selects in devis_auto_vehicule:")
for s in selects:
    print(s)

labels = re.findall(r'children:\"([^\"]+)\"\}\)[^()]*\(\d+,\$l\.jsx\)\(\"select\",\{name:\"([^\"]+)\"', c)
print("\nLabels with select in devis_auto_vehicule:")
for l in labels:
    print(l)
