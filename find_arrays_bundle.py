with open(r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

import re

for const_name in ['ih', 'rh', 'th', 'nh']:
    m = re.search(r'(?:var|const|let)\s+' + const_name + r'\s*=\s*\[[^\]]+\]', code)
    if m:
        print(f"{const_name} =", m.group(0))
    else:
        # try find where it's assigned
        for match in re.finditer(const_name + r'\s*=\s*\[', code):
            p = match.start()
            print(f"Assign {const_name}:", code[p:p+300])
