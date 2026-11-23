# LE PHARE en production

`npm run dev` et `python manage.py runserver` sont des serveurs de **développement** : l'interface est envoyée module par
module et recompilée à la demande (des centaines de fichiers par page, dont des écrans de 100 à 270 Ko), et l'API traite
les postes sans serveur de production. C'est la première cause de lenteur en production.

## Démarrage

Double-cliquer sur `demarrer_production.bat` à la racine du projet, ou lancer à la main :

```bat
:: 1. API (une fois : pip install waitress)
python serveur_production.py

:: 2. Interface compilée (dans frontend\)
npm run build
npm run preview
```

L'adresse ne change pas : http://<serveur>:3000. L'interface renvoie toujours `/api` vers l'API sur 127.0.0.1:8000.

Après chaque mise à jour du code de l'interface, relancer `npm run build` (le `.bat` le fait) : `vite preview` sert
le dossier `frontend\dist` compilé, il ne voit pas les fichiers modifiés tant qu'on ne recompile pas.

## Réglages à vérifier dans `.env`

- `DEBUG=0` : en DEBUG, Django garde chaque requête SQL en mémoire et ralentit au fil de la journée ; il affiche aussi
  des pages d'erreur détaillées.
- `DJANGO_ALLOWED_HOSTS` doit contenir au moins `127.0.0.1 localhost` (avec DEBUG=0, Django refuse les autres hôtes).
- `DB_CONN_MAX_AGE` : laisser 60 (connexions PostgreSQL réutilisées).

## Options de l'API

```bat
python serveur_production.py --fils 24     :: plus de postes en même temps (une connexion PostgreSQL par fil)
python serveur_production.py --port 8001
```

## Retour à l'ancien mode

`python manage.py runserver` et `npm run dev` fonctionnent toujours, pour le développement.
