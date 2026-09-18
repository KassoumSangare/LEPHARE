with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\contrat_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for rh, th, nh, ih definitions in or before i$
pos = c.find("ih=")
if pos != -1:
    print("ih around:", c[pos-200:pos+300])

for const_name in ['ih', 'rh', 'th', 'nh', 'eh']:
    m = re.search(r'const\s+' + const_name + r'\s*=\s*\[[^\]]+\]', c)
    if m:
        print(f"{const_name} =", m.group(0))
