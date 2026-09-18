with open(r'c:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

import re

# Find i$ definition (Step 1 - Contrat step)
pos = code.find("i$=function")
print("i$ position:", pos)
if pos != -1:
    with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\contrat_step_code.js', 'w', encoding='utf-8') as out:
        out.write(code[pos:pos+25000])
    print("Written contrat_step_code.js")
