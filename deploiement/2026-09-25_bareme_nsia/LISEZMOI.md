# Mise en production — barème automobile aligné sur NSIA (25/09/2026)

Corrige, dans la base PostgreSQL de production :

| Correction | Avant | Après |
|---|---|---|
| Sécurité routière FORMULE I NSIA, 3 places (couvre 1 à 3) | 6 000 | 5 400 |
| Sécurité routière FORMULE I NSIA, 5 places | 6 000 | 7 650 |
| Sécurité routière FORMULE I NSIA, 7 places | 6 000 | 10 345 |
| Incendie tarifs 121/122/123 (TPC boisées) au-delà de 10 M | 3,5 ‰ | 2,5 ‰ |
| Bonus (BNS) sur le bris de glace avec toits ouvrants (sous-garantie 172) | non | oui |

Sources et justification : `configuration_api/migrations/0068_bareme_nsia_securite_routiere_incendie.py`
et `production/migrations/0141_fn_calcul_prime_prorata_bns_bris_glace_toits.py`.

**Attention : effet immédiat sur URANUS si la base est partagée.** URANUS et LE PHARE utilisent les
mêmes fonctions de tarification. Si LE PHARE et URANUS pointent sur la même base de production, les
nouveaux montants s'appliquent aussitôt aux devis faits dans URANUS. Obtenir l'accord d'OREOLE avant.

## 1. Sauvegarde (obligatoire)

```bash
pg_dump -U <utilisateur> -Fc -f oreole_avant_bareme_nsia_$(date +%F_%H%M).dump <base>
```

## 2. Appliquer — choisir UNE des deux options

**Option A — le serveur exécute LE PHARE (Django)** : les migrations appliquent aussi toutes celles qui
sont en attente. Vérifier d'abord la liste :

```bash
python manage.py showmigrations configuration_api institutionnel production | grep "\[ \]"
python manage.py migrate
```

Sur la sauvegarde de production du 11/09/2026, les migrations en attente étaient : `configuration_api`
0066, 0067, 0068 ; `institutionnel` 0001, 0002 ; `production` 0140, 0141.

**Option B — seul URANUS est installé, ou pour n'appliquer que ces corrections** :

```bash
psql -v ON_ERROR_STOP=1 -U <utilisateur> -d <base> -f appliquer.sql
```

Le script vérifie d'abord que les lignes attendues existent, sinon il s'arrête sans rien modifier.
Il peut être relancé sans risque, et reste compatible avec un `migrate` ultérieur (option A).

## 3. Vérifier

La fin de `appliquer.sql` affiche : `1:5400 4:10345 14:7650`, `1059:2.5000 1060:2.5000 1061:2.5000`
et `t`. Contrôle métier (camionnette NSIA EBENE PREMIUM TPC, doit donner `172:63147 10:26678 169:5400`) :

```sql
SELECT string_agg(idsousgarantie || ':' || primenette::int, ' ')
FROM fn_garantie_offre(1, 99, 123, 36083931, 23453555, 300000, 15, 2, 1095, 35, 0, '2026-02-19',
     '2027-02-18', 30, '2024-11-07', false, 'FORMULE I', 0, 2, 3, false, false, false, false, true)
WHERE idsousgarantie IN (10, 169, 172);
```

## 4. Revenir en arrière

- Option A : `python manage.py migrate configuration_api 0067 && python manage.py migrate production 0140`
- Option B : `psql -v ON_ERROR_STOP=1 -U <utilisateur> -d <base> -f annuler.sql`

Testé le 25/09/2026 sur une restauration de la base de production du 11/09/2026 : application,
relance, contrôle métier et annulation conformes.
