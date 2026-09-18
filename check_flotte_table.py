with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\flotte_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for table or list rendering vehiculesFLotte
pos = c.find("vehiculesFLotte")
while pos != -1:
    print(c[max(0, pos-100):min(len(c), pos+400)])
    print("="*60)
    pos = c.find("vehiculesFLotte", pos+15)
