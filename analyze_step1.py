with open(r'c:\Users\HP\Documents\PROJET ASSURANCE\Backup Uranus\uranus-backend\contrat_step_code.js', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Find all select elements and inputs in step 1
print("=== LABELS AND SELECTS/INPUTS IN STEP 1 ===")
for m in re.finditer(r'children:\"([^\"]+)\"\}\)[^;]+?(select|input)[^}]+name:\"([^\"]+)\"', c):
    print(f"Label: {m.group(1)} | Type: {m.group(2)} | Name: {m.group(3)}")

# Also look for useEffect in step 1
print("\n=== USEEFFECTS IN STEP 1 ===")
effects = re.findall(r'\(0,s\.useEffect\)\(\(\)=>{([^}]+(?:\{[^}]+(?:\{[^}]+\})*[^}]*\})*[^}]*\}\s*,\s*\[([^\]]*)\]\)', c)
for eff, deps in effects:
    print(f"Deps: [{deps}]")
    print(f"Body: {eff[:300]}")
    print("-" * 50)
