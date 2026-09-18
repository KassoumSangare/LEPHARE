with open(r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

import re

for pos in [2540078, 2593757, 2859647, 3017562]:
    print(f"\n================ POS {pos} ================")
    start = max(0, pos - 500)
    end = min(len(code), pos + 1500)
    print(code[start:end])
