import re

bundle_path = r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js'
with open(bundle_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print("Searching for routes and devis keywords...")
matches = re.findall(r'["\'](/[^"\']+)["\']', content)
devis_paths = set([m for m in matches if 'devis' in m.lower() or 'quote' in m.lower()])
for p in sorted(devis_paths):
    print("PATH:", p)

api_paths = set([m for m in matches if m.startswith('/api/') and any(k in m.lower() for k in ['voyage', 'transport', 'sante', 'mrh', 'habitation', 'ia', 'accident'])])
for p in sorted(api_paths):
    print("API:", p)
