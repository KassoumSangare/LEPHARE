with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\vehicule_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for inputs after "Type commercial du v\xe9hicule"
pos = c.find("Type commercial du v")
print(c[pos:pos+4000])
