"""
Consommations MINENE Santé (demande du 2026-11-19 : « comme en Oreole Santé, en MINENE Santé il y a un fichier de consommation à importer ;
le système doit faire les différentes statistiques avec plus de détail »).

Le gestionnaire (MCI) remet le détail des sinistres MINENE en états personnalisés (feuille ETATS PERSONNALISES, garant OREOLEMINENE) :
une ligne par prestation, tiers payant (TP) ou remboursement direct (RD), avec le type d'affection. L'import est celui des consommations
(sante/consommations.py, format reconnu à la colonne NPrestations). Ici, l'analyse des prestations MINENE :
- indicateurs, mois, mode de prise en charge (TP / RD), familles de prestations, types d'affection, profil (statut, sexe, âge) ;
- familles (assuré principal), rattachées à la police MINENE de LE PHARE par le matricule du gestionnaire porté par chaque personne
  (stdaffilie.matricule) : formule SOLO / FAMILLE / FAMILLE PLUS et prime nette annuelle de la formule (lephare_sante_formule.primebase) ;
  taux de consommation = remboursé / prime acquise sur les mois couverts (prime annuelle x mois / 12), projection sur 12 mois ;
- portefeuille MINENE de LE PHARE (familles en vigueur) : primes acquises face aux remboursements, par formule ;
- centres exécutants et communes, médecins, actes, délais des soins à la clôture ;
- anomalies : règles F01 à F10 des consommations (detecter_fraude) sur les seules prestations MINENE.

GET /api/consommations/minene/?du&au&police : rien n'est écrit (droit consommations.view par la garde).
"""

from collections import Counter, defaultdict
from decimal import Decimal
from statistics import median

from django.db import connection
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from autorisations.rbac import a_le_droit
from production.minene_package import SQL_MINENE
from production.renouvellement import AUTHENTIFICATION, _lignes

from .consommations import ErreurConsommation, colonnes_detail, detecter_fraude, lire_date

GARANT_MINENE = "OREOLEMINENE"
ID_PRODUIT_SANTE = 5
ZERO = Decimal("0")
TYPES = {"TP": "Tiers payant", "RD": "Remboursement direct", "HO": "Hospitalisation"}
STATUTS = {"A": "Assuré", "C": "Conjoint(e)", "E": "Enfant"}
SEXES = {"F": "Femmes", "M": "Hommes"}
TRANCHES = [(0, 5, "0 à 5 ans"), (6, 17, "6 à 17 ans"), (18, 35, "18 à 35 ans"), (36, 55, "36 à 55 ans"), (56, 200, "56 ans et plus")]
SEUIL_SURVEILLANCE, SEUIL_DEPASSEMENT = Decimal("0.8"), Decimal("1")
TOP = 12


def _n(v):
    return float(v) if v is not None else 0.0


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _age(naissance, jour):
    if not naissance or not jour:
        return None
    return jour.year - naissance.year - ((jour.month, jour.day) < (naissance.month, naissance.day))


def _tranche(age):
    if age is None:
        return "Âge inconnu"
    return next((t for debut, fin, t in TRANCHES if debut <= age <= fin), "Âge inconnu")


def _cumul():
    return {"Prestations": 0, "Reclame": ZERO, "Rembourse": ZERO, "Beneficiaires": set(), "Familles": set()}


def _ajouter(cumul, p):
    cumul["Prestations"] += 1
    cumul["Reclame"] += p["mt_reclame"] or ZERO
    cumul["Rembourse"] += p["mt_rembourse"] or ZERO
    cumul["Beneficiaires"].add(p["matricule_beneficiaire"])
    cumul["Familles"].add(p["matricule_assure"])


def _sortie(cle, libelle, cumul, total_rembourse, **autres):
    rembourse = cumul["Rembourse"]
    return {
        "Code": cle, "Libelle": libelle, "Prestations": cumul["Prestations"], "Beneficiaires": len(cumul["Beneficiaires"]),
        "Familles": len(cumul["Familles"]), "Reclame": _n(cumul["Reclame"]), "Rembourse": _n(rembourse),
        "Part": _n(rembourse / total_rembourse) if total_rembourse else 0.0,
        "CoutMoyen": _n(rembourse / cumul["Prestations"]) if cumul["Prestations"] else 0.0, **autres,
    }


def _repartition(prestations, cle, libelle=lambda c: c or "Non renseigné", total=ZERO, limite=None):
    groupes = defaultdict(_cumul)
    for p in prestations:
        _ajouter(groupes[cle(p)], p)
    lignes = [_sortie(c, libelle(c), g, total) for c, g in groupes.items()]
    lignes.sort(key=lambda l: (-l["Rembourse"], str(l["Libelle"])))
    return lignes[:limite] if limite else lignes


def _situation(taux):
    if taux is None:
        return "SANS_CONTRAT"
    if taux >= SEUIL_DEPASSEMENT:
        return "DEPASSEE"
    if taux >= SEUIL_SURVEILLANCE:
        return "A_SURVEILLER"
    return "NORMALE"


def famille_du_matricule(matricule):
    """Matricule de famille du gestionnaire : celui du membre sans ses deux derniers chiffres (1571000402 -> 15710004 = MatriculeA)."""
    return matricule // 100 if matricule and matricule >= 100 else None


def analyser(prestations, liens, portefeuille, mois_couverts=None):
    """
    Analyse pure des prestations MINENE.
    prestations : lignes de lephare_sante_prestation (date_soins_retenue, montants, matricules, famille, type, type_affection, sexe...) ;
    liens : {matricule_beneficiaire: {"Police", "Formule", "PrimeNette", "IdAdherent", "Famille"}} (personnes des polices MINENE de LE PHARE) ;
      un bénéficiaire sans matricule dans LE PHARE est rattaché par sa famille (matricule assuré = matricule d'un membre sans ses deux
      derniers chiffres) ;
    portefeuille : familles MINENE en vigueur [{"Police", "IdAdherent", "Famille", "Formule", "PrimeNette", "Personnes"}] ;
    mois_couverts : nombre de mois de la période analysée (défaut : mois distincts des soins).
    """
    par_famille_lephare = {}
    for matricule, lien in liens.items():
        par_famille_lephare.setdefault(famille_du_matricule(matricule), lien)

    def lien_de(p):
        return liens.get(p["matricule_beneficiaire"]) or par_famille_lephare.get(p["matricule_assure"])

    total_reclame = sum((p["mt_reclame"] or ZERO for p in prestations), ZERO)
    total = sum((p["mt_rembourse"] or ZERO for p in prestations), ZERO)
    exclusions = sum((p.get("exclusion") or ZERO for p in prestations), ZERO)
    depassements = sum((p.get("depassement") or ZERO for p in prestations), ZERO)
    mois = sorted({p["date_soins_retenue"].strftime("%Y-%m") for p in prestations if p.get("date_soins_retenue")})
    nb_mois = max(1, mois_couverts or len(mois))
    beneficiaires = {p["matricule_beneficiaire"] for p in prestations}
    familles_conso = {p["matricule_assure"] for p in prestations}

    # Mois
    par_mois = defaultdict(_cumul)
    for p in prestations:
        if p.get("date_soins_retenue"):
            _ajouter(par_mois[p["date_soins_retenue"].strftime("%Y-%m")], p)
    serie = [_sortie(m, m, par_mois[m], total) for m in mois]

    # Profil
    def sexe(p):
        return (p.get("sexe") or p.get("genre") or "").strip().upper()[:1]

    profil_age = defaultdict(lambda: {"F": ZERO, "M": ZERO, "Beneficiaires": set()})
    for p in prestations:
        tranche = _tranche(_age(p.get("date_naissance"), p.get("date_soins_retenue")))
        profil_age[tranche][sexe(p) if sexe(p) in ("F", "M") else "F"] += p["mt_rembourse"] or ZERO
        profil_age[tranche]["Beneficiaires"].add(p["matricule_beneficiaire"])
    ordre = [t for _d, _f, t in TRANCHES] + ["Âge inconnu"]
    pyramide = [{"Tranche": t, "Femmes": _n(profil_age[t]["F"]), "Hommes": _n(profil_age[t]["M"]),
                 "Beneficiaires": len(profil_age[t]["Beneficiaires"])} for t in ordre if t in profil_age]

    # Familles (assuré principal) et rattachement à LE PHARE
    par_famille = defaultdict(_cumul)
    noms, polices_mci, membres_lies = {}, {}, defaultdict(set)
    for p in prestations:
        _ajouter(par_famille[p["matricule_assure"]], p)
        noms.setdefault(p["matricule_assure"], p.get("assure") or p.get("souscripteur") or "")
        polices_mci.setdefault(p["matricule_assure"], p.get("police") or "")
        if lien_de(p):
            membres_lies[p["matricule_assure"]].add(p["matricule_beneficiaire"])
    familles = []
    for matricule, g in par_famille.items():
        lien = next((liens.get(m) or par_famille_lephare.get(matricule) for m in membres_lies.get(matricule, ())), None)
        prime = Decimal(str(lien["PrimeNette"])) if lien and lien.get("PrimeNette") else None
        acquise = prime * nb_mois / 12 if prime else None
        taux = g["Rembourse"] / acquise if acquise else None
        familles.append(_sortie(
            matricule, noms.get(matricule) or str(matricule), g, total,
            PoliceGestionnaire=polices_mci.get(matricule, ""), PoliceLePhare=lien["Police"] if lien else "",
            Formule=lien["Formule"] if lien else "", PrimeNette=_n(prime) if prime else None,
            PrimeAcquise=_n(acquise) if acquise else None, Taux=_n(taux) if taux is not None else None,
            Projection=_n(g["Rembourse"] * 12 / nb_mois / prime) if prime else None, Situation=_situation(taux),
        ))
    familles.sort(key=lambda l: (-l["Rembourse"], l["Libelle"]))

    # Portefeuille MINENE de LE PHARE : primes acquises sur la période, consommation des familles rattachées, par formule
    remb_par_adherent = defaultdict(lambda: ZERO)
    for p in prestations:
        lien = lien_de(p)
        if lien:
            remb_par_adherent[lien["IdAdherent"]] += p["mt_rembourse"] or ZERO
    par_formule = defaultdict(lambda: {"Familles": 0, "Personnes": 0, "Primes": ZERO, "Rembourse": ZERO, "Consommatrices": 0})
    for f in portefeuille:
        x = par_formule[f["Formule"] or "Formule inconnue"]
        x["Familles"] += 1
        x["Personnes"] += f.get("Personnes") or 0
        x["Primes"] += Decimal(str(f.get("PrimeNette") or 0))
        rembourse = remb_par_adherent.get(f["IdAdherent"], ZERO)
        x["Rembourse"] += rembourse
        x["Consommatrices"] += 1 if rembourse else 0
    formules = []
    for nom, x in sorted(par_formule.items(), key=lambda kv: -kv[1]["Primes"]):
        acquises = x["Primes"] * nb_mois / 12
        formules.append({
            "Formule": nom, "Familles": x["Familles"], "Personnes": x["Personnes"], "Consommatrices": x["Consommatrices"],
            "PrimesAnnuelles": _n(x["Primes"]), "PrimesAcquises": _n(acquises), "Rembourse": _n(x["Rembourse"]),
            "Taux": _n(x["Rembourse"] / acquises) if acquises else None,
            "CoutMoyenFamille": _n(x["Rembourse"] / x["Familles"]) if x["Familles"] else 0.0,
        })
    primes_annuelles = sum((Decimal(str(f.get("PrimeNette") or 0)) for f in portefeuille), ZERO)
    primes_acquises = primes_annuelles * nb_mois / 12
    rembourse_lie = sum(remb_par_adherent.values(), ZERO)

    # Prestataires et actes
    centres = defaultdict(_cumul)
    localites_centres = {}
    for p in prestations:
        cle = p.get("centre_executant") or "Non renseigné"
        _ajouter(centres[cle], p)
        localites_centres.setdefault(cle, p.get("localite_centre") or "")
    liste_centres = sorted((_sortie(c, c, g, total, Localite=localites_centres.get(c, "")) for c, g in centres.items()),
                           key=lambda l: -l["Rembourse"])
    actes = defaultdict(_cumul)
    libelles_actes = {}
    for p in prestations:
        cle = p.get("code_acte") or p.get("acte") or "Non renseigné"
        _ajouter(actes[cle], p)
        libelles_actes.setdefault(cle, p.get("acte") or cle)
    liste_actes = sorted((_sortie(c, libelles_actes[c], g, total) for c, g in actes.items()), key=lambda l: (-l["Rembourse"], -l["Prestations"]))
    delais = [(p["date_cloture"] - p["date_soins_retenue"]).days for p in prestations
              if p.get("date_cloture") and p.get("date_soins_retenue") and p["date_cloture"] >= p["date_soins_retenue"]]

    # Tableau croisé familles de prestations x mois (chaleur)
    croise = defaultdict(lambda: defaultdict(lambda: ZERO))
    for p in prestations:
        if p.get("date_soins_retenue"):
            croise[p.get("famille") or "Non renseigné"][p["date_soins_retenue"].strftime("%Y-%m")] += p["mt_rembourse"] or ZERO
    chaleur = [{"Libelle": fam, "Valeurs": [_n(v[m]) for m in mois], "Total": _n(sum(v.values(), ZERO))}
               for fam, v in sorted(croise.items(), key=lambda kv: -sum(kv[1].values(), ZERO))]

    # Constats rédigés
    constats = []
    types = _repartition(prestations, lambda p: (p.get("type") or "").upper(), lambda c: TYPES.get(c, c or "Non renseigné"), total)
    affections = _repartition(prestations, lambda p: p.get("type_affection") or "", total=total)
    familles_prest = _repartition(prestations, lambda p: p.get("famille") or "", total=total)
    if familles_prest:
        f = familles_prest[0]
        constats.append(f"{f['Libelle'].capitalize()} : premier poste, {round(f['Part'] * 100)} % des remboursements.")
    if affections and affections[0]["Libelle"] != "Non renseigné":
        a = affections[0]
        constats.append(f"Affection la plus coûteuse : {a['Libelle']}, {round(a['Part'] * 100)} % des remboursements.")
    if total_reclame:
        constats.append(f"Prise en charge : {round(total / total_reclame * 100)} % des montants réclamés, le reste à la charge des assurés.")
    surveillees = [f for f in familles if f["Situation"] in ("DEPASSEE", "A_SURVEILLER")]
    if surveillees:
        constats.append(f"{len(surveillees)} famille(s) à au moins 80 % de leur prime acquise sur la période.")
    sans_contrat = [f for f in familles if f["Situation"] == "SANS_CONTRAT"]
    if sans_contrat:
        constats.append(f"{len(sans_contrat)} famille(s) du relevé sans police MINENE retrouvée dans LE PHARE (matricule du gestionnaire absent des fiches).")
    if familles:
        part_top = sum(f["Rembourse"] for f in familles[:max(1, len(familles) // 5)]) / _n(total) if total else 0
        constats.append(f"Les 20 % de familles les plus consommatrices pèsent {round(part_top * 100)} % des remboursements.")

    return {
        "Periode": {"Mois": mois, "NombreMois": nb_mois,
                    "Du": _iso(min((p["date_soins_retenue"] for p in prestations if p.get("date_soins_retenue")), default=None)),
                    "Au": _iso(max((p["date_soins_retenue"] for p in prestations if p.get("date_soins_retenue")), default=None))},
        "Indicateurs": {
            "Prestations": len(prestations), "Beneficiaires": len(beneficiaires), "Familles": len(familles_conso),
            "Reclame": _n(total_reclame), "Rembourse": _n(total), "PartAssures": _n(total_reclame - total), "Exclusions": _n(exclusions),
            "Depassements": _n(depassements), "TauxPriseEnCharge": _n(total / total_reclame) if total_reclame else None,
            "CoutMoyenPrestation": _n(total / len(prestations)) if prestations else 0.0,
            "CoutMoyenBeneficiaire": _n(total / len(beneficiaires)) if beneficiaires else 0.0,
            "FamillesPortefeuille": len(portefeuille), "PersonnesPortefeuille": sum(f.get("Personnes") or 0 for f in portefeuille),
            "PrimesAnnuelles": _n(primes_annuelles), "PrimesAcquises": _n(primes_acquises), "RembourseRattache": _n(rembourse_lie),
            "TauxConsommation": _n(rembourse_lie / primes_acquises) if primes_acquises else None,
            "TauxFrequence": _n(Decimal(len(beneficiaires)) / Decimal(sum(f.get("Personnes") or 0 for f in portefeuille)))
            if sum(f.get("Personnes") or 0 for f in portefeuille) else None,
            "DelaiMedian": median(delais) if delais else None,
        },
        "ParMois": serie,
        "ParType": types,
        "ParFamillePrestation": familles_prest,
        "ParAffection": affections,
        "ParStatut": _repartition(prestations, lambda p: (p.get("statut") or "").upper(), lambda c: STATUTS.get(c, "Non renseigné"), total),
        "ParSexe": _repartition(prestations, sexe, lambda c: SEXES.get(c, "Non renseigné"), total),
        "Pyramide": pyramide,
        "Familles": familles,
        "Formules": formules,
        "Centres": liste_centres[:TOP],
        "Localites": _repartition(prestations, lambda p: p.get("localite_centre") or "", total=total, limite=TOP),
        "Medecins": _repartition(prestations, lambda p: p.get("medecin") or "", total=total, limite=TOP),
        "Actes": liste_actes[:15],
        "Chaleur": {"Mois": mois, "Lignes": chaleur},
        "Constats": constats,
    }


# ------------------------------------------------------------------ base
def _prestations(cursor, params):
    detail = colonnes_detail(cursor)
    condition, valeurs = ["p.garant = %s"], [GARANT_MINENE]
    for cle, op in (("du", ">="), ("au", "<=")):
        jour = lire_date(params.get(cle))
        if jour:
            condition.append(f"p.date_soins_retenue {op} %s")
            valeurs.append(jour)
    police = str(params.get("police") or "").strip()
    if police:
        condition.append("(p.police = %s OR p.npol::text = %s)")
        valeurs += [police, police]
    lignes = _lignes(cursor, f"""
        SELECT p.*, e.genre, e.date_effet, e.actif AS actif_effectif, e.date_sortie, e.statut AS statut_effectif,
               (e.matricule_beneficiaire IS NOT NULL) AS dans_effectif, '' AS bareme
        FROM lephare_sante_prestation p
        LEFT JOIN lephare_sante_effectif e ON e.matricule_beneficiaire = p.matricule_beneficiaire AND e.garant = '{GARANT_MINENE}'
        WHERE {' AND '.join(condition)}
        ORDER BY p.date_soins_retenue, p.numero_prest""", valeurs)
    for p in lignes:
        for champ in ("type_affection", "code_affection", "code_acte", "sexe", "localite_centre"):
            if champ not in detail:
                p.setdefault(champ, None)
        # Sexe du relevé MINENE à défaut de l'effectif (règle F05 des anomalies)
        p["genre"] = (p.get("genre") or p.get("sexe") or "").strip()
    return lignes


SQL_LIENS = f"""
    SELECT DISTINCT ON (x.matricule) x.matricule, x.police, x.formule, x.primebase, x.idadherent, x.famille
    FROM (
        SELECT CASE WHEN TRIM(af.matricule) ~ '^[0-9]{{1,18}}$' THEN TRIM(af.matricule)::bigint END AS matricule, c.numeropolice AS police,
               COALESCE(NULLIF(TRIM(sf.option), ''), TRIM(o.libelleoffre)) AS formule, sf.primebase, h.idadherent, c.idcontrat,
               TRIM(COALESCE(h.nom, '') || ' ' || COALESCE(h.prenom, '')) AS famille
        FROM stdaffilie af
        JOIN stdcontrat c ON c.iddevis = af.iddevis AND c.idproduit = {ID_PRODUIT_SANTE} AND COALESCE(c.idcontratannulation, 0) = 0
        JOIN stddevis d ON d.iddevis = c.iddevis
        LEFT JOIN stdadherent h ON h.idadherent = af.idadherent
        LEFT JOIN stdfiliale f ON f.idfiliale = h.idfiliale
        LEFT JOIN stdoffre o ON o.idoffre = f.idoffresante
        LEFT JOIN lephare_sante_formule sf ON sf.idoffre = f.idoffresante
        WHERE {SQL_MINENE}
    ) x
    WHERE x.matricule = ANY(%s) OR x.matricule / 100 = ANY(%s)
    ORDER BY x.matricule, x.idcontrat DESC
"""

# Familles MINENE en vigueur : composition du dernier contrat émis de chaque police qui porte des familles (affaire nouvelle, renouvellement,
# avenants de modification), comme sp_avenant_creation_devis_initial v7 ; familles actives non sorties
SQL_PORTEFEUILLE = f"""
    WITH dernier AS (
        SELECT DISTINCT ON (c.numeropolice) c.numeropolice, c.iddevis, c.dateexpiration::date AS echeance
        FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant JOIN stddevis d ON d.iddevis = c.iddevis
        WHERE c.idproduit = {ID_PRODUIT_SANTE} AND COALESCE(c.idcontratannulation, 0) = 0 AND a.codeavenant IN ('AFN', 'REN', 'RPP', 'TRP', 'MOD')
          AND {SQL_MINENE} AND EXISTS (SELECT 1 FROM stdadherent ad WHERE ad.iddevis = c.iddevis)
          AND NOT EXISTS (SELECT 1 FROM stdcontrat r JOIN stdavenant ar ON ar.idavenant = r.idavenant
                          WHERE r.numeropolice = c.numeropolice AND ar.codeavenant = 'RES' AND r.dateeffet::date <= CURRENT_DATE)
        ORDER BY c.numeropolice, c.idcontrat DESC)
    SELECT dn.numeropolice AS police, h.idadherent, TRIM(COALESCE(h.nom, '') || ' ' || COALESCE(h.prenom, '')) AS famille,
           COALESCE(NULLIF(TRIM(sf.option), ''), TRIM(o.libelleoffre)) AS formule, sf.primebase,
           (SELECT COUNT(*) FROM stdaffilie x WHERE x.idadherent = h.idadherent AND COALESCE(x.actif, TRUE)
              AND (x.datesortie IS NULL OR x.datesortie > CURRENT_DATE)) AS personnes,
           -- Matricules du gestionnaire des membres : lien avec les prestations (chaque avenant recopie les familles sous d'autres identifiants)
           ARRAY(SELECT TRIM(x.matricule)::bigint FROM stdaffilie x
                 WHERE x.idadherent = h.idadherent AND TRIM(COALESCE(x.matricule, '')) ~ '^[0-9]{{1,18}}$') AS matricules
    FROM dernier dn
    JOIN stdadherent h ON h.iddevis = dn.iddevis AND COALESCE(h.actif, TRUE) AND (h.datesortie IS NULL OR h.datesortie > CURRENT_DATE)
    LEFT JOIN stdfiliale f ON f.idfiliale = h.idfiliale
    LEFT JOIN stdoffre o ON o.idoffre = f.idoffresante
    LEFT JOIN lephare_sante_formule sf ON sf.idoffre = f.idoffresante
    WHERE dn.echeance >= CURRENT_DATE - 365
"""


def _anomalies(prestations):
    """Règles F01 à F10 des consommations sur les seules prestations MINENE : bénéficiaires signalés, par niveau, et règles déclenchées."""
    if not prestations:
        return {"Signales": 0, "Niveaux": {}, "Regles": [], "Beneficiaires": []}
    signaux, scores = detecter_fraude(prestations)
    regles = Counter(s["Regle"] for s in signaux)
    liste = sorted(scores.values(), key=lambda x: (-x["Score"], -x["Montant"]))
    return {
        "Signales": len(scores), "Niveaux": dict(Counter(x["Niveau"] for x in scores.values())),
        "Regles": [{"Regle": r, "Signaux": n} for r, n in regles.most_common()],
        "Beneficiaires": [{k: x.get(k) for k in ("MatriculeBeneficiaire", "Beneficiaire", "Police", "Score", "Niveau", "Montant", "Regles")}
                          for x in liste[:15]],
    }


def analyse(params):
    with connection.cursor() as cursor:
        prestations = _prestations(cursor, params)
        portefeuille = [{"Police": l["police"], "IdAdherent": l["idadherent"], "Famille": l["famille"], "Formule": l["formule"] or "",
                         "PrimeNette": l["primebase"], "Personnes": l["personnes"], "Matricules": [m for m in (l["matricules"] or []) if m]}
                        for l in _lignes(cursor, SQL_PORTEFEUILLE)]
        # Lien d'abord par la composition en vigueur (famille du portefeuille), sinon par le dernier contrat MINENE portant la personne
        liens = {m: {"Police": f["Police"], "Formule": f["Formule"], "PrimeNette": f["PrimeNette"], "IdAdherent": f["IdAdherent"], "Famille": f["Famille"]}
                 for f in portefeuille for m in f["Matricules"]}
        connues = {famille_du_matricule(m) for m in liens}
        matricules = sorted({p["matricule_beneficiaire"] for p in prestations if p["matricule_beneficiaire"]} - set(liens))
        familles = sorted({p["matricule_assure"] for p in prestations if p["matricule_assure"]} - connues)
        if matricules or familles:
            for l in _lignes(cursor, SQL_LIENS, [matricules, familles]):
                liens.setdefault(l["matricule"], {"Police": l["police"], "Formule": l["formule"] or "", "PrimeNette": l["primebase"],
                                                  "IdAdherent": l["idadherent"], "Famille": l["famille"]})
        polices = [l["police"] for l in _lignes(cursor, """SELECT DISTINCT police FROM lephare_sante_prestation WHERE garant = %s AND police <> ''
                                                          ORDER BY 1""", [GARANT_MINENE])]
        releves = _lignes(cursor, """SELECT r.idreleve, r.fichier, r.dateimport, r.cloture_du, r.cloture_au, r.lignes, r.nouvelles
                                     FROM lephare_sante_releve r WHERE r.garants LIKE %s ORDER BY r.idreleve DESC LIMIT 12""", [f"%{GARANT_MINENE}%"])
    du, au = lire_date(params.get("du")), lire_date(params.get("au"))
    mois = None
    if du and au and au >= du:
        mois = (au.year - du.year) * 12 + au.month - du.month + 1
    resultat = analyser(prestations, liens, portefeuille, mois)
    resultat["Anomalies"] = _anomalies(prestations)
    resultat["Filtres"] = {"Polices": polices}
    resultat["Releves"] = [{"Id": r["idreleve"], "Fichier": r["fichier"], "Date": _iso(r["dateimport"]), "ClotureDu": _iso(r["cloture_du"]),
                            "ClotureAu": _iso(r["cloture_au"]), "Lignes": r["lignes"], "Nouvelles": r["nouvelles"]} for r in releves]
    resultat["DetailDisponible"] = bool(prestations) and any(p.get("type_affection") for p in prestations)
    return resultat


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_minene(request):
    try:
        resultat = analyse(request.query_params)
        # Comme la fiche famille : les anomalies (bénéficiaires, scores, niveaux) ne se lisent qu'avec le droit de la détection
        if not a_le_droit(request.user, "consommations.fraude"):
            resultat["Anomalies"] = None
        return Response(resultat)
    except ErreurConsommation as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
