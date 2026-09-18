with open(r'c:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

import re

# Find occurrences of tarifparproduit or how offres/tarifs are fetched
for m in re.finditer(r'tarifparproduit', code):
    p = m.start()
    print("--- tarifparproduit around", p)
    print(code[max(0, p-300):min(len(code), p+400)])
