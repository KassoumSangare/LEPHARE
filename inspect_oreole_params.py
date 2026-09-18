import re

oreole_fe = r'C:\Users\HP\Downloads\OREOLE\OREOLE\APPLICATIONS\uranus-frontend\build\static\js\main.092db3ec.js'
with open(oreole_fe, 'r', encoding='utf-8', errors='ignore') as fp:
    c = fp.read()

routes = [
    '/parametrage/formule-securite',
    '/parametrage/garanties',
    '/parametrage/marque-vehicule',
    '/parametrage/offre',
    '/parametrage/offre-garantie',
    '/parametrage/reduction-flotte',
    '/parametrage/sous-garanties',
    '/parametrage/taux-commission',
    '/parametrage/taux-taxe',
]

for r in routes:
    pos = c.find(r)
    print(f'=== ROUTE {r} ===')
    if pos != -1:
        snippet = c[max(0, pos-200):min(len(c), pos+400)]
        print(snippet[:300])
    else:
        print('Not found')
