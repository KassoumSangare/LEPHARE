"""
Avenants de retrait, de résiliation et de changement d'immatriculation (demande du 2026-11-19). Ils matérialisent un
changement de la police en cours d'exercice, sous le même numéro de police ; le renouvellement (renouvellement.py) et
l'incorporation (incorporation.py, sante/avenant.py) ont leurs propres parcours.

- RETRAIT (RET) : pendant de l'incorporation, pour les flottes Automobile et les polices de groupe (IA, MRH, Vie AFA ;
  Santé : sortie d'un membre ou d'une famille dans sante/avenant.py). Ristourne au choix : portion de la prime de l'objet
  retiré pour le temps restant à courir jusqu'à l'échéance, ou aucune (tarifs forfaitaires : IA, AFA, par défaut).
- RÉSILIATION (RES) : toute la police. En cours de contrat, ristourne de la portion de prime du temps restant à courir ;
  à l'échéance (date d'effet = lendemain de l'échéance), aucune ristourne : l'avenant signé matérialise la résiliation.
  Le contrat de base est marqué résilié (IdContratAnnulation, sp_confirmation_devis), la police ne se renouvelle plus.
- CHANGEMENT D'IMMATRICULATION (CHI) : Automobile ; la ligne du véhicule passe sous sa nouvelle immatriculation
  (oldmatricule = ancienne), sans prime ; fn_liste_objets_assures v3 (migration 0222) le prend en compte.

Ristourne : pour chaque objet, chaque contrat de la période qui le porte (affaire nouvelle ou renouvellement,
incorporation, modification, retrait déjà émis) compte pour la part de sa propre période qui reste à courir après la
date de l'avenant (jours restants / jours de sa période) ; prime nette hors CEDEAO (montant légal fixe), FGA, taxe au
même rapport (Automobile : taxe recalculée en une fois sur la prime nette et l'accessoire, taxe_auto.py). Commission
du cabinet reprise au taux du contrat, donc négative. Accessoires (frais d'avenant) au choix, 0 par défaut.

Émission directe : devis d'avenant (sp_avenant_creation_devis_initial : numéro d'avenant, période), lignes des objets,
confirmation par sp_confirmation_devis, quittance créée ici. sp_generation_quittance annulerait la quittance d'origine
pour un retrait ou une résiliation (règle d'URANUS faite pour l'annulation) : la quittance d'origine reste due, la
ristourne est une quittance négative (nature R) en plus, qui diminue le solde du client.

Routes : GET /api/avenants/<idcontrat>/ (préparation), POST /api/avenants/<idcontrat>/simulation/ (montants, rien
n'est écrit), POST /api/avenants/<idcontrat>/ (émission), GET /api/avenants/document/<idcontrat>/ (avenant imprimé).
"""

import logging
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from . import vie_offres
from .recalcul_contrat import repartir
from .renouvellement import AUTHENTIFICATION, ErreurRenouvellement, _contrat_base, _date, _iso, _lignes
from .taxe_auto import ID_PRODUIT_AUTO, taux_taxe_auto

logger = logging.getLogger(__name__)

RETRAIT, RESILIATION, IMMATRICULATION = "RET", "RES", "CHI"
LIBELLES = {RETRAIT: "Retrait", RESILIATION: "Résiliation", IMMATRICULATION: "Changement d'immatriculation"}
ID_PRODUIT_IA, ID_PRODUIT_MRH, ID_PRODUIT_SANTE, ID_PRODUIT_TRANSPORT, ID_PRODUIT_VIE = 2, 4, 5, 6, 10
ID_FGA, ID_CEDEAO = 2, 3
# Contrats dont la prime court sur la période (un retrait déjà émis compte en moins)
CODES_PRIME = ("AFN", "REN", "RPP", "TRP", "INC", "MOD", "RET")
CODES_HISTORIQUE = ("AFN", "REN", "RPP", "TRP", "INC", "MOD", "RET", "RES", "CHI", "ANL", "ANP")
NATURE_RISTOURNE, NATURE_COMPTANT, STATUT_EN_COURS = "R", "C", 1
MOTIF_MINIMUM = 5
# Compléments de ligne recopiés avec la ligne (tables présentes selon les branches)
COMPLEMENTS = ("stdcomplementdevisdetailauto", "stdcomplementdevisdetailvoyage", "stdcomplementdevisdetailsante",
               "stdcomplementdevisdetailrc", "stdcomplementdevisdetaildommage")
ZERO = Decimal("0")


class ErreurAvenant(Exception):
    """Avenant refusé : message affiché tel quel."""


def _d(valeur):
    return ZERO if valeur in (None, "") else (valeur if isinstance(valeur, Decimal) else Decimal(str(valeur)))


def _franc(valeur):
    return _d(valeur).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _nombre(valeur):
    return float(valeur) if valeur is not None else 0.0


def _cle(matricule):
    return str(matricule or "").strip()


# ------------------------------------------------------------------ contrat et police
def _base(cursor, id_contrat):
    """Contrat de base de la période (affaire nouvelle ou renouvellement) ; refus si la police est annulée ou résiliée."""
    ligne = _lignes(cursor, "SELECT COALESCE(idcontratannulation, 0) AS annule FROM stdcontrat WHERE idcontrat = %s", [id_contrat])
    if not ligne:
        raise ErreurAvenant("Contrat introuvable.")
    if ligne[0]["annule"]:
        raise ErreurAvenant("Contrat annulé ou résilié : aucun avenant n'est possible.")
    try:
        base = _contrat_base(cursor, id_contrat)
    except ErreurRenouvellement as erreur:
        raise ErreurAvenant(str(erreur).replace("elle ne peut pas être renouvelée", "aucun avenant n'est possible")) from erreur
    complement = _lignes(cursor, """
        SELECT c.taux_commission, c.idintermediaire,
               (SELECT idoffre FROM stdcontratdetail x WHERE x.idcontrat = c.idcontrat ORDER BY x.idcontratdetail LIMIT 1) AS idoffre
        FROM stdcontrat c WHERE c.idcontrat = %s""", [base["idcontrat"]])[0]
    base.update(complement)
    return base


def _package_oreole(cursor, id_devis):
    cursor.execute("SELECT to_regclass('lephare_oreole_package') IS NOT NULL")
    if not cursor.fetchone()[0]:
        return False
    cursor.execute(
        "SELECT 1 FROM lephare_oreole_package WHERE %s IN (iddevis_sante, iddevis_ia, iddevis_afa) LIMIT 1", [id_devis])
    return bool(cursor.fetchone())


def _objets(cursor, base):
    """Objets en vigueur de la police (fn_liste_objets_assures : incorporations comprises, retraits écartés), libellés."""
    return _lignes(cursor, """
        SELECT l.matricule AS "Matricule", l.idcontrat AS "IdContrat", l.idcontratdetail AS "IdContratDetail",
               c.dateeffet::date AS "DateEffet", TRIM(a.libelleavenant) AS "Mouvement",
               d.primenette AS "PrimeNette", d.taxeenregistrement AS "Taxe", d.fga AS "Fga",
               NULLIF(TRIM(COALESCE(m.libellemarque, '') || ' ' || COALESCE(d.modelevehicule, '')), '') AS "Vehicule",
               NULLIF(TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')), '') AS "Personne",
               NULLIF(TRIM(COALESCE(d.assure, '')), '') AS "Assure", NULLIF(TRIM(COALESCE(d.observation, '')), '') AS "Observation"
        FROM fn_liste_objets_assures(%s) l
        JOIN stdcontratdetail d ON d.idcontratdetail = l.idcontratdetail
        JOIN stdcontrat c ON c.idcontrat = l.idcontrat
        JOIN stdavenant a ON a.idavenant = c.idavenant
        LEFT JOIN stdmarque m ON m.idmarque = d.idmarque
        LEFT JOIN stdclient cl ON c.idproduit IN (2, 10)
             AND cl.idclient = CASE WHEN l.matricule ~ '^0*[1-9][0-9]{0,17}$' THEN LTRIM(l.matricule, '0')::bigint END
        ORDER BY l.matricule
    """, [base["numeropolice"]])


def _libelle_objet(objet, id_produit):
    if id_produit == ID_PRODUIT_AUTO:
        return " - ".join(x for x in (objet["Matricule"], objet["Vehicule"]) if x) or "Véhicule"
    return objet["Personne"] or objet["Assure"] or objet["Observation"] or objet["Matricule"] or "Risque du contrat"


def _actes(cursor, base, objets):
    """Avenants possibles sur ce contrat, raison sinon ; ristourne proposée par défaut."""
    produit = base["idproduit"]
    oreole = _package_oreole(cursor, base["iddevis"])
    actes = {}
    raison = ""
    if oreole:
        raison = "Police du package Oreole Santé : ses trois polices se gèrent ensemble depuis le bloc Oreole Santé."
    elif produit == ID_PRODUIT_SANTE:
        raison = "Santé : la sortie d'un membre ou d'une famille se fait par « Incorporer ou retirer un membre »."
    elif produit == ID_PRODUIT_AUTO and not base["flotte"]:
        raison = "Contrat mono : le retrait d'un véhicule unique est une résiliation."
    elif produit not in (ID_PRODUIT_AUTO, ID_PRODUIT_IA, ID_PRODUIT_MRH, ID_PRODUIT_VIE):
        raison = "Le retrait concerne les flottes Automobile et les polices de groupe (IA, MRH, Vie, Santé)."
    elif produit == ID_PRODUIT_VIE and vie_offres.offre_du_devis(cursor, base["iddevis"])["Saisie"] == vie_offres.SAISIE_COTISATION:
        raison = "Retraite complémentaire : un salarié sortant quitte l'état des cotisations du mois suivant."
    elif len(objets) < 2:
        raison = "Un seul objet assuré : son retrait est une résiliation de la police."
    # Tarifs forfaitaires (IA, AFA) : sans prorata à l'incorporation, donc sans ristourne par défaut au retrait
    actes[RETRAIT] = {"Possible": not raison, "Raison": raison,
                      "RistourneParDefaut": produit in (ID_PRODUIT_AUTO, ID_PRODUIT_MRH)}
    raison = ""
    if oreole:
        raison = "Police du package Oreole Santé : ses trois polices se résilient ensemble, pas une seule."
    elif produit == ID_PRODUIT_TRANSPORT:
        raison = "Transport : les polices se gèrent par leurs bordereaux et certificats."
    actes[RESILIATION] = {"Possible": not raison, "Raison": raison, "RistourneParDefaut": True}
    actes[IMMATRICULATION] = {
        "Possible": produit == ID_PRODUIT_AUTO and bool(objets),
        "Raison": "" if produit == ID_PRODUIT_AUTO else "Le changement d'immatriculation concerne l'Automobile.",
        "RistourneParDefaut": False,
    }
    return actes


def _historique(cursor, base):
    """Contrats de la police depuis le début de la période : affaire, avenants, résiliation."""
    lignes = _lignes(cursor, f"""
        SELECT c.idcontrat AS "IdContrat", a.codeavenant AS "Code", TRIM(a.libelleavenant) AS "Mouvement",
               TRIM(COALESCE(c.numeroavenant, '')) AS "NumeroAvenant", c.dateemission::date AS "DateEmission",
               c.dateeffet::date AS "DateEffet", c.dateexpiration::date AS "DateExpiration", c.primettc AS "PrimeTtc",
               COALESCE(c.idcontratannulation, 0) <> 0 AS "Annule", TRIM(COALESCE(q.numeroquittance, '')) AS "Quittance"
        FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
        LEFT JOIN stdquittance q ON q.idquittance = c.idquittance
        WHERE c.numeropolice = %s AND a.codeavenant IN {CODES_HISTORIQUE} AND c.dateeffet::date >= %s
        ORDER BY c.dateeffet, c.idcontrat
    """, [base["numeropolice"], base["dateeffet"]])
    for ligne in lignes:
        for cle in ("DateEmission", "DateEffet", "DateExpiration"):
            ligne[cle] = _iso(ligne[cle])
        ligne["PrimeTtc"] = _nombre(ligne["PrimeTtc"])
    return lignes


# ------------------------------------------------------------------ montants de l'avenant
def _fraction(effet, expiration, date_acte):
    """Part de la période [effet, expiration] (jours inclus) qui reste à courir à partir de date_acte."""
    total = (expiration - effet).days + 1
    if total <= 0:
        return ZERO
    restant = (expiration - max(date_acte, effet)).days + 1
    return Decimal(max(0, min(total, restant))) / Decimal(total)


def _alias_immatriculation(cursor, base):
    """Ancienne immatriculation -> nouvelle, d'après les changements d'immatriculation de la période."""
    cursor.execute(
        """SELECT TRIM(COALESCE(d.oldmatricule, '')), TRIM(COALESCE(d.matricule, ''))
           FROM stdcontratdetail d JOIN stdcontrat c ON c.idcontrat = d.idcontrat JOIN stdavenant a ON a.idavenant = c.idavenant
           WHERE c.numeropolice = %s AND a.codeavenant = 'CHI' AND COALESCE(c.idcontratannulation, 0) = 0 AND c.dateeffet::date >= %s
           ORDER BY c.dateeffet, c.idcontrat""",
        [base["numeropolice"], base["dateeffet"]],
    )
    alias = {}
    for ancienne, nouvelle in cursor.fetchall():
        if ancienne and nouvelle and ancienne != nouvelle:
            alias[ancienne] = nouvelle
    return alias


def _actuelle(alias, matricule):
    vues = set()
    while matricule in alias and matricule not in vues:
        vues.add(matricule)
        matricule = alias[matricule]
    return matricule


def _ristournes(cursor, base, date_acte, matricules):
    """
    Prime qui reste à courir après date_acte pour chaque objet (clé : immatriculation ou matricule en vigueur), cumulée
    sur les contrats de la période qui le portent. Retour {matricule: {"Ht", "Fga", "Taxe", "Garanties": {idg: ht}}}
    en montants positifs non arrondis.
    """
    auto = base["idproduit"] == ID_PRODUIT_AUTO
    alias = _alias_immatriculation(cursor, base)
    contrats = _lignes(cursor, f"""
        SELECT c.idcontrat, c.dateeffet::date AS effet, c.dateexpiration::date AS expiration
        FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
        WHERE c.numeropolice = %s AND COALESCE(c.idcontratannulation, 0) = 0 AND a.codeavenant IN {CODES_PRIME}
          AND c.dateeffet::date BETWEEN %s AND %s
    """, [base["numeropolice"], base["dateeffet"], base["dateexpiration"]])
    resultat = {m: {"Ht": ZERO, "Fga": ZERO, "Taxe": ZERO, "Garanties": {}} for m in matricules}
    for contrat in contrats:
        fraction = _fraction(contrat["effet"], contrat["expiration"], date_acte)
        if not fraction:
            continue
        lignes = _lignes(cursor, """
            SELECT d.idcontratdetail, TRIM(COALESCE(d.matricule, '')) AS matricule, COALESCE(d.primenette, 0) AS primenette,
                   COALESCE(d.taxeenregistrement, 0) AS taxe, COALESCE(d.fga, 0) AS fga,
                   COALESCE((SELECT json_agg(json_build_array(g.idgarantie, g.primenette))
                             FROM stdcontratdetgarantie g WHERE g.idcontratdetail = d.idcontratdetail AND g.acquise), '[]') AS garanties
            FROM stdcontratdetail d WHERE d.idcontrat = %s ORDER BY d.idcontratdetail
        """, [contrat["idcontrat"]])
        for ligne in lignes:
            cle = _actuelle(alias, ligne["matricule"])
            if cle not in resultat:
                continue
            garanties = [(int(i), _d(p)) for i, p in ligne["garanties"]]
            # Automobile : la CEDEAO (montant légal fixe) ne se ristourne pas ; le FGA est porté par la ligne
            cedeao = sum((p for i, p in garanties if auto and i == ID_CEDEAO), ZERO)
            ht = _d(ligne["primenette"]) - cedeao
            cumul = resultat[cle]
            cumul["Ht"] += ht * fraction
            cumul["Fga"] += _d(ligne["fga"]) * fraction if auto else ZERO
            cumul["Taxe"] += _d(ligne["taxe"]) * fraction
            for idg, prime in garanties:
                if idg in (ID_FGA, ID_CEDEAO) and auto:
                    continue
                cumul["Garanties"][idg] = cumul["Garanties"].get(idg, ZERO) + prime * fraction
    return resultat


def _taux_produit(cursor, base, date_acte):
    try:
        with transaction.atomic():
            cursor.execute("SELECT fn_get_taux_taxe(%s, %s, %s, %s)",
                           [base["idcompagnie"], base["idproduit"], base["idoffre"] or 0, date_acte])
            ligne = cursor.fetchone()
        return _d(ligne[0]) if ligne and ligne[0] is not None else None
    except DatabaseError:
        return None


def _donnees(donnees):
    """Saisie de l'écran : type, date, objets, ristourne, accessoires, nouvelle immatriculation, motif."""
    acte = str(donnees.get("Type") or "").upper()
    if acte not in LIBELLES:
        raise ErreurAvenant("Choisissez l'avenant : retrait, résiliation ou changement d'immatriculation.")
    date_acte = _date(donnees.get("DateEffet"))
    if not date_acte:
        raise ErreurAvenant("Saisissez la date d'effet de l'avenant.")
    try:
        accessoire = _franc(donnees.get("Accessoire") or 0)
    except Exception as erreur:  # noqa: BLE001
        raise ErreurAvenant("Accessoires : montant invalide.") from erreur
    if accessoire < 0:
        raise ErreurAvenant("Les accessoires de l'avenant ne peuvent pas être négatifs.")
    return {
        "Type": acte, "DateEffet": date_acte, "Accessoire": accessoire,
        "Objets": [_cle(m) for m in (donnees.get("Objets") or [])],
        "Ristourne": donnees.get("Ristourne") not in (False, "false", "0", 0),
        "Immatriculation": _cle(donnees.get("NouvelleImmatriculation")).upper(),
        "Motif": str(donnees.get("Motif") or "").strip(),
    }


def calculer(cursor, base, saisie):
    """Montants de l'avenant (rien n'est écrit) : lignes par objet et en-tête. Lève ErreurAvenant si la saisie est refusée."""
    objets = _objets(cursor, base)
    actes = _actes(cursor, base, objets)
    acte, date_acte = saisie["Type"], saisie["DateEffet"]
    if not actes[acte]["Possible"]:
        raise ErreurAvenant(actes[acte]["Raison"])
    debut, echeance = base["dateeffet"], base["dateexpiration"]
    fin = echeance + timedelta(days=1) if acte == RESILIATION else echeance
    if not debut <= date_acte <= fin:
        raise ErreurAvenant(f"La date d'effet doit être comprise entre le {debut:%d/%m/%Y} et le {fin:%d/%m/%Y}"
                            + (" (lendemain de l'échéance : résiliation à l'échéance)." if acte == RESILIATION else "."))
    par_matricule = {o["Matricule"]: o for o in objets}
    if acte == RETRAIT:
        choisis = [m for m in dict.fromkeys(saisie["Objets"]) if m in par_matricule]
        if not choisis:
            raise ErreurAvenant("Cochez le ou les objets à retirer.")
        if len(choisis) >= len(objets):
            raise ErreurAvenant("Tous les objets de la police seraient retirés : faites une résiliation.")
    elif acte == RESILIATION:
        choisis = list(par_matricule)
    else:
        choisis = [m for m in saisie["Objets"][:1] if m in par_matricule]
        if not choisis:
            raise ErreurAvenant("Choisissez le véhicule dont l'immatriculation change.")
        nouvelle = saisie["Immatriculation"]
        if len(nouvelle) < 4:
            raise ErreurAvenant("Saisissez la nouvelle immatriculation.")
        if nouvelle.replace(" ", "").replace("-", "") == choisis[0].upper().replace(" ", "").replace("-", ""):
            raise ErreurAvenant("La nouvelle immatriculation est celle du véhicule.")
        if any(nouvelle.replace(" ", "").replace("-", "") == m.upper().replace(" ", "").replace("-", "") for m in par_matricule):
            raise ErreurAvenant(f"Le véhicule {nouvelle} est déjà assuré dans cette police.")
    a_echeance = acte == RESILIATION and date_acte > echeance
    avec_ristourne = acte in (RETRAIT, RESILIATION) and saisie["Ristourne"] and not a_echeance
    auto = base["idproduit"] == ID_PRODUIT_AUTO
    montants = _ristournes(cursor, base, date_acte, choisis) if avec_ristourne else {}
    lignes = []
    for matricule in choisis:
        objet = par_matricule[matricule]
        cumul = montants.get(matricule)
        ht = -_franc(cumul["Ht"]) if cumul else ZERO
        fga = -_franc(cumul["Fga"]) if cumul else ZERO
        taxe = -_franc(cumul["Taxe"]) if cumul else ZERO
        # Garanties : la ristourne de la ligne répartie au prorata de leurs primes restant à courir (plus forts restes)
        garanties = {}
        if cumul and cumul["Garanties"]:
            garanties = {idg: -part for idg, part in repartir(-ht, list(cumul["Garanties"].items())).items()}
        lignes.append({
            "Matricule": matricule, "Libelle": _libelle_objet(objet, base["idproduit"]),
            "IdContratDetail": objet["IdContratDetail"], "IdContrat": objet["IdContrat"],
            "PrimeNette": ht, "Fga": fga, "Taxe": taxe, "Garanties": garanties,
            "NouvelleImmatriculation": saisie["Immatriculation"] if acte == IMMATRICULATION else "",
        })
    accessoire = saisie["Accessoire"]
    ht_total = sum((l["PrimeNette"] for l in lignes), ZERO)
    fga_total = sum((l["Fga"] for l in lignes), ZERO)
    if auto:
        taxe = _franc((ht_total + accessoire) * taux_taxe_auto(cursor, date_acte) / 100)
    else:
        taux = _taux_produit(cursor, base, date_acte)
        taxe = sum((l["Taxe"] for l in lignes), ZERO) + (_franc(accessoire * taux / 100) if taux is not None else ZERO)
    prime_nette = ht_total + fga_total
    taux_commission = _d(base["taux_commission"])
    return {
        "Type": acte, "Libelle": LIBELLES[acte], "DateEffet": date_acte, "DateExpiration": max(date_acte, echeance),
        "AEcheance": a_echeance, "Ristourne": avec_ristourne, "Lignes": lignes,
        "PrimeNette": prime_nette, "Fga": fga_total, "Accessoire": accessoire, "Taxe": taxe,
        "PrimeTtc": prime_nette + accessoire + taxe,
        "Commission": _franc(ht_total * taux_commission / 100), "TauxCommission": taux_commission,
        "JoursRestants": max(0, (echeance - date_acte).days + 1), "JoursPeriode": (echeance - debut).days + 1,
    }


def _vers_json(calcul):
    lignes = [{
        **{cle: valeur for cle, valeur in l.items() if cle != "Garanties"},
        "PrimeNette": _nombre(l["PrimeNette"]), "Fga": _nombre(l["Fga"]), "Taxe": _nombre(l["Taxe"]),
    } for l in calcul["Lignes"]]
    return {
        **{cle: valeur for cle, valeur in calcul.items() if cle not in ("Lignes",)},
        "DateEffet": _iso(calcul["DateEffet"]), "DateExpiration": _iso(calcul["DateExpiration"]), "Lignes": lignes,
        **{cle: _nombre(calcul[cle]) for cle in ("PrimeNette", "Fga", "Accessoire", "Taxe", "PrimeTtc", "Commission", "TauxCommission")},
    }


# ------------------------------------------------------------------ écriture
def _colonnes(cursor, table):
    """Colonnes d'une table : (nom, générée) ; les identifiants générés ne se recopient pas."""
    cursor.execute(
        """SELECT a.attname, (a.attidentity <> '' OR COALESCE(pg_get_expr(d.adbin, d.adrelid), '') LIKE 'nextval%%')
           FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
           WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped AND a.attgenerated = ''
           ORDER BY a.attnum""",
        [table],
    )
    return cursor.fetchall()


def _copier(cursor, table, colonne, valeur, remplacements):
    """Recopie les lignes de table où colonne = valeur, avec les valeurs de remplacements ; renvoie les nouveaux identifiants."""
    colonnes = _colonnes(cursor, table)
    generees = [n for n, g in colonnes if g]
    copiees = [n for n, g in colonnes if not g]
    selection = ["%s" if n in remplacements else f'"{n}"' for n in copiees]
    parametres = [remplacements[n] for n in copiees if n in remplacements] + [valeur]
    sql = (f'INSERT INTO {table} ({", ".join(f"{chr(34)}{n}{chr(34)}" for n in copiees)}) '
           f'SELECT {", ".join(selection)} FROM {table} WHERE "{colonne}" = %s')
    if generees:
        sql += f' RETURNING "{generees[0]}"'
    cursor.execute(sql, parametres)
    return [l[0] for l in cursor.fetchall()] if generees else []


def _ligne_devis_source(cursor, id_contrat_detail):
    """Ligne de devis d'où vient une ligne de contrat : même devis, même matricule, même rang parmi les homonymes."""
    cursor.execute(
        """WITH l AS (SELECT d.idcontratdetail, c.iddevis, TRIM(COALESCE(d.matricule, '')) AS m,
                             ROW_NUMBER() OVER (PARTITION BY d.idcontrat, TRIM(COALESCE(d.matricule, '')) ORDER BY d.idcontratdetail) AS rang
                      FROM stdcontratdetail d JOIN stdcontrat c ON c.idcontrat = d.idcontrat
                      WHERE d.idcontrat = (SELECT idcontrat FROM stdcontratdetail WHERE idcontratdetail = %s)),
                s AS (SELECT dd.iddevisdetail, dd.iddevis, TRIM(COALESCE(dd.matricule, '')) AS m,
                             ROW_NUMBER() OVER (PARTITION BY TRIM(COALESCE(dd.matricule, '')) ORDER BY dd.iddevisdetail) AS rang
                      FROM stddevisdetail dd WHERE dd.iddevis = (SELECT iddevis FROM l LIMIT 1))
           SELECT s.iddevisdetail FROM l JOIN s ON s.m = l.m AND s.rang = l.rang WHERE l.idcontratdetail = %s""",
        [id_contrat_detail, id_contrat_detail],
    )
    ligne = cursor.fetchone()
    return ligne[0] if ligne else None


def _ecrire_lignes(cursor, base, id_devis, calcul):
    for ligne in calcul["Lignes"]:
        source = _ligne_devis_source(cursor, ligne["IdContratDetail"])
        if not source:
            raise ErreurAvenant(f"Objet {ligne['Libelle']} : ligne d'origine introuvable dans son devis, avenant impossible.")
        # Ligne : prime nette des garanties (hors FGA, porté à part, comme sp_finalisation_devis), taxe de la ligne
        remplacements = {
            "iddevis": id_devis, "primenette": ligne["PrimeNette"], "primeannuelle": ligne["PrimeNette"],
            "taxeenregistrement": ligne["Taxe"], "fga": ligne["Fga"], "idoldhist": base["iddevis"], "primeimposee": True,
        }
        if calcul["Type"] == IMMATRICULATION:
            remplacements.update({"matricule": ligne["NouvelleImmatriculation"], "oldmatricule": ligne["Matricule"]})
        id_ligne = _copier(cursor, "stddevisdetail", "iddevisdetail", source, remplacements)[0]
        for table in COMPLEMENTS:
            cursor.execute("SELECT to_regclass(%s) IS NOT NULL", [table])
            if cursor.fetchone()[0] and "iddevisdetail" in {n for n, _ in _colonnes(cursor, table)}:
                _copier(cursor, table, "iddevisdetail", source, {"iddevisdetail": id_ligne})
        nouvelles = _copier(cursor, "stddevisdetgarantie", "iddevisdet", source, {"iddevisdet": id_ligne})
        if nouvelles:
            cursor.execute("SELECT iddevisdetgarantie, idgarantie FROM stddevisdetgarantie WHERE iddevisdetgarantie = ANY(%s)", [nouvelles])
            for id_garantie_ligne, idg in cursor.fetchall():
                prime = ligne["Garanties"].get(idg, ZERO)
                cursor.execute(
                    "UPDATE stddevisdetgarantie SET primenette = %s, primeannuelle = %s, taxe = 0 WHERE iddevisdetgarantie = %s",
                    [prime, prime, id_garantie_ligne],
                )


def _creer_quittance(cursor, id_contrat):
    """Quittance de l'avenant, comme sp_generation_quittance hors annulation : la quittance d'origine reste en l'état.
    Ristourne (TTC négative) : nature R. Solde du client corrigé de la TTC."""
    contrat = _lignes(cursor, """
        SELECT c.idintermediaire, c.idcompagnie, c.idclient, c.dateeffet::date AS dateeffet, c.primettc, c.idproduit,
               COALESCE(cl.exoneredeaccess, FALSE) OR COALESCE(o.exoneredeaccess, FALSE) AS exo_acc,
               COALESCE(cl.exoneredetaxes, FALSE) OR COALESCE(o.exoneredetaxes, FALSE) AS exo_taxe
        FROM stdcontrat c LEFT JOIN stdclient cl ON cl.idclient = c.idclient
        LEFT JOIN stdoffre o ON o.idoffre = (SELECT idoffre FROM stdcontratdetail x WHERE x.idcontrat = c.idcontrat ORDER BY x.idcontratdetail LIMIT 1)
        WHERE c.idcontrat = %s""", [id_contrat])[0]
    if not _d(contrat["primettc"]):
        return None, ""
    cursor.execute("SELECT 1 FROM stdnumero WHERE idmodule = 'QUITT' AND cloture AND exercice = %s", [contrat["dateeffet"].year])
    if cursor.fetchone():
        raise ErreurAvenant(f"Exercice {contrat['dateeffet'].year} clôturé : la quittance de l'avenant ne peut pas être émise.")
    cursor.execute("SELECT TRIM(COALESCE(codeintermediaire, '0')) FROM stdintermediairecompagnie WHERE idintermediaire = %s AND idcompagnie = %s",
                   [contrat["idintermediaire"], contrat["idcompagnie"]])
    ligne = cursor.fetchone()
    cursor.execute("CALL public.sp_generation_numero_quittance(%s, %s, '')", [ligne[0] if ligne else "0", contrat["dateeffet"]])
    numero = (cursor.fetchone() or [""])[0]
    if not str(numero or "").strip():
        raise ErreurAvenant("Le numéro de quittance de l'avenant n'a pas pu être attribué.")
    nature = NATURE_RISTOURNE if _d(contrat["primettc"]) < 0 else NATURE_COMPTANT
    cursor.execute(
        """INSERT INTO stdquittance (numeroquittance, idintermediaire, idclient, nature, dateeffet, dateexpiration, exercice, source,
                                     primenette, taxe, accessoire, commission, primettc, encaissee, mt_encaisse, reglee, mt_regle,
                                     numeropolice, idquittannul, statut, idaperiteur, coassurance, idproduit, exoneredetaxes,
                                     exoneredeaccess, taux_commission, dateemission)
           SELECT %s, idintermediaire, idclient, %s, dateeffet, dateexpiration, %s, 1, primenette, taxe, accessoire, 0, primettc,
                  false, 0, false, 0, numeropolice, NULL, %s, idaperiteur, COALESCE(coassurance, false), idproduit, %s, %s,
                  taux_commission, dateemission
           FROM stdcontrat WHERE idcontrat = %s RETURNING idquittance""",
        [numero, nature, contrat["dateeffet"].year, STATUT_EN_COURS, contrat["exo_taxe"], contrat["exo_acc"], id_contrat],
    )
    id_quittance = cursor.fetchone()[0]
    cursor.execute(
        """INSERT INTO stddetquittance (idquittance, idbranchereassurance, tauxtaxe, tauxcommission, primenette, taxe, commission)
           SELECT %s, sg.idgarantie, t.tauxtaxe, cm.tauxcommission, SUM(g.primenette), SUM(g.primenette) * t.tauxtaxe / 100,
                  SUM(g.primenette) * cm.tauxcommission / 100
           FROM stdcontrat c
           JOIN stdcontratdetail d ON d.idcontrat = c.idcontrat
           JOIN stdcontratdetgarantie g ON g.idcontratdetail = d.idcontratdetail
           JOIN stdsousgarantie sg ON sg.idsousgarantie = g.idgarantie
           JOIN stdtauxtaxegarantieproduit t ON t.idgarantie = g.idgarantie AND c.dateeffet::date BETWEEN t.debutvalidite AND t.finvalidite
           JOIN stdcommissionproduitcompagnie cm ON cm.idproduit = t.idproduit AND cm.idproduit = c.idproduit
                AND c.dateeffet::date BETWEEN cm.debutvalidite AND cm.finvalidite
           WHERE c.idcontrat = %s
           GROUP BY sg.idgarantie, t.tauxtaxe, cm.tauxcommission
           HAVING SUM(g.primenette) <> 0""",
        [id_quittance, id_contrat],
    )
    cursor.execute("UPDATE stdcontrat SET idquittance = %s WHERE idcontrat = %s", [id_quittance, id_contrat])
    cursor.execute("UPDATE stdclient SET solde = COALESCE(solde, 0) + %s WHERE idclient = %s", [contrat["primettc"], contrat["idclient"]])
    return id_quittance, str(numero).strip()


def emettre(cursor, utilisateur, base, saisie):
    """Avenant émis : devis d'avenant, lignes, confirmation en contrat, quittance. Renvoie le résultat pour l'écran."""
    if len(saisie["Motif"]) < MOTIF_MINIMUM:
        raise ErreurAvenant("Indiquez le motif de l'avenant (5 caractères au moins).")
    cursor.execute("SELECT 1 FROM stdcontrat WHERE idcontrat = %s FOR UPDATE", [base["idcontrat"]])
    calcul = calculer(cursor, base, saisie)
    cursor.execute("SELECT idavenant FROM stdavenant WHERE codeavenant = %s", [calcul["Type"]])
    avenant = cursor.fetchone()
    if not avenant:
        raise ErreurAvenant(f"Le mouvement « {calcul['Libelle']} » n'est pas configuré.")
    cursor.execute(
        "CALL sp_avenant_creation_devis_initial(%s, %s, %s, %s, %s, %s, %s, 0, '')",
        [utilisateur.id, base["idcontrat"], avenant[0], timezone.localdate(), calcul["DateEffet"], calcul["DateExpiration"],
         saisie["Motif"][:250]],
    )
    id_devis, message = cursor.fetchone()
    if not id_devis:
        raise ErreurAvenant(message or "Le devis de l'avenant n'a pas pu être créé.")
    # En-tête : montants de l'avenant (le devis recopié portait les primes du contrat), prime imposée (rien ne les recalcule)
    plusieurs = len(calcul["Lignes"]) > 1 and base["idproduit"] in (ID_PRODUIT_AUTO, ID_PRODUIT_IA)
    cursor.execute(
        """UPDATE stddevis SET primeannuelle = %s, primenette = %s, fga = %s, cedeao = 0, accessoire = %s, accessoirecompagnie = %s,
                  accessoireintermediaire = 0, accessoiregestionnaire = 0, taxe = %s, primettc = %s, commissionintermediaire = 0,
                  commissionaperiteur = 0, commissiongestionnaire = 0, primeimposee = true, motifannulation = %s,
                  flotte = (COALESCE(flotte, false) OR %s)
           WHERE iddevis = %s""",
        [calcul["PrimeNette"], calcul["PrimeNette"], calcul["Fga"], calcul["Accessoire"], calcul["Accessoire"], calcul["Taxe"],
         calcul["PrimeTtc"], saisie["Motif"][:250], plusieurs, id_devis],
    )
    _ecrire_lignes(cursor, base, id_devis, calcul)
    # Confirmation sans la quittance d'URANUS (elle annulerait la quittance d'origine) : réglage lu par sp_generation_quittance
    cursor.execute("SELECT set_config('lephare.reprise', 'on', true)")
    cursor.execute("CALL sp_confirmation_devis(%s, 0, '')", [id_devis])
    id_contrat, message = cursor.fetchone()
    cursor.execute("SELECT set_config('lephare.reprise', 'off', true)")
    if not id_contrat:
        raise ErreurAvenant(message or "L'avenant n'a pas pu être émis.")
    cursor.execute(
        "UPDATE stdcontrat SET taux_commission = %s, commissionintermediaire = %s, motifannulation = %s WHERE idcontrat = %s",
        [calcul["TauxCommission"], calcul["Commission"], saisie["Motif"][:250], id_contrat],
    )
    if calcul["Type"] == IMMATRICULATION:
        cursor.execute("UPDATE stdcontratdetail SET oldmatricule = %s WHERE idcontrat = %s",
                       [calcul["Lignes"][0]["Matricule"], id_contrat])
    _, numero_quittance = _creer_quittance(cursor, id_contrat)
    cursor.execute("SELECT TRIM(COALESCE(numeroavenant, '')), primettc FROM stdcontrat WHERE idcontrat = %s", [id_contrat])
    numero_avenant, ttc = cursor.fetchone()
    return {
        "IdContrat": id_contrat, "IdDevis": id_devis, "NumeroAvenant": numero_avenant, "NumeroQuittance": numero_quittance,
        "Type": calcul["Type"], "Libelle": calcul["Libelle"], "PrimeTtc": _nombre(ttc), "NumeroPolice": base["numeropolice"],
    }


# ------------------------------------------------------------------ vues
def _contrat_json(base):
    return {
        "IdContrat": base["idcontrat"], "NumeroPolice": base["numeropolice"], "Client": base["client"], "Compagnie": base["compagnie"],
        "Produit": base["produit"], "IdProduit": base["idproduit"], "Flotte": bool(base["flotte"]),
        "DateEffet": _iso(base["dateeffet"]), "DateExpiration": _iso(base["dateexpiration"]), "PrimeTtc": _nombre(base["primettc"]),
    }


def _refus(erreur):
    return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def avenants(request, pk):
    try:
        if request.method == "GET":
            with connection.cursor() as cursor:
                base = _base(cursor, pk)
                objets = _objets(cursor, base)
                return Response({
                    "Contrat": _contrat_json(base),
                    "Actes": _actes(cursor, base, objets),
                    "Objets": [{
                        "Matricule": o["Matricule"], "Libelle": _libelle_objet(o, base["idproduit"]), "Mouvement": o["Mouvement"],
                        "DateEffet": _iso(o["DateEffet"]), "PrimeNette": _nombre(o["PrimeNette"]), "IdContrat": o["IdContrat"],
                    } for o in objets],
                    "Historique": _historique(cursor, base),
                    "DateDuJour": _iso(timezone.localdate()),
                })
        saisie = _donnees(request.data or {})
        with transaction.atomic(), connection.cursor() as cursor:
            base = _base(cursor, pk)
            resultat = emettre(cursor, request.user, base, saisie)
        return Response(resultat, status=status.HTTP_201_CREATED)
    except (ErreurAvenant, ErreurRenouvellement, ValueError) as erreur:
        return _refus(erreur)
    except DatabaseError as erreur:
        logger.exception("Avenant refusé par la base pour le contrat %s.", pk)
        return _refus(str(erreur).splitlines()[0].split(" : ")[0][:300] or "L'avenant n'a pas pu être émis.")


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def simulation(request, pk):
    """Montants que l'avenant aurait, sans rien écrire."""
    try:
        saisie = _donnees(request.data or {})
        with connection.cursor() as cursor:
            base = _base(cursor, pk)
            return Response(_vers_json(calculer(cursor, base, saisie)))
    except (ErreurAvenant, ErreurRenouvellement, ValueError) as erreur:
        return _refus(erreur)
    except DatabaseError:
        logger.exception("Simulation d'avenant impossible pour le contrat %s.", pk)
        return _refus("Les montants de l'avenant ne peuvent pas être calculés pour le moment.")


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def historique(request, pk):
    """Contrats de la police, toutes périodes (affaire nouvelle, renouvellements, avenants), police annulée ou résiliée comprise."""
    with connection.cursor() as cursor:
        police = _lignes(cursor, "SELECT numeropolice FROM stdcontrat WHERE idcontrat = %s", [pk])
        if not police:
            return Response({"error": "Contrat introuvable."}, status=status.HTTP_404_NOT_FOUND)
        lignes = _lignes(cursor, """
            SELECT c.idcontrat AS "IdContrat", a.codeavenant AS "Code", TRIM(a.libelleavenant) AS "Mouvement",
                   TRIM(COALESCE(c.numeroavenant, '')) AS "NumeroAvenant", c.dateemission::date AS "DateEmission",
                   c.dateeffet::date AS "DateEffet", c.dateexpiration::date AS "DateExpiration", c.primettc AS "PrimeTtc",
                   COALESCE(c.idcontratannulation, 0) <> 0 AS "Annule", TRIM(COALESCE(q.numeroquittance, '')) AS "Quittance",
                   TRIM(COALESCE(c.motifannulation, '')) AS "Motif"
            FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
            LEFT JOIN stdquittance q ON q.idquittance = c.idquittance
            WHERE c.numeropolice = %s
            ORDER BY c.dateeffet DESC, c.idcontrat DESC
            LIMIT 200
        """, [police[0]["numeropolice"]])
    for ligne in lignes:
        for cle in ("DateEmission", "DateEffet", "DateExpiration"):
            ligne[cle] = _iso(ligne[cle])
        ligne["PrimeTtc"] = _nombre(ligne["PrimeTtc"])
        ligne["Document"] = ligne["Code"] in LIBELLES
    return Response({"NumeroPolice": police[0]["numeropolice"], "Lignes": lignes})


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def document(request, pk):
    """Données de l'avenant imprimé (retrait, résiliation, changement d'immatriculation) : contrat, objets, montants."""
    with connection.cursor() as cursor:
        entete = _lignes(cursor, """
            SELECT c.idcontrat, a.codeavenant, TRIM(a.libelleavenant) AS mouvement, c.numeropolice, TRIM(COALESCE(c.numeroavenant, '')) AS numeroavenant,
                   c.dateemission::date AS dateemission, c.dateeffet::date AS dateeffet, c.dateexpiration::date AS dateexpiration,
                   c.primenette, c.fga, c.accessoire, c.taxe, c.primettc, TRIM(COALESCE(c.motifannulation, '')) AS motif,
                   TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client, TRIM(COALESCE(cl.adresse1, '')) AS adresse,
                   TRIM(co.raisonsociale) AS compagnie, TRIM(p.libelleproduit) AS produit, c.idproduit,
                   TRIM(COALESCE(q.numeroquittance, '')) AS quittance, TRIM(COALESCE(c.numeropolicecompagnie, '')) AS policecompagnie,
                   (SELECT b.dateexpiration::date FROM stdcontrat b WHERE b.idcontrat = c.idoldhist) AS echeance
            FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
            LEFT JOIN stdclient cl ON cl.idclient = c.idclient LEFT JOIN stdcompagnie co ON co.idcompagnie = c.idcompagnie
            LEFT JOIN stdproduit p ON p.idproduit = c.idproduit LEFT JOIN stdquittance q ON q.idquittance = c.idquittance
            WHERE c.idcontrat = %s""", [pk])
        if not entete or entete[0]["codeavenant"] not in LIBELLES:
            return Response({"error": "Ce contrat n'est pas un avenant de retrait, de résiliation ou de changement d'immatriculation."},
                            status=status.HTTP_404_NOT_FOUND)
        e = entete[0]
        lignes = _lignes(cursor, """
            SELECT TRIM(COALESCE(d.matricule, '')) AS matricule, TRIM(COALESCE(d.oldmatricule, '')) AS ancienne,
                   NULLIF(TRIM(COALESCE(m.libellemarque, '') || ' ' || COALESCE(d.modelevehicule, '')), '') AS vehicule,
                   NULLIF(TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')), '') AS personne,
                   NULLIF(TRIM(COALESCE(d.observation, '')), '') AS observation, d.primenette, d.fga, d.taxeenregistrement AS taxe
            FROM stdcontratdetail d JOIN stdcontrat c ON c.idcontrat = d.idcontrat
            LEFT JOIN stdmarque m ON m.idmarque = d.idmarque
            LEFT JOIN stdclient cl ON c.idproduit IN (2, 10)
                 AND cl.idclient = CASE WHEN TRIM(d.matricule) ~ '^0*[1-9][0-9]{0,17}$' THEN LTRIM(TRIM(d.matricule), '0')::bigint END
            WHERE d.idcontrat = %s ORDER BY d.idcontratdetail""", [pk])
    return Response({
        "Type": e["codeavenant"], "Libelle": LIBELLES[e["codeavenant"]], "NumeroPolice": e["numeropolice"],
        "PoliceCompagnie": e["policecompagnie"], "NumeroAvenant": e["numeroavenant"], "Quittance": e["quittance"],
        "DateEmission": _iso(e["dateemission"]), "DateEffet": _iso(e["dateeffet"]), "Echeance": _iso(e["echeance"]),
        "Client": e["client"], "Adresse": e["adresse"], "Compagnie": e["compagnie"], "Produit": e["produit"],
        "Automobile": e["idproduit"] == ID_PRODUIT_AUTO, "Motif": e["motif"],
        "PrimeNette": _nombre(e["primenette"]), "Fga": _nombre(e["fga"]), "Accessoire": _nombre(e["accessoire"]),
        "Taxe": _nombre(e["taxe"]), "PrimeTtc": _nombre(e["primettc"]),
        "Objets": [{
            "Matricule": l["matricule"], "Ancienne": l["ancienne"],
            "Libelle": " - ".join(x for x in (l["matricule"], l["vehicule"]) if x) if e["idproduit"] == ID_PRODUIT_AUTO
            else (l["personne"] or l["observation"] or l["matricule"] or e["produit"]),
            "PrimeNette": _nombre(l["primenette"]), "Taxe": _nombre(l["taxe"]),
        } for l in lignes],
    })
