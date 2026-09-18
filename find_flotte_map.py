with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\flotte_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# In Y$, vehiculesFLotte is renamed to 'be' in the destructuring: vehiculesFLotte:be
# Let's search for 'be.map(' in c
matches = [m.start() for m in re.finditer(r'be\.map\(', c)]
print("Matches for be.map in Y$:", matches)
for p in matches:
    print(c[max(0, p-100):min(len(c), p+800)])
