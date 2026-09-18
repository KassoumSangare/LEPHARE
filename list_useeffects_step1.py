with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\contrat_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for useEffect positions
positions = [m.start() for m in re.finditer(r'useEffect', c)]
print(f"Found {len(positions)} useEffect in step 1:")
for p in positions:
    snippet = c[p:p+600]
    # find ending of useEffect
    print(snippet[:300])
    print("="*50)
