with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_root.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for te, re passing into <o$
pos = c.find("CarburantAutreMatiere")
if pos != -1:
    print(c[max(0, pos-1500):min(len(c), pos+1500)])
else:
    print("Not found CarburantAutreMatiere in devis_auto_root")
