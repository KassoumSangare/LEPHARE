# Audit Uranus (OREOLE ASSURANCES) — couverture fonctionnelle et fiabilité des calculs

*Date de l'audit : 23/09/2026. Périmètre : dossiers `_OREOLE ASSURANCE` (documents métier) et `OREOLE` (code source + sauvegardes de base).*

## 0. Synthèse

| # | Constat | Gravité |
|---|---|---|
| 1 | **Montant en lettres des factures faux dans 17,2 % des cas** : la fonction JS `nombreEnLettres` (factures proforma Auto) produit `undefined` pour tout groupe 11 à 19 (ex. 30 513 → « TRENTE MILLE CINQ CENT DIX undefined »). Reproduit à l'identique sur les deux factures PDF fournies par OREOLE. | Critique |
| 2 | **Modèle de prime incohérent** : selon le parcours (tarifé ou « prime imposée »), la CEDEAO est incluse ou non dans la prime nette stockée. La formule « TTC = PN + Accessoire + Taxe + FGA + CEDEAO » n'est donc pas vérifiable sans connaître le parcours ; 47 devis Auto sur 311 (12 mois) ne respectent aucune des deux règles. | Critique |
| 3 | **Prime imposée sans contrôle** : `sp_maj_manuelle_primes` accepte une Prime TTC de 999 999 alors que les composantes totalisent 122 225 (test exécuté). | Élevée |
| 4 | **Tarif Voyage obsolète** : la grille en base (bande d'âge unique 0–75 ans, durée 22–31 j) donne 21 235 FCFA de prime nette pour un assuré de 68 ans / 31 jours ; le tarif AMSA à jour (×250 % pour 66–75 ans) donne 41 328 à 48 461 FCFA selon la zone. | Élevée |
| 5 | **Suppression physique autorisée** : `DELETE /api/client/{id}/` supprime réellement le client (HTTP 204, ligne effacée) ; les devis MRH non confirmés sont aussi supprimés physiquement. Contraire à « archivage logique sans suppression ». | Élevée |
| 6 | **Anti-doublon client limité à la CNI exacte** : un second client identique au nom près (« AUDIT DOUBLON » / « AUDIT-DOUBLON ») est accepté ; le doublon de CNI est bloqué par une contrainte base qui renvoie une **erreur HTTP 500** au lieu d'un message. | Moyenne |
| 7 | **Numérotation** : la « clé » finale est une lettre tournante (pas une clé de contrôle), l'année est celle de l'émission (pas de la souscription), le compteur de police n'est pas verrouillé (doublons possibles en concurrence) et tronqué au-delà de 99 999. | Moyenne |
| 8 | **Arrondi NSIA au multiple de 5 inactif** : la fonction `fn_calculer_primettc` existe mais n'est rattachée à aucun trigger ; les nouveaux devis ne sont plus arrondis alors que 213/293 devis NSIA historiques le sont. | Moyenne |
| 9 | Modules de la spécification V3 **absents** d'Uranus : CRM (leads, pipeline, campagnes), sinistres délégués (menu sans back-end), journal d'audit (désactivé), sécurité de connexion (blocage, MFA), rétrocessions, rapprochement compagnie. | Information (écart de périmètre) |

**Constat structurant pour LE PHARE** : le back-end de LE PHARE est un fork quasi identique du back-end Uranus (`customer/models.py` identique, `production/models.py` à 39 lignes près) et partage la même base PostgreSQL et ses 244 routines. Toutes les règles de calcul ci-dessous s'appliquent donc aujourd'hui à LE PHARE.

---

## 1. Méthode et environnement d'exécution

| Élément | Ce qui a été fait |
|---|---|
| Documents | 54 fichiers parcourus (46 uniques après dédoublonnage par empreinte) : texte extrait (docx, pdf, xlsx, xls, pptx), PDF scanné lu visuellement, 38 captures d'écran uniques examinées. |
| Code back-end | `uranus-backend` (Django 4.2.13 / DRF / PostgreSQL) lu ; 244 routines PL/pgSQL extraites de la sauvegarde `oreole_testing_db_2026_09_05_17_35.sql` (dont beaucoup ne sont pas versionnées dans le dépôt). |
| Code front-end | Livré **compilé uniquement** (pas de `src`, pas de `package.json`). 416 fichiers sources reconstitués depuis la source map `main.092db3ec.js.map` livrée dans le build. |
| Exécution back-end | Base `uranus_audit` restaurée depuis la sauvegarde *testing* (pas de sauvegarde de production utilisée). Uranus lancé sur `127.0.0.1:8001` sans modifier le dossier livré (`.env` d'audit placé dans un répertoire de travail séparé). Tests via l'API REST avec un utilisateur d'audit. |
| Exécution front-end | Les fonctions de génération de documents ont été **exécutées** sous Node à partir des sources reconstituées. L'interface complète n'a **pas** été servie : voir §4. |

---

## 2. Inventaire des documents (étape 1)

| Document | Type | Contenu (une ligne) |
|---|---|---|
| Besoin Fonctionnel/Specifications_fonctionnelles_OREOLE_Assurances_V3.docx (+ .pdf identique en contenu) | Spécification | Spécifications fonctionnelles cible écran par écran : 12 modules A→L (~80 écrans), règles transverses, priorisation MVP1/MVP2/V2+. |
| Besoin Fonctionnel/Creation et gestion des clients(developpeur).docx (doublon dans Comptes Rendus Reunions/) | Spécification | Création client en cours de saisie, dédoublonnage/identifiant unique, parcours Auto (mono/flotte, écarts de prime, prime imposée, saisie progressive flotte), IA (individuel, groupe, import Excel), Transport GUCE, Voyage. |
| DOCUMENT RECAPITULATIF SEANCE LE PHARE DU 09 09 2026.docx | Compte rendu | Priorités OREOLE après la séance du 09/09/2026 (client → auto → IA → transport → voyage ; santé, RD, MRH, RC en attente) + 12 captures. |
| Besoin Fonctionnel/DOCUMENT PROJET LE PHARE.docx | Captures | Écrans Uranus : création client, production Auto/MRH/IA/Voyage/Transport, listes de mouvements. |
| Besoin Fonctionnel/DOCUMENTS LE PHARE.docx | Captures | 28 captures Uranus par produit (Auto mono/flotte, IA, MRH, Transport, Voyage, Santé). |
| LE_PHARE/Exploration_de_Le_Phare.docx | Remarques | Retours sur LE PHARE : mode de règlement, statuts bancaires (acompte, soldé, impayé, en attente), état des primes à reverser par compagnie. |
| Plan De Travail/Plan_de_mise_en_oeuvre.docx | Plan | Profils/droits, cartographie des modules, fiche technique serveur (Ubuntu, PostgreSQL 14+, Redis, Nginx, UFW). |
| Plan De Travail/Plan_de_Management_de_Projet_LEPHARE_FINAL_0809226.xlsx | Plan | Planning (phases 1–6, sprints du 07/09 au 30/11/2026), budget, matrice des risques, RACI. |
| Presentation_Oreoles_Assurance_Uranus.pptx | Présentation | Plan de présentation (contexte, état des lieux, bilan, perspectives, stratégie, planning) — titres uniquement. |
| AUTO/OREOLE_Codes_Categorie_Numerotation.docx (+ versions IA, TRANSPORT, VOYAGE) | Règle métier | Codes catégorie par branche et règle de numérotation police/devis (code courtier + catégorie + année + séquentiel + clé ; « D » pour les devis). |
| AUTO/FACTURE AUTO PREFORMA.pdf | Exemple Uranus | Facture proforma Auto 1186/09-2026/00004 — montant en lettres « TRENTE MILLE CINQ CENT DIX undefined ». |
| AUTO/FACTURE ASSURANCE AUTOMOBILE.pdf | Exemple Uranus | Facture de prime 00005/1186/08-2026 — « DIX undefined MILLE HUIT CENT QUARANTE CINQ ». |
| AUTO/CONDITIONS PARTICULIERES ASSURANCE AUTO.pdf | Exemple Uranus | CP Auto mono police 1186201263156M (véhicule, garanties, récapitulatif). |
| CONDITIONS PARTICULIERES AUTO.pdf (doublon dans AUTO/) | Exemple assureur (scan) | CP NSIA « exemplaire courtier », avenant de renouvellement, offre EBENE PREMIUM TPC — référence des règles NSIA (BNS, réduction, FGA, arrondi). |
| AUTO/ASSURANCE AUTO FLOTTE CONDITIONS PART..pdf | Exemple Uranus | CP flotte 1186201263196A (synthèse par nature de risque, « Voir Annexes »). |
| AUTO/ASSURANCE AUTO FLOTTE (ANNEXE).pdf | Exemple Uranus | Annexe liste des véhicules de la flotte 1186201263196A. |
| LISTE DE VEHICULE FLOTTE(ANNEXE DANS URANUS).pdf (doublon dans AUTO/) | Exemple Uranus | Annexe flotte 1186212263169W (5 véhicules). |
| IA/ASSURANCE IA FACTURE PREFORMA.pdf | Exemple Uranus | Facture IA à primes nulles (capitaux à 0), ayants droit. |
| IA/ASSURANCE IA CONDITIONS PART..pdf | Exemple Uranus | Proposition IA groupe à 0 FCFA. |
| IA/CONDITIONS PARTICULIERES IA GROUPE.pdf | Exemple Uranus | Contrat IA groupe 1186119263142P, avenant d'incorporation, 18 000 FCFA. |
| IA/QUITTANCE IA GROUPE.pdf | Exemple Uranus | Quittance IA groupe (garanties décès/infirmité, prime prorata). |
| IA/ASSURANCE IA ANNEXE.pdf | Exemple Uranus | Annexe liste des assurés/ayants droit d'un devis IA. |
| FICHIER IA RESSORTI PAR URANUS.pdf (doublon dans IA/) | Exemple Uranus | Annexe IA police 1186119263143Q (parts 33 %/33 %/33 %). |
| IA/IA ATM INFORMATIQUE 2026.xlsx | Données | Fichier d'import IA groupe (assurés, capitaux, bénéficiaires, prime HT/TTC). |
| TARIF IA_NSIA CI.xlsx | Tarif | Mode de calcul IA NSIA (classes d'activité, taux ‰, ITT = 0,25 ‰ × (décès + invalidité)). |
| MRH/ASSURANCE MRH FACTURE PREFORMA.pdf | Exemple Uranus | Proposition MRH (8 garanties, PN 950 508, TTC 1 088 333). |
| MRH/FACTURE MRH.pdf | Exemple Uranus | Facture MRH 1186/2026/000182. |
| MRH/QUITTANCE MRH.pdf | Exemple Uranus | Quittance MRH 1186320263168V. |
| MRH/MRH LISTE GARANTIES PROPRIETAIRE OCCUPANT TOTAL.pdf | Modèle | Gabarit vierge (XXXX) de la liste des garanties MRH propriétaire occupant total. |
| VOYAGE/ASSURANCE VOYAGE FACTURE PREFORMA.pdf | Exemple Uranus | Facture voyage AMSA 205313726D1874N. |
| VOYAGE/ASSURANCE VOYAGE PROPOSITION.pdf | Exemple Uranus | Proposition voyage AMSA (31 jours, assurée née en 1958). |
| VOYAGE/QUITTANCE ASSURANCE VOYAGE.pdf | Exemple Uranus | Quittance voyage AMSA 2053137250317G. |
| VOYAGE/OK TARIFS Assurances voyages COVEREDGE - AMSACI -03112025.xlsx | Tarif | Tarif AMSA à jour par zone, durée et tranche d'âge (taxe = 14,5 % × (PN + accessoire)). |
| VOYAGE/TARIF VOYAGE NSIA ASSURANCES.pdf | Tarif | Tarif voyage NSIA. |
| VOYAGE/TABLEAU COMPARATIF FORMULE OFFRES BOISEES.xlsx | Recette | Comparaison primes NSIA / Uranus des formules ACACIA, BAOBAB, EBENE PREMIUM. |
| VOYAGE/TABLEAU DES GARANTIES SOUMISES A REDUCTION.xlsx | Règle métier | Garanties soumises ou non à réduction commerciale et au BNS (ex. RC : BNS oui, réduction non ; CEDEAO : ni l'un ni l'autre). |
| TRANSPORT/QUITTANCE ASSURANCE TRANSPORT.pdf | Exemple Uranus | Quittance facultés maritimes SUNU 2431611260354K. |
| TRANSPORT/RESSORTIE DE PRIME FACULTES ... (v1).xls | Données | Bordereau GUCE n°01 (01–15/01/2026). |
| RESSORTIE DE PRIME A IMPLEMENTER... .xls (= TRANSPORT/... v2 - a implementer) | Modèle | Format de ressortie GUCE à implémenter. |
| certificatGenSearchResult EXTRACTION GUCE.xls (doublon dans TRANSPORT/) | Données | Extraction GUCE bordereau n°03 (01–15/02/2026). |
| SANTE/TARIFICATION MINENE SANTE.xlsx | Tarif | Tarif MINENE santé (taux 80 %/80 %, 70 %/80 %), répartition de la prime et frais de gestion. |
| Etats Decisionnels/ETATS DECISIONNEL.pdf | Exemple Uranus | Bordereau des émissions par compagnie, branche et client (01/01–09/09/2026, 40 pages). |
| Finance Encaissement/Bordereau_Emissions_Cie_Branche_Client_01-01-2026_31-03-2026.xlsx | Exemple Uranus | Export Excel du même bordereau (T1 2026). |
| TRE - ACTUALISEE.pdf | Référentiel | Traité des Risques d'Entreprises – Incendie (FFSA, 2009, 360 pages) : tarification incendie. |

---

## 3. Analyse statique du code (étape 3)

**Stack** : Django 4.2.13, Django REST Framework, authentification Knox, PostgreSQL (logique métier majoritairement en PL/pgSQL : 244 routines), Celery/Redis (tâches planifiées), React (build CRA/craco) avec génération PDF côté navigateur (`@react-pdf`). Intégrations : ASACI (attestations digitales), SMS (Arolitec, Nerhy), paiement Distripay.

**Applications Django** : `account`, `customer`, `production` (devis, contrats, quittances, encaissements, reversements, avenants), `configuration_api` (référentiels, offres, tarifs), `commissions`, `sante`, `asaci`, `reporting` (états décisionnels), `payment`, `messaging`, `autorisations` (demandes/jetons de validation).

**Où se trouvent les calculs**

| Calcul | Emplacement |
|---|---|
| Prime Auto par garantie | `fn_garantie_offre` → `fn_garantie_offre_cat{1,2,3,5}_{nsia,amsa,sunu}`, `fn_tarif_garantie_auto_*` (une fonction par catégorie × compagnie) |
| FGA | `ROUND(prime_rc × 2 / 100)` dupliqué dans 13 fonctions |
| CEDEAO | `fn_get_prime_cedeao` (sous-garantie 3 du tarif) |
| Taxes | `fn_calcul_montant_taxe` (taux par produit × sous-garantie, arrondi par garantie), `fn_get_taux_taxe` (taux MIN de l'offre pour la taxe sur accessoire) |
| Accessoires | `fn_get_accessoire` (+ `_compagnie`, `_intermediaire`, `_moto`, `_sante`) avec identifiants de compagnies et d'offres codés en dur |
| Prime TTC | `sp_finalisation_devis` ; arrondi NSIA dans `fn_calculer_primettc` (non rattachée) ; prime imposée : `sp_maj_manuelle_primes`, `sp_calcul_devis_prime_imposee` |
| Commission | `fn_get_taux_commission(produit, compagnie, date)` appliqué dans `sp_finalisation_devis` |
| Montant en lettres | Front : `nombreEnLettres` dans `ProformaAuto.jsx` et `IndexFactureOreole.jsx` ; SQL : `fn_nombre_en_lettres` (utilisé par `fn_info_encaissement`) |
| Numérotation | `sp_generer_numero_police`, `sp_generer_numero_devis`, `fn_generer_numero_facture` |

**Dette technique notable** : règles par compagnie codées en dur (IDs 1/14/21, offres 154–170, tarifs 145/76), taxe MINENE en montant fixe (`2976 × nb_adhérents`), journal d'audit désactivé (`auditlog` commenté), migrations de la base *testing* en retard de 6 sur le code.

---

## 4. Mise en route (étape 4)

| Composant | Prérequis | Statut |
|---|---|---|
| PostgreSQL 14 | Sauvegarde `.sql` (PG 15.8) restaurable en PG 14 | ✅ Restaurée dans `uranus_audit` — 2 erreurs seulement, toutes deux sur l'extension de développement `plpgsql_check` (absente, sans impact métier). |
| Rôle `uranususer` | Propriétaire des objets dans la sauvegarde | ✅ Présent localement. |
| Python / dépendances | `requirements.txt` (Django 4.2.13, DRF, knox, celery…) | ✅ Environnement virtuel de LE PHARE compatible (`manage.py check` sans erreur). |
| Configuration | `.env` lu **depuis le répertoire courant** (`dotenv_values(".env")`), variables d'environnement ignorées | ✅ `.env` d'audit dans un répertoire séparé (base locale, `DEBUG=1`, `URANUS_IN_PRODUCTION=0`, SMS/Distripay/ASACI neutralisés). Le dossier livré n'a pas été modifié. |
| Migrations | 6 migrations non appliquées sur la base *testing* (commissions, chèques, quittances) | ✅ Appliquées sur `uranus_audit`. |
| Redis / Celery | Uniquement pour les tâches planifiées | ❓ Non lancés (non nécessaires à l'API testée). |
| Front-end | Build livré **compilé avec l'URL de l'API de production** `http://51.255.50.137:8000/api/` | ❌ **Volontairement non servi** : se connecter depuis ce build aurait envoyé des requêtes à la production. Pour le faire tourner en local il faut les sources (`src` + `package.json`, non livrés ; `src` reconstituable depuis la source map) et un nouveau build avec `REACT_APP_API_URL=http://127.0.0.1:8001/api/`. |

**Alerte configuration** : le `.env` livré pointe vers `oreole_production_db` avec `URANUS_IN_PRODUCTION=1` et contient des secrets en clair (clé Django, identifiants SMTP, ASACI, SMS, Distripay). Le lancer tel quel sur un poste de développement peut déclencher des appels réels (attestations ASACI, SMS, paiements).

---

## 5. Règles de calcul (étape 5)

| Règle | Formule attendue (source) | Formule trouvée dans le code | Résultat observé à l'exécution | Écart |
|---|---|---|---|---|
| **FGA** | 2 % de la prime RC (CP NSIA scannée : 108 633 × 2 % = 2 173) | `ROUND(prime_rc × 2 / 100)` | Devis créé par l'API (25259) : RC 114 693 → FGA 2 294 | ✅ Conforme |
| **CEDEAO** | Montant fixe (1 000 FCFA mono), non soumis à réduction ni taxe (tableau des garanties soumises à réduction) | Sous-garantie 3 du tarif ; taux de taxe absent → 0 | 25259 : CEDEAO 1 000, taxe 0 | ✅ Montant ; ⚠️ incluse dans la prime nette stockée et **dans l'assiette de commission** (20 % × Σ garanties dont CEDEAO = 211 028) |
| **Taxes** | 14,5 % × (PN + accessoire) (tarifs voyage/MINENE) ; NSIA : CEDEAO exclue de l'assiette | Taux par produit × sous-garantie, arrondi garantie par garantie + taxe sur accessoire au taux minimal de l'offre. Taux en base : 14,5 % général, **25 %** sur 14 garanties MRH incendie/dommages électriques, **8 %** santé ; aucun taux pour Transport | 25259 : Σ taxes garanties 152 851 + 14,5 % × 24 000 = 3 480 → 156 331 ; la formule globale donne 156 330 | ⚠️ 1 FCFA d'écart dû à l'arrondi par garantie ; règle 25 % MRH non documentée dans les specs fournies ; Transport sans taux paramétré |
| **Accessoires** | Selon convention compagnie | Barème `fn_get_accessoire_compagnie` ; NSIA/AMSA/SUNU (IDs 1, 14, 21) : moitié compagnie / moitié intermédiaire ; cas IA codés en dur (500/500, 39,5/39,5) | 25259 : 24 000 (12 000 + 12 000) | ❓ Conforme au code ; barème des conventions non fourni pour comparaison |
| **Prime nette stockée** | Somme des primes nettes des garanties | `primenette = Σ garanties + FGA` (parcours tarifé, CEDEAO incluse) ; `primenette = PN saisie + FGA` sans CEDEAO (prime imposée) | 25259 : 1 057 435 = 1 055 141 + 2 294 ✅ ; contrat 1186201263156M : CEDEAO hors PN | ⚠️ Deux modèles selon le parcours |
| **Prime TTC** | PN + Accessoire + Taxe + FGA + CEDEAO | `ROUND(primenette + accessoire + taxe + accessoiregestionnaire)` (FGA et CEDEAO déjà dans `primenette`) | 25259 : 1 237 766 = PN + Acc + Taxe ✅. Sur 311 devis Auto (12 mois) : 143 suivent « CEDEAO dans PN », 131 « CEDEAO hors PN » (les deux règles se confondent pour les 10 devis sans CEDEAO), **47 aucune des deux** (dont 43 primes imposées) | ⚠️ Règle non unique ; 47 devis incohérents |
| **Arrondi NSIA** | TTC au multiple de 5 supérieur (CP NSIA : 943 567 → 943 570) | `fn_calculer_primettc` : `CEIL(TTC/5)*5` si compagnie 1 | Fonction **rattachée à aucun trigger** ; 25259 non arrondi (1 237 766) ; 213/293 devis NSIA historiques arrondis | ⚠️ Règle appliquée par le passé, plus aujourd'hui |
| **Prime imposée** | Traçable, sans modifier artificiellement les garanties (specs clients/auto) | `sp_maj_manuelle_primes` écrit les montants saisis tels quels | Appel avec PN 100 000 / Acc 5 000 / Taxe 15 225 / FGA 2 000 / CEDEAO 1 000 / **TTC 999 999** → accepté | ❌ Aucun contrôle de cohérence |
| **BNS / réduction commerciale** | Nette = annuelle × (1 − BNS) × (1 − réduction) ; RC : BNS oui, réduction non (CP NSIA, tableau des réductions) | Paramètres `Bns`, `TauxReduction` transmis à `fn_garantie_offre` | Tarification rejouée par l'API sur 4 devis réels : primes différentes des primes stockées (ex. devis 6253, RC 38 910 recalculée vs 24 056 stockée) | ❓ Non concluant : primes stockées issues d'anciens tarifs ou de corrections ; non-reproductibilité à signaler (spec D3 : « prime reproductible et justifiable ») |
| **Prime Auto (tarif)** | Tarif compagnie | Une fonction par catégorie × compagnie | L'API renvoie la liste complète des garanties de l'offre, toutes « Acquise=True », **plus une ligne « CUMUL DES MONTANTS DES S/GARANTIES »** qui double le total si on additionne la liste | ⚠️ Ligne de cumul mêlée aux garanties |
| **Commission intermédiaire** | Taux par produit/compagnie (G1–G2) | `ROUND(Σ PN garanties × taux / 100)` | 25259 : 211 028 = 20 % × 1 055 141 (CEDEAO incluse) | ⚠️ Assiette inclut la CEDEAO — à valider |
| **Durée du contrat** | — | `fn_calcul_id_duree_contrat(entier)` : 364 et 366 jours → annuel, **365 → « Divers »** | Lecture du code (l'autre version, par dates, est correcte) | ⚠️ Anomalie de bornes |
| **Montant en lettres (factures)** | Montant TTC exact en toutes lettres | JS `nombreEnLettres` : tableau `dizaines` de 10 cases lu à l'indice `chiffre + 10` | Exécution sur 1 → 1 000 000 : **171 900 montants (17,2 %) contiennent `undefined`** ; 30 513 et 18 845 reproduisent exactement les factures fournies | ❌ Voir bug B1 |
| **Montant en lettres (reçus d'encaissement)** | Idem | SQL `fn_nombre_en_lettres` | 1 000 → « un mille », 80 000 → « quatre-vingts mille », 200 000 → « deux cents mille », espace initial, majuscules ≤ 100 et minuscules au-delà | ⚠️ Pas de `undefined`, mais français incorrect ; deux implémentations divergentes |
| **Numéro de police / devis** | code courtier + catégorie + année de souscription + séquentiel + clé ; « D » pour le devis | Année = `CURRENT_DATE` ; séquentiel par couple intermédiaire × compagnie, complété à 4 chiffres, tronqué aux 5 derniers au-delà ; « clé » = lettre tournante sur 23 lettres ; lecture puis mise à jour du compteur sans verrou | Devis 25259 : `118620126D4450P` ✅ format | ⚠️ Pas de clé de contrôle ; année d'émission ; collisions possibles |
| **Numéro de facture** | `1186/09-2026/00004` (proforma) | Devis : `code/MM-AAAA/NNNNN` ; contrat : `NNNNN/code/MM-AAAA` ; séquence mensuelle **verrouillée** (`FOR UPDATE`) | 25259 : `1186/09-2026/00001` ✅ | ⚠️ Deux nomenclatures devis/contrat |
| **Prime Voyage** | Tarif à jour NSIA/AMSA (compte rendu 09/09) | `StdZoneVoyagePrime` par zone × durée × âge | Âge 68 ans, 31 jours : 21 235 (zone 3) / 25 821 / 21 964 ; tarif AMSA à jour : 41 328 / 42 262 / 48 461 | ❌ Tarif obsolète (bande unique 0–75 ans) |
| **IA** | Prime = taux × capital ; ITT = 0,25 ‰ × (décès + invalidité) ; parts d'ayants droit = 100 % | `fn_tarif_ia_groupe`, `fn_tarif_ia_personnalise`, `fn_calcul_prime_ia_by_age` | Quittance IA groupe : PN 12 720 = 2 × 6 360 (primes annuelles) alors que la colonne « prorata » affiche 6 360 et 0 (189 jours) ; annexe IA : 3 × 33 % = 99 % | ⚠️ Prorata incohérent à l'affichage ; arrondi des parts |
| **MRH** | — | `mrh_calcul_service.py`, `fn_repartir_prime_sur_garanties` | Proposition MRH : Σ primes « annuelles » = TTC (1 088 333) ; répartition manuelle : ligne saisie à 12 000 avec taxe 131 (1,1 %) et alerte « +11 097 » | ⚠️ Taxe non recalculée après saisie manuelle |

---

## 6. Bugs runtime constatés

| ID | Bug | Conditions de reproduction |
|---|---|---|
| **B1** | `undefined` dans le montant en lettres des factures Auto | Générer une facture proforma Auto dont la Prime TTC contient un groupe 11 à 19 (unités de mille ou unités), ex. 18 845 ou 30 513. Cause : `dizaines[chiffre + 10]` sur un tableau de 10 éléments (`ProformaAuto.jsx`, `IndexFactureOreole.jsx`). Autres erreurs de la même fonction : « VINGT UN », « SOIXANTE-DIX UN », « QUATRE-VINGT-DIX DEUX », « UN MILLE », « DEUX MILLION », pas de devise. |
| **B2** | Génération de facture impossible si la Prime TTC est absente | TTC `null`/`undefined` → `parseInt` → chaîne vide → exception `Cannot read properties of null (reading 'map')` ; TTC = 0 → montant en lettres vide. |
| **B3** | « NaN » affiché sur l'écran « Mouvement police » Auto | Capture « Mouvement police n°1186201263156M » (DOCUMENT PROJET LE PHARE.docx) : « NaN » sous le bloc Contrat. Non reproduit (front non servi, voir §4). |
| **B4** | « undefined undefined » dans le champ Adhérent | Capture « Nouvel Affilié » (Santé, DOCUMENTS LE PHARE.docx), ouverture de l'écran sans adhérent chargé. Non reproduit. |
| **B5** | Date de naissance 01/01/1970 | Capture « Mouvement police n°1186119263198N » (IA) : date vide convertie en date epoch. Non reproduit. |
| **B6** | Erreur HTTP 500 à la création d'un client en doublon | `POST /api/client/` deux fois avec la même `CniPat` → `IntegrityError` (contrainte `cle_unique`) renvoyée en page d'erreur 500 au lieu d'un message de validation. |
| **B7** | Suppression physique d'un client | `DELETE /api/client/{id}/` → HTTP 204, ligne supprimée de `stdclient`. |
| **B8** | TTC incohérente acceptée en prime imposée | `CALL sp_maj_manuelle_primes(numero, 200000, 100000, 5000, 15225, 2000, 1000, 999999)` → TTC stockée 999 999 pour 122 225 de composantes. |
| **B9** | Devis enregistrés à primes nulles | Devis Auto NSIA offre 149 (ex. 25191, 24994, 24918, 24917) : PN, taxe, accessoire et TTC à 0 ; propositions IA à 0 FCFA dans les exemples fournis. |
| **B10** | Valeur « RAS » dans le numéro de police compagnie | L'écran Uranus envoie `NumeroPoliceCompagnie: "RAS"` quand le champ est vide ; la valeur est ensuite imprimée comme un vrai numéro. |
| **B11** | Détail de devis sans prime | Plusieurs devis (ex. 6272, 6253, 5799) ont `stddevisdetail.primenette = 0` alors que `stddevis.primenette` est renseignée. |

---

## 7. Tableau de couverture fonctionnelle (étapes 2 et 6)

Légende : ✅ implémentée et vérifiée en exécution · ⚠️ implémentée mais écart runtime/specs · ❌ absente du code · ❓ non testable en l'état.

### 7.1 Exigences issues des documents OREOLE (besoins prioritaires)

| Fonctionnalité | Statut | Source | Référence code | Vérifié en exécution ? | Commentaire |
|---|---|---|---|---|---|
| Création client personne physique / morale | ✅ | Creation et gestion des clients §Création ; captures | `customer/views.py` `ClientViewSet` | Oui (POST 201) | Champs `Vip` et `CreeCie` obligatoires côté API. |
| Création client en cours de saisie de police | ❓ | idem ; compte rendu 09/09 | Front `ClientRegistration.jsx` | Non (front non servi) | Présent dans les captures. |
| Identifiant client unique / regroupement des doublons | ⚠️ | idem §Gestion des doublons | `stdclient.cle_unique`, `production/anti_doublons/` | Oui | Clé = CNI exacte ou nom normalisé ; pas de regroupement de fiches existantes. |
| Prévention des doublons au-delà du nom exact | ❌ | idem §Prévention | — | Oui | Variante de nom acceptée ; CNI en double → HTTP 500 (B6). |
| Vue consolidée du client | ❓ | idem §Situation globale | — | Non | Non identifiée dans l'API Uranus. |
| Auto : choix Mono / Flotte en premier | ✅ | idem §Risque automobile ; captures | `ClientRegistration.jsx` (`Flotte`) | Oui (mono via API) | |
| Auto : offre → garanties et primes | ⚠️ | idem | `fn_garantie_offre` | Oui | Ligne « CUMUL » dans la liste ; primes non reproductibles sur les devis historiques. |
| Auto : écarts de prime / prime imposée traçable | ⚠️ | idem §Gestion des écarts | `sp_maj_manuelle_primes`, `correctiondevis` | Oui | Aucun contrôle de cohérence (B8) ; drapeau `primeimposee` seul comme trace. |
| Auto : compagnies sans tarif (saisie directe) | ⚠️ | idem | `sp_calcul_devis_prime_imposee` | Partiel | Même absence de contrôle. |
| Auto flotte : saisie progressive, reprise ultérieure | ❓ | idem §Contrats Flotte | `enregistrementdevis` + `finalisationdevisauto` | Non | Le code permet d'enregistrer véhicule par véhicule avant finalisation ; pas d'état « en cours de saisie » explicite. |
| Auto flotte : mouvements retrait / incorporation | ✅ | DOCUMENT PROJET §Production auto | `sp_avenant_retrait`, `sp_avenant_incorporation` | Non | Présents dans la liste des mouvements (captures). |
| IA : catégorie, capitaux, qualité, durée | ✅ | idem §IA | `fn_garantie_offre_ia`, `sp_creation_devis_ia` | Non (lecture) | |
| IA : ayants droit et contrôle des pourcentages | ⚠️ | idem | `sp_saisie_ayant_droit_ia` | Non | Annexe réelle à 3 × 33 % = 99 %. |
| IA : contrat groupe souscripteur → assurés → ayants droit | ✅ | idem | `sp_enregistrement_assure_ia` | Non | |
| IA : import Excel avec contrôle des erreurs | ⚠️ | idem §Importation | `production/import_assures.py`, `anti_doublons/importateur.py` | Non | Détection de fichier déjà importé par empreinte. |
| IA : produit à import direct | ❓ | idem | `sp_creation_devis_ia` (tarifs CGA/CI-ENERGIES codés en dur) | Non | |
| Transport : import GUCE bimensuel, contrôle, restitution contractée | ⚠️ | idem §Transports ; README front | `sp_generation_contrat_transport`, `sp_generation_quittance_transport` | Non | Le README Uranus liste « Retester l'importation des fichiers » ; aucun taux de taxe Transport en base. |
| Voyage : prime automatique selon assuré, destination, durée | ⚠️ | idem §Voyage | `fn_calcul_prime_voyage_by_age_*` | Oui | Tarif obsolète (écart ×2 sur l'exemple). |
| Voyage : tarifs NSIA / AMSA à jour | ❌ | compte rendu 09/09 | `StdZoneVoyagePrime` | Oui | Grille non mise à jour. |
| Codes catégorie | ⚠️ | OREOLE_Codes_Categorie_Numerotation | `stdcategorie` | Oui | Facultés terrestres : **614** dans le document, **618** en base. |
| Numérotation police / devis | ⚠️ | idem | `sp_generer_numero_*` | Oui | Voir §5. |
| Santé MINENE | ⚠️ | TARIFICATION MINENE SANTE.xlsx | `sp_finalisation_devis` (offre 66), `fn_get_*_minene` | Non | Taxe en montant fixe codé en dur (2 976 × adhérents). |
| MRH | ⚠️ | README front (« revisiter totalement ») | `mrh_calcul_service.py` | Non | Paramétrage déclaré non conforme par l'éditeur ; taxe non recalculée après répartition manuelle. |
| RC hors chef de famille | ❌ | README front | — | — | « Paramétrer les autres RC » non fait. |
| Mode de règlement, statuts bancaires, état des primes à reverser | ⚠️ | Exploration_de_Le_Phare | `encaissement`, `reversement`, `cheque` | Non | Encaissement/reversement/chèques présents ; statuts demandés à confirmer. |
| États décisionnels (bordereau des émissions) | ✅ | ETATS DECISIONNEL.pdf | `reporting` `EtatDecisionnelViewSet` | Non | Exemple réel fourni ; plusieurs lignes où PN + Acc + Taxe ≠ TTC (ex. 14 524 + 6 000 + 2 976 = 23 500 ≠ 25 000). |
| Archivage sans suppression | ⚠️ | Spec V3 C4, règles transverses | `sp_archivage_devis` (drapeau) | Oui | Devis archivés logiquement, mais clients et devis MRH supprimables (B7). |

### 7.2 Spécification V3 (écrans A à L)

| Module / écrans | Statut | Source | Référence code | Vérifié en exécution ? | Commentaire |
|---|---|---|---|---|---|
| A1 Connexion | ⚠️ | Spec V3 A1 | `account` (`users/login`, Knox) | Oui (jeton) | Pas de blocage après N tentatives, pas de MFA, pas de journal des connexions. |
| A2–A5 Rôles, accueil, profil, aide | ❓ | A2–A5 | `account`, `autorisations` | Non | Changement de mot de passe présent ; le reste n'a pas été identifié. |
| B1–B4 Cockpits DG / commercial / finance / sinistres | ❌ | B1–B4 | — | — | Seul le reporting par états existe. |
| C1–C3, C8 Leads, fiches prospects, pipeline, campagnes | ❌ | C1–C3, C8 | — | — | Aucune trace dans le code. |
| C4 Fiche client 360° | ⚠️ | C4 | `customer` | Partiel | Fiche client simple ; pas de vue 360°. |
| C5–C7 Contacts, interactions, réclamations | ❌ | C5–C7 | — | — | |
| D1–D2 Qualification, comparateur multi-compagnies | ❌ | D1–D2 | — | — | |
| D3 Écran de devis | ⚠️ | D3 | `production` | Oui | Pas de versionnement ; prime non reproductible sur l'historique. |
| D4 Proposition commerciale | ⚠️ | D4 | Documents PDF front | Oui (fonctions) | Montant en lettres défaillant (B1). |
| D5–D6 Dossier de souscription, file back-office | ❌ | D5–D6 | — | — | |
| D7 Émission police / attestation | ⚠️ | D7 | `sp_confirmation_devis`, `asaci` | Partiel | Numéro de police non garanti unique en concurrence ; ASACI non testé (service externe neutralisé). |
| D8 Refus / affaires perdues | ❌ | D8 | — | — | |
| E1–E3 Portefeuille, fiche contrat, avenants | ⚠️ | E1–E3 | `stdcontrat`, `sp_avenant_*` | Non | Avenants présents ; recalcul automatique des échéances non vérifié. |
| E4 Renouvellements | ✅ | E4 | `sp_avenant_renouvellement` | Non | |
| E5 Résiliations / suspensions | ⚠️ | E5 | Mouvements `RESILIATION`, `SUSPENSION` | Non | Calcul de ristourne non identifié. |
| E6 Portefeuille groupe (flottes, collectifs) | ⚠️ | E6 | Flotte, IA groupe, santé | Non | |
| E7 Extranet client | ❌ | E7 | — | — | |
| F1 Journal des encaissements | ✅ | F1 | `sp_enregistrement_encaissement`, `sp_annulation_encaissement` | Non | Annulation par écriture inverse. |
| F2 Import bancaire | ❌ | F2 | — | — | |
| F3 Échéancier / impayés | ❓ | F3 | — | Non | |
| F4 Bordereaux de reversement | ✅ | F4 | `sp_enregistrement_reversement`, `sp_validation_reversement` | Non | |
| F5 Rapprochement compagnie | ❌ | F5 | — | — | |
| F6 Caisse / guichet | ⚠️ | F6 | `caisse`, `cheques` | Non | |
| F7 Validation financière | ⚠️ | F7 | `autorisations` (demandes, jetons) | Non | |
| G1–G3 Barèmes, calcul, bordereau de commissions | ⚠️ | G1–G3 | `commissions`, `fn_get_taux_commission` | Oui (calcul) | Assiette incluant la CEDEAO. |
| G4–G6 Rétrocessions, participation bénéficiaire, portail partenaires | ❌ | G4–G6 | — | — | |
| H1–H10 Sinistres délégués | ❌ | H1–H10 | Menu « Sinistres » sans back-end | — | |
| I1 Compagnies | ✅ | I1 | `compagnie` | Oui (GET 200) | |
| I2–I5 Conventions, catalogue, matrice, obligations | ❌ | I2–I5 | Offres/tarifs uniquement | — | |
| J1 GED | ⚠️ | J1 | `piece_jointe` (devis) | Non | Pièce jointe unique par devis, sans versionnement. |
| J2 Générateur de documents | ⚠️ | J2 | PDF front | Oui (fonctions) | B1, B2. |
| J3–J4 Tâches/workflows, journal des envois | ❌ | J3–J4 | — | — | SMS présents (`messaging`) sans journal consultable identifié. |
| K1, K3, K5 Conformité, contrôle interne, risques | ❌ | K1, K3, K5 | — | — | |
| K2 Journal d'audit | ❌ | K2 | `auditlog` commenté | — | Désactivé dans le code. |
| K4 Reporting réglementaire / états | ⚠️ | K4 | `reporting` | Non | États non figés/rejouables. |
| L1 Utilisateurs et habilitations | ⚠️ | L1 | `account`, `autorisations` | Oui (création) | |
| L2 Référentiels | ✅ | L2 | `configuration_api` | Oui | Désactivation logique non systématique. |
| L3–L5 Workflows, intégrations, supervision | ❌ | L3–L5 | — | — | Intégrations configurées dans `.env` uniquement. |

---

## 8. Points à clarifier avec l'équipe métier (par priorité)

1. **Règle officielle de la Prime TTC Auto** : la CEDEAO et le FGA font-ils partie de la « prime nette » affichée ? Quelle formule doit faire foi quand la prime est imposée ? (47 devis incohérents aujourd'hui.)
2. **Prime imposée** : quels contrôles exiger (somme des composantes = TTC, écart maximal toléré, justificatif, validation hiérarchique) ?
3. **Arrondi NSIA au multiple de 5** : toujours en vigueur ? Pour les autres compagnies ?
4. **Tarifs Voyage** : date d'effet des nouveaux tarifs NSIA/AMSA et règle à appliquer aux productions en attente de saisie.
5. **Assiette de commission** : la CEDEAO (et le FGA) doivent-ils être exclus ?
6. **Numérotation** : la « clé » doit-elle être une vraie clé de contrôle ? L'année doit-elle être celle de l'effet/souscription ou de l'émission ? Nomenclature unique pour les factures devis/contrat ?
7. **Code catégorie Facultés terrestres** : 614 (document) ou 618 (base) ?
8. **Taxes** : confirmer 25 % MRH incendie/dommages électriques, 8 % santé, taux Transport (non paramétré), taxe fixe MINENE 2 976.
9. **Dédoublonnage client** : critères de rapprochement attendus (téléphone, CNI, RCCM, nom approchant) et règle de fusion des fiches historiques.
10. **Suppression** : quels objets peuvent être supprimés physiquement (devis brouillon ?) et lesquels uniquement archivés ?
11. **IA** : règle de prorata affichée sur les quittances et gestion des parts d'ayants droit non entières (33/33/33).
12. **Périmètre** : confirmer que les modules V3 absents d'Uranus (CRM, sinistres délégués, rétrocessions, rapprochement, journal d'audit) sont bien à construire dans LE PHARE, et dans quel lot.

---

## Annexe — Impact sur LE PHARE et éléments de preuve

**Corrections apportées à LE PHARE pendant l'audit** (code ajouté dans cette même session) :
- Endpoint `GET /api/devis/{id}/conditions-particulieres/` : jointure corrigée vers `stdsousgarantie`. `stddevisdetgarantie.idgarantie` référence une sous-garantie ; la jointure vers `stdgarantie` affichait de mauvais libellés (ex. « DOMMAGE » au lieu de « CEDEAO ») et omettait certaines garanties.
- Facture proforma et Conditions Particulières : prise en compte du modèle Uranus (FGA et, selon le parcours, CEDEAO déjà inclus dans la prime nette stockée ; arrondi NSIA accepté). Rendu vérifié sur les 311 devis Auto des 12 derniers mois : 0 valeur technique non résolue, 0 montant en lettres manquant, alerte d'écart sur les 47 devis réellement incohérents.

**Éléments de preuve** (répertoire de travail de l'audit, hors dépôt) : textes extraits des documents, 244 routines SQL extraites, sources front reconstituées, scripts `test_calculs_auto.py`, `test_devis_auto_e2e.py`, `uranus_lettres.js` et leurs sorties.

**Environnement d'exécution** : la base locale `uranus_audit` (copie de la sauvegarde *testing*) et le serveur Uranus utilisés pour les tests ont été supprimés après l'audit ; les scripts permettent de reconstituer l'environnement (restauration de la sauvegarde, `.env` d'audit, `manage.py runserver 127.0.0.1:8001`).
