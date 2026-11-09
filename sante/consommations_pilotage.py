"""
Consommations santé : tableau de bord et analyse des dépenses (demande du 2026-11-06 : « un tableau de bord spécial pour suivre les états de
consommation avec ces détails ; matérialiser dans l'application les besoins auxquels les fichiers répondent »).

Ce que les fichiers d'OREOLE calculent, refait ici sur les données importées :
- ETAT 2026, feuille CONTRÔLE DE GESTION : par entreprise, provision pour paiement des dépenses de santé face à la consommation, reste et
  couverture (provision / consommation), totaux (primes HT, cotisation santé pure, honoraires MCI, commissions, apporteurs) ;
- ETAT FINANCIER : consommation mois par mois et par entreprise ;
- RAPPORT OREOLE SANTE 2026 : effectifs (statut, tranche d'âge, anomalies), dépenses (mois, entreprise, famille, statut, âge, centres, médecins),
  entreprises à risque (score et alertes) et fiche de chaque entreprise à risque (production du rapport Word : consommations_rapport.py).
Mois et période : date de clôture du relevé (mois où la dépense est payée). Âge : à la fin de la période.
Lien entreprise de l'état / police du gestionnaire : confirmé par l'utilisateur, sinon proposé d'après les noms (mots rares d'abord).
Score de risque (critères du rapport modèle) : moyenne des rapports à la moyenne du portefeuille du coût par bénéficiaire, des actes par
bénéficiaire et du coût par acte ; « Critique » dès que le score atteint 1 (consigne du 2026-11-09), « Trop d'actes » au-delà de 10 actes par bénéficiaire, « Coût par acte élevé »
au-delà de 30 % de la moyenne. Formule proposée, à valider (le modèle ne la décrit pas).
"""

import datetime as dt
import re
from collections import Counter, defaultdict
from decimal import Decimal

from django.db import connection, transaction
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from production.renouvellement import AUTHENTIFICATION, _lignes

from .consommations import ErreurConsommation, SEUIL_ALERTE_PROVISION, _iso, _nombre, _reponse, lire_date, normaliser

ZERO = Decimal("0")
MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
TRANCHES = [(0, 7, "0-7 ans"), (8, 11, "8-11 ans"), (12, 15, "12-15 ans"), (16, 18, "16-18 ans"), (19, 21, "19-21 ans"), (22, 25, "22-25 ans"),
            (26, 30, "26-30 ans"), (31, 40, "31-40 ans"), (41, 55, "41-55 ans"), (56, 200, "56 et plus")]
STATUTS = {"A": "Assuré principal", "C": "Conjoint", "E": "Enfant"}
GENRES = {"M": "Masculin", "F": "Féminin"}
GENERIQUES = {"POUR", "COMPTE", "SARL", "SA", "ET", "DE", "DU", "LES", "LA", "LE", "DES", "EN"}
SEUIL_ACTES = 10
SEUIL_SCORE_CRITIQUE = 1
SEUIL_COUT_ACTE = Decimal("1.3")


# ------------------------------------------------------------------ outils
def _age(naissance, jour):
    if not naissance or not jour:
        return None
    return jour.year - naissance.year - ((jour.month, jour.day) < (naissance.month, naissance.day))


def tranche(age):
    if age is None:
        return "Non renseigné"
    return next((libelle for bas, haut, libelle in TRANCHES if bas <= age <= haut), "Non renseigné")


def _div(a, b):
    return float(a) / float(b) if b else None


def _mots(texte):
    return {m for m in re.split(r"[^A-Z0-9]+", normaliser(texte)) if len(m) > 1 and m not in GENERIQUES}


def proposer_liens(entreprises, polices, confirmes):
    """Police proposée pour chaque entreprise d'après les noms : mots rares d'abord, un mot de plus pénalise un peu, nom identique gagne ;
    une police ne sert qu'une fois, les liens confirmés passent avant. Égalité ou rapprochement trop faible : aucune proposition."""
    df = Counter(m for p in polices for m in _mots(p))
    prises = {p for p in confirmes.values() if p}
    candidats = []
    for e in entreprises:
        if e in confirmes:
            continue
        notes = []
        for p in polices:
            if normaliser(e) == normaliser(p):
                notes.append((100.0, p))
                continue
            commun = _mots(e) & _mots(p)
            if commun:
                notes.append((sum(1 / df[m] for m in commun) / (1 + 0.1 * len(_mots(p) - _mots(e))), p))
        notes.sort(reverse=True)
        if notes and notes[0][0] >= 0.5 and not (len(notes) > 1 and abs(notes[0][0] - notes[1][0]) < 1e-9):
            candidats.append((notes[0][0], e, notes[0][1]))
    propositions = {}
    for _note, e, p in sorted(candidats, reverse=True):
        if p not in prises:
            propositions[e] = p
            prises.add(p)
    return propositions


# ------------------------------------------------------------------ données de la période
def _periode(cursor, params):
    """Exercice et période : du/au donnés, sinon l'exercice entier (dernier exercice des relevés ou des cotisations)."""
    cursor.execute("""SELECT DISTINCT a FROM (SELECT EXTRACT(YEAR FROM date_cloture)::int AS a FROM lephare_sante_prestation
                      UNION SELECT exercice FROM lephare_sante_cotisation) x WHERE a IS NOT NULL ORDER BY a""")
    exercices = [r[0] for r in cursor.fetchall()]
    try:
        exercice = int(params.get("exercice") or 0) or (exercices[-1] if exercices else dt.date.today().year)
    except (TypeError, ValueError):
        raise ErreurConsommation("Exercice illisible.")
    du = lire_date(params.get("du")) or dt.date(exercice, 1, 1)
    au = lire_date(params.get("au")) or dt.date(exercice, 12, 31)
    if au < du:
        raise ErreurConsommation("La fin de la période précède son début.")
    return exercice, du, au, exercices


def charger(cursor, du, au, garant=""):
    condition, valeurs = "p.date_cloture BETWEEN %s AND %s", [du, au]
    if garant:
        condition += " AND p.garant = %s"
        valeurs.append(garant)
    prestations = _lignes(cursor, f"""
        SELECT p.numero_prest, p.date_cloture, p.garant, p.police, p.matricule_beneficiaire, p.beneficiaire, p.matricule_assure, p.assure, p.statut,
               COALESCE(p.date_naissance, e.date_naissance) AS date_naissance, COALESCE(NULLIF(e.genre, ''), '') AS genre, p.famille, p.acte,
               p.centre_prescripteur, p.centre_executant, p.medecin, p.souscripteur, p.mt_reclame, p.mt_rembourse
        FROM lephare_sante_prestation p LEFT JOIN lephare_sante_effectif e ON e.matricule_beneficiaire = p.matricule_beneficiaire
        WHERE {condition}""", valeurs)
    cond_eff, val_eff = "TRUE", []
    if garant:
        cond_eff, val_eff = "garant = %s", [garant]
    effectif = _lignes(cursor, f"SELECT * FROM lephare_sante_effectif WHERE {cond_eff}", val_eff)
    return prestations, effectif


def repartition(prestations, cle):
    """Dépenses, % et actes par valeur de cle(p), avec coût moyen par acte, triées par dépenses."""
    groupes = defaultdict(lambda: {"Depenses": ZERO, "Actes": 0, "Beneficiaires": set(), "Reclame": ZERO})
    for p in prestations:
        g = groupes[cle(p)]
        g["Depenses"] += p["mt_rembourse"]
        g["Reclame"] += p["mt_reclame"]
        g["Actes"] += 1
        g["Beneficiaires"].add(p["matricule_beneficiaire"])
    total = sum((g["Depenses"] for g in groupes.values()), ZERO)
    actes = sum(g["Actes"] for g in groupes.values())
    return [{"Libelle": k or "Non renseigné", "Depenses": _nombre(g["Depenses"]), "Part": _div(g["Depenses"], total) or 0, "Actes": g["Actes"],
             "PartActes": _div(g["Actes"], actes) or 0, "CoutParActe": _div(g["Depenses"], g["Actes"]), "Beneficiaires": len(g["Beneficiaires"]),
             "Reclame": _nombre(g["Reclame"])}
            for k, g in sorted(groupes.items(), key=lambda kv: -kv[1]["Depenses"])]


def indicateurs(prestations, beneficiaires, jour):
    """Indicateurs clés du rapport modèle pour un ensemble de prestations et de bénéficiaires."""
    consommants = {p["matricule_beneficiaire"] for p in prestations}
    rembourse = sum((p["mt_rembourse"] for p in prestations), ZERO)
    ages = [a for a in (_age(b.get("date_naissance"), jour) for b in beneficiaires) if a is not None]
    effectif = len(beneficiaires) or len(consommants)
    return {"Effectif": effectif, "Consommants": len(consommants), "NonConsommants": max(effectif - len(consommants), 0), "Actes": len(prestations),
            "TauxRecours": _div(len(consommants), effectif), "Reclame": _nombre(sum((p["mt_reclame"] for p in prestations), ZERO)),
            "Rembourse": _nombre(rembourse), "CoutParBeneficiaire": _div(rembourse, len(consommants)), "CoutParActe": _div(rembourse, len(prestations)),
            "Frequence": _div(len(prestations), len(consommants)), "AgeMoyen": round(sum(ages) / len(ages)) if ages else None}


def entreprises_a_risque(prestations, effectif, jour):
    """Tableau des entreprises (police du gestionnaire) avec score et alertes, comme la partie III du rapport modèle."""
    par_police = defaultdict(list)
    for p in prestations:
        par_police[p["police"]].append(p)
    eff_police = defaultdict(list)
    for e in effectif:
        eff_police[e["police"]].append(e)
    portefeuille = indicateurs(prestations, [], jour)
    lignes = []
    for police, ps in par_police.items():
        ind = indicateurs(ps, [], jour)
        ages = [a for a in (_age(p["date_naissance"], jour) for p in {p["matricule_beneficiaire"]: p for p in ps}.values()) if a is not None]
        rapports = [r for r in (_div(ind["CoutParBeneficiaire"], portefeuille["CoutParBeneficiaire"]), _div(ind["Frequence"], portefeuille["Frequence"]),
                                _div(ind["CoutParActe"], portefeuille["CoutParActe"])) if r is not None]
        score = round(sum(rapports) / len(rapports), 2) if rapports else 0
        alertes = []
        # Critique dès que le score atteint 1 (consigne du 2026-11-09)
        if score >= SEUIL_SCORE_CRITIQUE:
            alertes.append("Critique")
        if (ind["Frequence"] or 0) > SEUIL_ACTES:
            alertes.append("Trop d'actes")
        if portefeuille["CoutParActe"] and (ind["CoutParActe"] or 0) > float(SEUIL_COUT_ACTE) * portefeuille["CoutParActe"]:
            alertes.append("Coût par acte élevé")
        lignes.append({"Police": police, "Beneficiaires": ind["Consommants"], "Effectif": len(eff_police.get(police, [])), "Actes": ind["Actes"],
                       "Depenses": ind["Rembourse"], "AgeMoyen": round(sum(ages) / len(ages)) if ages else None, "CoutParBeneficiaire": ind["CoutParBeneficiaire"],
                       "ActesParBeneficiaire": ind["Frequence"], "CoutParActe": ind["CoutParActe"], "Score": score, "Alertes": alertes})
    return sorted(lignes, key=lambda l: -l["Depenses"]), portefeuille


# ------------------------------------------------------------------ tableau de bord
def tableau_de_bord(params):
    with connection.cursor() as cursor:
        exercice, du, au, exercices = _periode(cursor, params)
        garant = str(params.get("garant") or "").strip()
        prestations, effectif = charger(cursor, du, au, garant)
        cotisations = _lignes(cursor, "SELECT * FROM lephare_sante_cotisation WHERE exercice = %s ORDER BY entreprise", [exercice])
        confirmes = {l["entreprise"]: l["police"] for l in _lignes(cursor, "SELECT entreprise, police FROM lephare_sante_entreprise_police")}
        polices = sorted({l["police"] for l in _lignes(cursor, "SELECT DISTINCT police FROM lephare_sante_prestation UNION SELECT DISTINCT police FROM lephare_sante_effectif")
                          if l["police"]})
        garants = [l["garant"] for l in _lignes(cursor, "SELECT DISTINCT garant FROM lephare_sante_prestation ORDER BY 1") if l["garant"]]
    propositions = proposer_liens([c["entreprise"] for c in cotisations], polices, confirmes)
    conso = defaultdict(lambda: {"Total": ZERO, "Mois": defaultdict(lambda: ZERO), "Actes": 0, "Beneficiaires": set()})
    for p in prestations:
        c = conso[p["police"]]
        c["Total"] += p["mt_rembourse"]
        c["Mois"][p["date_cloture"].month] += p["mt_rembourse"]
        c["Actes"] += 1
        c["Beneficiaires"].add(p["matricule_beneficiaire"])
    eff = Counter(e["police"] for e in effectif if e["actif"])

    def situation(provision, consommation):
        if not provision:
            return "Sans provision"
        if consommation > provision:
            return "Provision dépassée"
        return "Alerte" if consommation >= SEUIL_ALERTE_PROVISION * provision else "Normal"

    controle, polices_liees = [], set()
    for c in cotisations:
        confirme = c["entreprise"] in confirmes
        police = confirmes.get(c["entreprise"], propositions.get(c["entreprise"], "")) or ""
        polices_liees.add(police)
        k = conso.get(police) if police else None
        consommation = k["Total"] if k else ZERO
        controle.append({
            "Entreprise": c["entreprise"], "Police": police, "LienConfirme": confirme, "LienPropose": bool(police) and not confirme,
            "EffectifEtat": c["effectif"], "Beneficiaires": eff.get(police, 0) if police else 0, "PrimeHt": _nombre(c["prime_ht"]),
            "CotisationPure": _nombre(c["cotisation_pure"]), "Honoraires": _nombre(c["honoraires"]), "Commissions": _nombre(c["commissions"]),
            "Apporteurs": _nombre(c["apporteurs"]), "Provision": _nombre(c["provision"]), "Consommation": _nombre(consommation),
            "Reste": _nombre(c["provision"] - consommation), "Taux": _div(consommation, c["provision"]), "Couverture": _div(c["provision"], consommation),
            "Mois": {m: _nombre(v) for m, v in (k["Mois"].items() if k else [])}, "Actes": k["Actes"] if k else 0,
            "Consommants": len(k["Beneficiaires"]) if k else 0, "Situation": situation(c["provision"], consommation),
        })
    # Polices qui consomment sans état de cotisation rapproché
    for police, k in conso.items():
        if police not in polices_liees:
            controle.append({"Entreprise": "", "Police": police, "LienConfirme": False, "LienPropose": False, "EffectifEtat": None, "Beneficiaires": eff.get(police, 0),
                             "PrimeHt": 0.0, "CotisationPure": 0.0, "Honoraires": 0.0, "Commissions": 0.0, "Apporteurs": 0.0, "Provision": 0.0,
                             "Consommation": _nombre(k["Total"]), "Reste": -_nombre(k["Total"]), "Taux": None, "Couverture": None,
                             "Mois": {m: _nombre(v) for m, v in k["Mois"].items()}, "Actes": k["Actes"], "Consommants": len(k["Beneficiaires"]),
                             "Situation": "Sans état de cotisation"})
    controle.sort(key=lambda l: (-(l["Taux"] or 0) if l["Provision"] else 1, -l["Consommation"]))
    total = lambda cle: sum(l[cle] for l in controle)  # noqa: E731
    provision, consommation = total("Provision"), total("Consommation")
    risque, _portefeuille = entreprises_a_risque(prestations, effectif, au)
    mensuel = defaultdict(lambda: [ZERO, 0])
    for p in prestations:
        m = mensuel[(p["date_cloture"].year, p["date_cloture"].month)]
        m[0] += p["mt_rembourse"]
        m[1] += 1
    total_mois = sum((v[0] for v in mensuel.values()), ZERO)
    return {
        "Exercice": exercice, "Exercices": exercices, "Du": _iso(du), "Au": _iso(au), "Garants": garants, "Polices": polices,
        "Totaux": {"PrimeHt": total("PrimeHt"), "CotisationPure": total("CotisationPure"), "Honoraires": total("Honoraires"), "Commissions": total("Commissions"),
                   "Apporteurs": total("Apporteurs"), "Provision": provision, "Consommation": consommation, "Reste": provision - consommation,
                   "Taux": _div(consommation, provision), "Entreprises": len(cotisations),
                   "EnDepassement": sum(1 for l in controle if l["Situation"] == "Provision dépassée"),
                   "EnAlerte": sum(1 for l in controle if l["Situation"] == "Alerte"), "SansEtat": sum(1 for l in controle if l["Situation"] == "Sans état de cotisation")},
        "Indicateurs": indicateurs(prestations, [e for e in effectif if e["actif"]], au),
        "Controle": controle,
        "Mensuel": [{"Mois": f"{MOIS[m - 1]} {a}", "Depenses": _nombre(v[0]), "Part": _div(v[0], total_mois) or 0, "Actes": v[1], "CoutParActe": _div(v[0], v[1])}
                    for (a, m), v in sorted(mensuel.items())],
        "Familles": repartition(prestations, lambda p: p["famille"]),
        "Executants": repartition(prestations, lambda p: p["centre_executant"])[:15],
        "Risque": risque,
        "CotisationsImportees": bool(cotisations),
    }


def lier_entreprise(donnees, user):
    entreprise = " ".join(str(donnees.get("Entreprise") or "").split())
    police = str(donnees.get("Police") or "").strip()
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM lephare_sante_cotisation WHERE entreprise = %s LIMIT 1", [entreprise])
        if not cursor.fetchone():
            raise ErreurConsommation("Entreprise inconnue de l'état des cotisations.")
        if police:
            cursor.execute("SELECT 1 FROM lephare_sante_prestation WHERE police = %s UNION SELECT 1 FROM lephare_sante_effectif WHERE police = %s LIMIT 1", [police, police])
            if not cursor.fetchone():
                raise ErreurConsommation("Police inconnue des relevés et de l'effectif du gestionnaire.")
        auteur = ((user.get_full_name() if hasattr(user, "get_full_name") else "") or getattr(user, "email", "") or "")[:150]
        cursor.execute("""INSERT INTO lephare_sante_entreprise_police (entreprise, police, auteur) VALUES (%s, %s, %s)
                          ON CONFLICT (entreprise) DO UPDATE SET police = EXCLUDED.police, auteur = EXCLUDED.auteur, datemaj = now()""", [entreprise, police, auteur])
    return {"Message": f"{entreprise} : " + (f"lié à la police {police}." if police else "aucune police du gestionnaire.")}


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_tableau_de_bord(request):
    return _reponse(tableau_de_bord, request.query_params)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_lien(request):
    return _reponse(lier_entreprise, request.data, request.user)
