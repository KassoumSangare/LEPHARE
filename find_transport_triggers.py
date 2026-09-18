with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\devis_auto_root.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Look for nn and sn definitions (setTransportCompteAssure, setTransportPublicMarchandise)
pos = c.find("setTransportCompteAssure")
if pos != -1:
    print(c[max(0, pos-3000):min(len(c), pos+1500)])
