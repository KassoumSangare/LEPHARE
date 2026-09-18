with open(r'c:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

import re

# Search where tarifparproduit or offreparproduit is called with arguments
for m in re.finditer(r'xa\.(?:get|post)\([^\)]*(?:tarifparproduit|offreparproduit|securiteroutiereparcompagnie|assistanceautomobile)[^\)]*\)', code):
    print(m.group(0))
