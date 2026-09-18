with open(r'c:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

import re

pos = code.find("(0,$l.jsx)(Y$,{idAvenant:")
print("JSX call to Y$:", pos)
# Find where Y$ is defined before this position
m = [m.start() for m in re.finditer(r'Y\$=', code[:pos])]
print("Y$= matches:", m)
if m:
    def_pos = m[-1]
    print(code[def_pos:def_pos+4000])
    with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\flotte_step_code.js', 'w', encoding='utf-8') as out:
        out.write(code[def_pos:def_pos+30000])
