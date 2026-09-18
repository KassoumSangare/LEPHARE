import re

oreole_fe = r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js'
with open(oreole_fe, 'r', encoding='utf-8', errors='ignore') as fp:
    c = fp.read()

matches = set(re.findall(r'"(/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+)"', c))
param_routes = [m for m in matches if any(k in m for k in ['param', 'config', 'admin', 'profil', 'utilisat', 'role', 'user', 'compagnie', 'tarif', 'produit'])]
print('Param/Config/Admin routes in OREOLE:')
for r in sorted(param_routes):
    print('-', r)
