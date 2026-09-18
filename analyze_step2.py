with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\vehicule_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Find all occurrences of select or input in step 2
inputs = re.findall(r'name:\"([^\"]+)\"', c)
print("Unique input/select names in step 2:", sorted(list(set(inputs))))

labels = re.findall(r'children:\"([^\"]+)\"', c)
print("\nLabels in step 2:", sorted(list(set([l for l in labels if len(l) < 40]))))
