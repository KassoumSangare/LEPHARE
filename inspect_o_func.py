with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\vehicule_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for te, re around start of o$
pos = c.find("o$=function")
print(c[pos:pos+2500])
