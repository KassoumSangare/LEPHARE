"""
Registre des avenants (demande du 2026-11-20 : « regarde comment il fonctionne et met-le à jour en fonction de comment les
avenants fonctionnent »). L'ancien écran lisait des avenants enregistrés dans le navigateur et la liste des TYPES d'avenant
(/api/avenant/) présentée comme des actes.

Un avenant est un contrat de la police (stdcontrat) : code de mouvement (stdavenant), numéro d'avenant, période, quittance.
Le registre lit donc :
- les actes émis : renouvellements, incorporations, modifications (Santé), retraits, résiliations, changements
  d'immatriculation, annulations d'URANUS et autres actes (certificats Transport, attestations…) ; affaires nouvelles,
  reprises et transferts de portefeuille exclus (portefeuille des contrats), comme l'avenant de paramétrage FIC ;
- les avenants en préparation : devis d'avenant non confirmés (renouvellement, incorporation, modification Santé), qui se
  continuent dans leur écran de saisie puis se confirment. Le retrait, la résiliation et le changement d'immatriculation
  s'émettent directement (production/avenants.py) : ils n'ont pas de préparation.

GET /api/avenants/registre/?etat=emis|preparation&type=REN|INC|MOD|RET|RES|CHI|ANL|AUTRES&q=&du=&au=&page=&taille=
Période : date d'émission de l'acte (du devis en préparation) ; par défaut, l'exercice en cours.
"""

from collections import OrderedDict
from datetime import date, datetime

from django.db import DatabaseError, connection
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .renouvellement import AUTHENTIFICATION, _lignes
from .views_bordereaux import _branche

TYPES = OrderedDict([
    ("REN", ("Renouvellements", ("REN",))),
    ("INC", ("Incorporations", ("INC",))),
    ("MOD", ("Modifications", ("MOD",))),
    ("RET", ("Retraits", ("RET",))),
    ("RES", ("Résiliations", ("RES",))),
    ("CHI", ("Changements d'immatriculation", ("CHI",))),
    ("ANL", ("Annulations", ("ANL", "ANP"))),
])
CODES_EXCLUS = ("AFN", "RPP", "TRP", "FIC")
CODES_TYPES = tuple(code for _, codes in TYPES.values() for code in codes)
TAILLE_DEFAUT, TAILLE_MAX = 50, 500

# Type de l'acte (onglet du registre) d'après son code de mouvement
SQL_TYPE = "CASE " + " ".join(
    f"WHEN TRIM(a.codeavenant) IN ({', '.join(repr(c) for c in codes)}) THEN '{cle}'" for cle, (_, codes) in TYPES.items()
) + " ELSE 'AUTRES' END"


class ErreurRegistre(Exception):
    """Filtre refusé : message affiché tel quel."""


def _iso(valeur):
    if isinstance(valeur, datetime):
        valeur = valeur.date()
    return valeur.isoformat() if isinstance(valeur, date) else None


def _date(valeur, libelle):
    if not valeur:
        return None
    try:
        return date.fromisoformat(str(valeur)[:10])
    except ValueError as erreur:
        raise ErreurRegistre(f"{libelle} : date invalide.") from erreur


def _entier(valeur, defaut, minimum=1, maximum=None):
    try:
        nombre = int(valeur)
    except (TypeError, ValueError):
        return defaut
    nombre = max(minimum, nombre)
    return min(nombre, maximum) if maximum else nombre


def _nombre(valeur):
    nombre = float(valeur or 0)
    return 0.0 if nombre != nombre else nombre  # NaN des devis importés


def _filtres(params, alias):
    """Conditions communes : période, type, recherche. alias : table de l'acte (c contrat, d devis)."""
    jour = timezone.localdate()
    du = _date(params.get("du"), "Du") or date(jour.year, 1, 1)
    au = _date(params.get("au"), "Au") or jour
    if au < du:
        raise ErreurRegistre("La fin de la période précède son début.")
    conditions = [f"TRIM(a.codeavenant) NOT IN {CODES_EXCLUS}", f"{alias}.dateemission::date BETWEEN %(du)s AND %(au)s"]
    valeurs = {"du": du, "au": au}
    mots = [m for m in str(params.get("q") or "").strip().split() if m][:6]
    for i, mot in enumerate(mots):
        valeurs[f"q{i}"] = f"%{mot}%"
        conditions.append(
            f"""(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '') || ' ' || COALESCE({{police}}, '') || ' '
                 || COALESCE({alias}.numeroavenant, '') || ' ' || COALESCE({alias}.numeropolicecompagnie, '') || ' '
                 || COALESCE(cie.raisonsociale, '') || ' ' || COALESCE({{quittance}}, '') || ' ' || COALESCE(p.libelleproduit, '')) ILIKE %(q{i})s""")
    return du, au, conditions, valeurs


def _type_condition(params, valeurs):
    type_ = str(params.get("type") or "").upper()
    if not type_:
        return []
    if type_ == "AUTRES":
        return [f"TRIM(a.codeavenant) NOT IN {CODES_TYPES}"]
    if type_ not in TYPES:
        raise ErreurRegistre("Type d'acte inconnu.")
    valeurs["codes"] = list(TYPES[type_][1])
    return ["TRIM(a.codeavenant) = ANY(%(codes)s)"]


def _compteurs(cursor, sql_from, conditions, valeurs):
    lignes = _lignes(cursor, f"SELECT {SQL_TYPE} AS type, COUNT(*) AS n FROM {sql_from} WHERE {' AND '.join(conditions)} GROUP BY 1", valeurs)
    compteurs = {cle: 0 for cle in list(TYPES) + ["AUTRES"]}
    for l in lignes:
        compteurs[l["type"]] = l["n"]
    return compteurs


FROM_EMIS = """stdcontrat c
    JOIN stdavenant a ON a.idavenant = c.idavenant
    LEFT JOIN stdquittance q ON q.idquittance = c.idquittance
    LEFT JOIN stdclient cl ON cl.idclient = c.idclient
    LEFT JOIN stdcompagnie cie ON cie.idcompagnie = c.idcompagnie
    LEFT JOIN stdproduit p ON p.idproduit = c.idproduit"""

FROM_PREPARATION = """stddevis d
    JOIN stdavenant a ON a.idavenant = d.idavenant
    LEFT JOIN LATERAL (SELECT b.idcontrat, b.numeropolice FROM stdcontrat b WHERE b.iddevis = d.idoldhist
                       ORDER BY b.idcontrat DESC LIMIT 1) base ON TRUE
    LEFT JOIN stdclient cl ON cl.idclient = d.idclient
    LEFT JOIN stdcompagnie cie ON cie.idcompagnie = d.idcompagnie
    LEFT JOIN stdproduit p ON p.idproduit = d.idproduit"""


def registre_emis(cursor, params):
    du, au, conditions, valeurs = _filtres(params, "c")
    conditions = [x.replace("{police}", "c.numeropolice").replace("{quittance}", "q.numeroquittance") for x in conditions]
    compteurs = _compteurs(cursor, FROM_EMIS, conditions, valeurs)
    # Synthèse de la période (tous types) : actes, dont annulés ; primes et ristournes des actes non annulés
    totaux = _lignes(cursor, f"""
        SELECT COUNT(*) AS n, COUNT(*) FILTER (WHERE COALESCE(c.idcontratannulation, 0) <> 0) AS annules,
               COALESCE(SUM(NULLIF(c.primettc, 'NaN')) FILTER (WHERE c.primettc > 0 AND COALESCE(c.idcontratannulation, 0) = 0), 0) AS primes,
               COALESCE(-SUM(NULLIF(c.primettc, 'NaN')) FILTER (WHERE c.primettc < 0 AND COALESCE(c.idcontratannulation, 0) = 0), 0) AS ristournes
        FROM {FROM_EMIS} WHERE {' AND '.join(conditions)}""", valeurs)[0]
    conditions += _type_condition(params, valeurs)
    where = " AND ".join(conditions)
    total = _lignes(cursor, f"SELECT COUNT(*) AS n FROM {FROM_EMIS} WHERE {where}", valeurs)[0]["n"]
    taille = _entier(params.get("taille"), TAILLE_DEFAUT, maximum=TAILLE_MAX)
    page = _entier(params.get("page"), 1)
    valeurs.update({"limite": taille, "decalage": (page - 1) * taille})
    lignes = _lignes(cursor, f"""
        SELECT c.idcontrat, {SQL_TYPE} AS type, TRIM(a.codeavenant) AS code, TRIM(a.libelleavenant) AS libelle,
               TRIM(COALESCE(c.numeroavenant, '')) AS numeroavenant, TRIM(COALESCE(c.numeroavenantcompagnie, '')) AS avenantcompagnie,
               TRIM(COALESCE(c.numeropolice, '')) AS police, c.idproduit, TRIM(COALESCE(p.libelleproduit, '')) AS branche,
               COALESCE(c.flotte, FALSE) AS flotte, TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client,
               TRIM(COALESCE(cie.raisonsociale, '')) AS compagnie, c.dateemission::date AS dateemission, c.dateeffet::date AS dateeffet,
               c.dateexpiration::date AS dateexpiration, NULLIF(c.primettc, 'NaN') AS primettc, TRIM(COALESCE(q.numeroquittance, '')) AS quittance,
               NULLIF(q.primettc, 'NaN') - COALESCE(NULLIF(q.mt_encaisse, 'NaN'), 0) AS restequittance,
               TRIM(COALESCE(c.motifannulation, '')) AS motif, COALESCE(c.idcontratannulation, 0) <> 0 AS annule,
               TRIM(COALESCE(u.name, '')) AS operateur,
               (SELECT COUNT(*) FROM stdcontratdetail x WHERE x.idcontrat = c.idcontrat) AS objets
        FROM {FROM_EMIS}
        LEFT JOIN account_uranususer u ON u.id = c.idoperateur
        WHERE {where}
        ORDER BY c.dateemission DESC, c.idcontrat DESC
        LIMIT %(limite)s OFFSET %(decalage)s""", valeurs)
    return {
        "Etat": "emis", "Du": _iso(du), "Au": _iso(au), "Page": page, "Taille": taille, "Total": total, "Compteurs": compteurs,
        "Totaux": {"Actes": totaux["n"], "Annules": totaux["annules"], "Primes": round(_nombre(totaux["primes"])), "Ristournes": round(_nombre(totaux["ristournes"]))},
        "Lignes": [{
            "IdContrat": l["idcontrat"], "Type": l["type"], "Code": l["code"], "Libelle": l["libelle"],
            "NumeroAvenant": l["avenantcompagnie"] or l["numeroavenant"], "NumeroPolice": l["police"], "IdProduit": l["idproduit"],
            "Branche": _branche(l["idproduit"], l["branche"]), "Flotte": l["flotte"], "Client": l["client"], "Compagnie": l["compagnie"],
            "DateEmission": _iso(l["dateemission"]), "DateEffet": _iso(l["dateeffet"]), "DateExpiration": _iso(l["dateexpiration"]),
            "PrimeTtc": _nombre(l["primettc"]), "Quittance": l["quittance"],
            # Quittance soldée : prime encaissée, ou ristourne remboursée ou imputée (production/ristournes.py)
            "ResteQuittance": _nombre(l["restequittance"]) if l["quittance"] else None,
            "Motif": l["motif"], "Annule": l["annule"], "Operateur": l["operateur"], "Objets": l["objets"],
        } for l in lignes],
    }


def registre_preparation(cursor, params):
    du, au, conditions, valeurs = _filtres(params, "d")
    conditions = [x.replace("{police}", "base.numeropolice").replace("{quittance}", "d.numerodevis") for x in conditions]
    conditions += ["NOT COALESCE(d.confirme, FALSE)", "COALESCE(d.statut, '') <> 'ARCHIVE'"]
    compteurs = _compteurs(cursor, FROM_PREPARATION, conditions, valeurs)
    conditions += _type_condition(params, valeurs)
    where = " AND ".join(conditions)
    total = _lignes(cursor, f"SELECT COUNT(*) AS n FROM {FROM_PREPARATION} WHERE {where}", valeurs)[0]["n"]
    taille = _entier(params.get("taille"), TAILLE_DEFAUT, maximum=TAILLE_MAX)
    page = _entier(params.get("page"), 1)
    valeurs.update({"limite": taille, "decalage": (page - 1) * taille})
    lignes = _lignes(cursor, f"""
        SELECT d.iddevis, TRIM(COALESCE(d.numerodevis, '')) AS numerodevis, {SQL_TYPE} AS type, TRIM(a.codeavenant) AS code,
               TRIM(a.libelleavenant) AS libelle, base.idcontrat AS idcontratbase, TRIM(COALESCE(base.numeropolice, '')) AS police,
               d.idproduit, TRIM(COALESCE(p.libelleproduit, '')) AS branche, COALESCE(d.flotte, FALSE) AS flotte,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client, TRIM(COALESCE(cie.raisonsociale, '')) AS compagnie,
               d.dateemission::date AS dateemission, d.dateeffet::date AS dateeffet, d.dateexpiration::date AS dateexpiration,
               NULLIF(d.primettc, 'NaN') AS primettc, TRIM(COALESCE(u.name, '')) AS operateur
        FROM {FROM_PREPARATION}
        LEFT JOIN account_uranususer u ON u.id = d.idoperateur
        WHERE {where}
        ORDER BY d.dateemission DESC, d.iddevis DESC
        LIMIT %(limite)s OFFSET %(decalage)s""", valeurs)
    return {
        "Etat": "preparation", "Du": _iso(du), "Au": _iso(au), "Page": page, "Taille": taille, "Total": total, "Compteurs": compteurs,
        "Lignes": [{
            "IdDevis": l["iddevis"], "NumeroDevis": l["numerodevis"], "Type": l["type"], "Code": l["code"], "Libelle": l["libelle"],
            "IdContratBase": l["idcontratbase"], "NumeroPolice": l["police"], "IdProduit": l["idproduit"], "Branche": _branche(l["idproduit"], l["branche"]),
            "Flotte": l["flotte"], "Client": l["client"], "Compagnie": l["compagnie"], "DateEmission": _iso(l["dateemission"]),
            "DateEffet": _iso(l["dateeffet"]), "DateExpiration": _iso(l["dateexpiration"]), "PrimeTtc": _nombre(l["primettc"]),
            "Operateur": l["operateur"],
        } for l in lignes],
    }


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def registre(request):
    params = request.query_params
    try:
        with connection.cursor() as cursor:
            if params.get("etat") == "preparation":
                return Response(registre_preparation(cursor, params))
            return Response(registre_emis(cursor, params))
    except ErreurRegistre as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
    except DatabaseError:
        return Response({"error": "Le registre des avenants ne peut pas être lu pour le moment."}, status=status.HTTP_400_BAD_REQUEST)
