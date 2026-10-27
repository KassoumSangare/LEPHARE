"""
Cockpit opérationnel (/user/dashboard) : chiffres réels de la base, en un appel, chaque bloc selon les droits de
l'utilisateur (production, devis, caisse, reversements, commissions, sinistres, suivi commercial).

GET /api/cockpit/
"""
from datetime import date, timedelta

from django.db import connection
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from autorisations.rbac import a_le_droit
from configuration_api.parametrage import valeur_parametre

from . import views_finance
from .views_reprise import AUTHENTIFICATION

# Échéances suivies : contrats échus depuis moins de … jours (non renouvelés) et à échoir d'ici …
ECHUS_DEPUIS_JOURS = 30
ECHEANCE_JOURS = 30
LIGNES_LISTE = 8
# Sinistres et questionnaires dont le traitement est terminé
SINISTRES_CLOS = ("Réglé", "Clôturé", "Rejeté")
QUESTIONNAIRE_TRAITE = "Devis établi"

CONTRAT_VALIDE = "COALESCE(c.idcontratannulation, 0) = 0"
# Devis du registre (vue Production) : ni archivé ni confirmé, hors devis d'affaires antérieures à finaliser
DEVIS_NON_CONFIRME = """COALESCE(d.archive, FALSE) = FALSE AND COALESCE(d.confirme, FALSE) = FALSE
    AND d.iddevis NOT IN (SELECT iddevis FROM lephare_reprise_devis)
    AND LOWER(COALESCE(d.statut, '')) NOT LIKE '%%confirm%%' AND LOWER(COALESCE(d.statut, '')) NOT LIKE '%%contrat%%'"""


def _lignes(cursor, sql, params=None):
    cursor.execute(sql, params or [])
    colonnes = [c[0] for c in cursor.description]
    return [dict(zip(colonnes, ligne)) for ligne in cursor.fetchall()]


def _une(cursor, sql, params=None):
    return _lignes(cursor, sql, params)[0]


def _franc(valeur):
    return round(float(valeur or 0))


def _iso(valeur):
    return valeur.isoformat()[:10] if valeur else None


def _meme_jour(jour, annee):
    try:
        return jour.replace(year=annee)
    except ValueError:  # 29 février
        return jour.replace(year=annee, day=28)


def _production(cursor, jour):
    debut, debut_mois = date(jour.year, 1, 1), jour.replace(day=1)
    debut_n1, jour_n1 = date(jour.year - 1, 1, 1), _meme_jour(jour, jour.year - 1)
    total = _une(cursor, f"""
        SELECT COUNT(*) FILTER (WHERE c.dateemission::date BETWEEN %(debut)s AND %(jour)s) AS nombre,
               COALESCE(SUM(c.primettc) FILTER (WHERE c.dateemission::date BETWEEN %(debut)s AND %(jour)s), 0) AS ttc,
               COUNT(*) FILTER (WHERE c.dateemission::date BETWEEN %(debut_mois)s AND %(jour)s) AS nombre_mois,
               COALESCE(SUM(c.primettc) FILTER (WHERE c.dateemission::date BETWEEN %(debut_mois)s AND %(jour)s), 0) AS ttc_mois,
               COUNT(*) FILTER (WHERE c.dateemission::date BETWEEN %(debut_n1)s AND %(jour_n1)s) AS nombre_n1,
               COALESCE(SUM(c.primettc) FILTER (WHERE c.dateemission::date BETWEEN %(debut_n1)s AND %(jour_n1)s), 0) AS ttc_n1,
               COUNT(*) FILTER (WHERE a.codeavenant = 'AFN' AND c.dateemission::date BETWEEN %(debut)s AND %(jour)s) AS nouvelles,
               COUNT(*) FILTER (WHERE a.codeavenant = 'REN' AND c.dateemission::date BETWEEN %(debut)s AND %(jour)s) AS renouvellements
        FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
        WHERE {CONTRAT_VALIDE} AND c.dateemission::date BETWEEN %(debut_n1)s AND %(jour)s
    """, {"debut": debut, "jour": jour, "debut_mois": debut_mois, "debut_n1": debut_n1, "jour_n1": jour_n1})
    branches = _lignes(cursor, f"""
        SELECT c.idproduit, COALESCE(p.libelleproduit, 'Autres') AS branche, COUNT(*) AS nombre, SUM(c.primettc) AS ttc
        FROM stdcontrat c LEFT JOIN stdproduit p ON p.idproduit = c.idproduit
        WHERE {CONTRAT_VALIDE} AND c.dateemission::date BETWEEN %s AND %s
        GROUP BY 1, 2 ORDER BY 4 DESC NULLS LAST
    """, [debut, jour])
    # Polices en vigueur : période d'affaire nouvelle ou de renouvellement qui couvre le jour, police non résiliée
    en_vigueur = _une(cursor, f"""
        SELECT COUNT(DISTINCT c.numeropolice) AS n FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
        WHERE {CONTRAT_VALIDE} AND a.codeavenant IN ('AFN', 'REN') AND %s BETWEEN c.dateeffet::date AND c.dateexpiration::date
          AND NOT EXISTS (SELECT 1 FROM stdcontrat r JOIN stdavenant ra ON ra.idavenant = r.idavenant
                          WHERE r.numeropolice = c.numeropolice AND ra.codeavenant = 'RES'
                            AND COALESCE(r.idcontratannulation, 0) = 0 AND r.dateeffet >= c.dateeffet)
    """, [jour])["n"]
    # Échéances : dernière période (affaire nouvelle ou renouvellement) de chaque police, sans renouvellement
    # plus récent ni résiliation, échue depuis peu ou à échoir
    echeances = _lignes(cursor, f"""
        SELECT c.idcontrat, c.iddevis, c.numeropolice, c.dateexpiration::date AS dateexpiration, c.primettc,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client, p.libelleproduit AS produit,
               co.raisonsociale AS compagnie,
               -- Devis de renouvellement déjà préparé (page de renouvellement : rattaché au devis du contrat)
               EXISTS (SELECT 1 FROM stddevis d JOIN stdavenant da ON da.idavenant = d.idavenant
                       WHERE da.codeavenant = 'REN' AND NOT COALESCE(d.confirme, FALSE) AND NOT COALESCE(d.archive, FALSE)
                         AND d.idoldhist = c.iddevis) AS devis_en_cours
        FROM stdcontrat c
        JOIN stdavenant a ON a.idavenant = c.idavenant
        LEFT JOIN stdclient cl ON cl.idclient = c.idclient
        LEFT JOIN stdproduit p ON p.idproduit = c.idproduit
        LEFT JOIN stdcompagnie co ON co.idcompagnie = c.idcompagnie
        WHERE {CONTRAT_VALIDE} AND a.codeavenant IN ('AFN', 'REN')
          AND c.dateexpiration::date BETWEEN %s AND %s
          AND NOT EXISTS (SELECT 1 FROM stdcontrat r JOIN stdavenant ra ON ra.idavenant = r.idavenant
                          WHERE r.numeropolice = c.numeropolice AND COALESCE(r.idcontratannulation, 0) = 0
                            AND ((ra.codeavenant = 'REN' AND r.dateeffet > c.dateeffet)
                                 OR (ra.codeavenant = 'RES' AND r.dateeffet >= c.dateeffet)))
        ORDER BY c.dateexpiration, c.idcontrat
    """, [jour - timedelta(days=ECHUS_DEPUIS_JOURS), jour + timedelta(days=ECHEANCE_JOURS)])
    derniers = _lignes(cursor, f"""
        SELECT c.idcontrat, c.numeropolice, c.dateemission::date AS dateemission, c.dateeffet::date AS dateeffet,
               c.dateexpiration::date AS dateexpiration, c.primettc, a.libelleavenant AS avenant,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client, p.libelleproduit AS produit,
               co.raisonsociale AS compagnie, GREATEST(COALESCE(q.primettc, 0) - COALESCE(q.mt_encaisse, 0), 0) AS reste
        FROM stdcontrat c
        JOIN stdavenant a ON a.idavenant = c.idavenant
        LEFT JOIN stdquittance q ON q.idquittance = c.idquittance
        LEFT JOIN stdclient cl ON cl.idclient = c.idclient
        LEFT JOIN stdproduit p ON p.idproduit = c.idproduit
        LEFT JOIN stdcompagnie co ON co.idcompagnie = c.idcompagnie
        WHERE {CONTRAT_VALIDE} AND c.dateemission::date <= %s
        ORDER BY c.dateemission DESC, c.idcontrat DESC
        LIMIT %s
    """, [jour, LIGNES_LISTE])
    return {
        "Annee": {"Nombre": total["nombre"], "PrimeTtc": _franc(total["ttc"]),
                  "AffairesNouvelles": total["nouvelles"], "Renouvellements": total["renouvellements"]},
        "Mois": {"Nombre": total["nombre_mois"], "PrimeTtc": _franc(total["ttc_mois"])},
        "AnneePrecedente": {"Nombre": total["nombre_n1"], "PrimeTtc": _franc(total["ttc_n1"]), "Au": _iso(jour_n1)},
        "ParBranche": [{"IdProduit": b["idproduit"], "Branche": b["branche"], "Nombre": b["nombre"], "PrimeTtc": _franc(b["ttc"])}
                       for b in branches],
        "PolicesEnVigueur": en_vigueur,
        "Echeances": {
            "Echues": sum(1 for e in echeances if e["dateexpiration"] < jour),
            "AEchoir": sum(1 for e in echeances if e["dateexpiration"] >= jour),
            "Lignes": [{
                "IdContrat": e["idcontrat"], "NumeroPolice": e["numeropolice"], "Client": e["client"], "Produit": e["produit"],
                "Compagnie": e["compagnie"], "DateExpiration": _iso(e["dateexpiration"]),
                "Jours": (e["dateexpiration"] - jour).days, "PrimeTtc": _franc(e["primettc"]), "DevisEnCours": e["devis_en_cours"],
            # Les plus proches du jour, dans l'ordre des dates
            } for e in sorted(sorted(echeances, key=lambda e: abs((e["dateexpiration"] - jour).days))[:LIGNES_LISTE],
                              key=lambda e: (e["dateexpiration"], e["idcontrat"]))],
        },
        "Derniers": [{
            "IdContrat": c["idcontrat"], "NumeroPolice": c["numeropolice"], "Client": c["client"], "Produit": c["produit"],
            "Compagnie": c["compagnie"], "Avenant": c["avenant"], "DateEmission": _iso(c["dateemission"]),
            "DateEffet": _iso(c["dateeffet"]), "DateExpiration": _iso(c["dateexpiration"]),
            "PrimeTtc": _franc(c["primettc"]), "Reste": _franc(c["reste"]),
        } for c in derniers],
    }


def _devis(cursor, jour):
    # Mêmes fenêtres que la vue Production : devis en cours émis durant les N dernières années, devis expirés émis
    # depuis le 1er janvier de l'année N - k (Administration > Le cabinet)
    annees = int(valeur_parametre("devis.registre_annees", 3))
    annees_expires = int(valeur_parametre("devis.registre_expires_annees", 1))
    limite = _meme_jour(jour, jour.year - annees)
    debut_expires = date(jour.year - annees_expires, 1, 1)
    compte = _une(cursor, f"""
        SELECT COUNT(*) FILTER (WHERE {DEVIS_NON_CONFIRME} AND d.dateexpiration::date >= %(jour)s AND d.dateemission::date >= %(limite)s) AS en_cours,
               COALESCE(SUM(d.primettc) FILTER (WHERE {DEVIS_NON_CONFIRME} AND d.dateexpiration::date >= %(jour)s
                                                  AND d.dateemission::date >= %(limite)s), 0) AS ttc_en_cours,
               COUNT(*) FILTER (WHERE {DEVIS_NON_CONFIRME} AND d.dateexpiration::date < %(jour)s AND d.dateemission::date >= %(debut_expires)s) AS expires,
               COUNT(*) FILTER (WHERE d.dateemission::date BETWEEN %(debut)s AND %(jour)s) AS emis,
               COUNT(*) FILTER (WHERE d.dateemission::date BETWEEN %(debut)s AND %(jour)s AND COALESCE(d.confirme, FALSE)) AS confirmes
        FROM stddevis d
        WHERE d.dateemission::date >= LEAST(%(limite)s, %(debut_expires)s)
    """, {"jour": jour, "limite": limite, "debut_expires": debut_expires, "debut": date(jour.year, 1, 1)})
    derniers = _lignes(cursor, f"""
        SELECT d.iddevis, d.numerodevis, d.idproduit, d.dateemission::date AS dateemission,
               d.dateexpiration::date AS dateexpiration, d.primettc,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client, p.libelleproduit AS produit,
               co.raisonsociale AS compagnie
        FROM stddevis d
        LEFT JOIN stdclient cl ON cl.idclient = d.idclient
        LEFT JOIN stdproduit p ON p.idproduit = d.idproduit
        LEFT JOIN stdcompagnie co ON co.idcompagnie = d.idcompagnie
        WHERE {DEVIS_NON_CONFIRME} AND d.dateexpiration::date >= %s AND d.dateemission::date >= %s
        ORDER BY d.dateemission DESC, d.iddevis DESC
        LIMIT %s
    """, [jour, limite, LIGNES_LISTE])
    return {
        "EnCours": compte["en_cours"], "PrimeTtcEnCours": _franc(compte["ttc_en_cours"]),
        "Expires": compte["expires"], "ExpiresDepuis": _iso(debut_expires),
        "EmisAnnee": compte["emis"], "ConfirmesAnnee": compte["confirmes"],
        "TauxTransformation": round(compte["confirmes"] * 100 / compte["emis"], 1) if compte["emis"] else 0.0,
        "Derniers": [{
            "IdDevis": d["iddevis"], "NumeroDevis": d["numerodevis"] or f"DEV-{d['iddevis']}", "IdProduit": d["idproduit"],
            "Client": d["client"], "Produit": d["produit"], "Compagnie": d["compagnie"],
            "DateEmission": _iso(d["dateemission"]), "DateExpiration": _iso(d["dateexpiration"]),
            "Jours": (d["dateexpiration"] - jour).days if d["dateexpiration"] else None, "PrimeTtc": _franc(d["primettc"]),
        } for d in derniers],
    }


def _caisse(cursor, jour):
    debut, debut_mois = date(jour.year, 1, 1), jour.replace(day=1)
    # Décaissement de prime mal affectée : compté en négatif, comme l'état des encaissements
    montant = "CASE WHEN UPPER(TRIM(COALESCE(m.abregereglement, ''))) = ANY(%(decaissements)s) THEN -de.montant_encaissement ELSE de.montant_encaissement END"
    encaisse = _une(cursor, f"""
        SELECT COUNT(DISTINCT e.idencaissement) FILTER (WHERE e.dateencaissement::date >= %(debut_mois)s) AS pieces_mois,
               COALESCE(SUM({montant}) FILTER (WHERE e.dateencaissement::date >= %(debut_mois)s), 0) AS mois,
               COUNT(DISTINCT e.idencaissement) AS pieces_annee, COALESCE(SUM({montant}), 0) AS annee
        FROM stddetailencaissement de
        JOIN stdencaissement e ON e.idencaissement = de.idencaissement
        LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
        WHERE NOT COALESCE(e.piece_annulee, FALSE) AND e.dateencaissement::date BETWEEN %(debut)s AND %(jour)s
    """, {"debut": debut, "debut_mois": debut_mois, "jour": jour, "decaissements": sorted(views_finance.MODES_DECAISSEMENT)})
    # Reste à encaisser : même règle que la caisse (quittance du contrat non soldée)
    reste = _une(cursor, f"""
        SELECT COUNT(*) FILTER (WHERE q.dateemission::date >= %(debut)s) AS nombre,
               COALESCE(SUM(q.primettc - COALESCE(q.mt_encaisse, 0)) FILTER (WHERE q.dateemission::date >= %(debut)s), 0) AS montant,
               COUNT(*) FILTER (WHERE q.dateemission::date < %(debut)s) AS nombre_ant,
               COALESCE(SUM(q.primettc - COALESCE(q.mt_encaisse, 0)) FILTER (WHERE q.dateemission::date < %(debut)s), 0) AS montant_ant
        FROM stdquittance q
        WHERE q.primettc - COALESCE(q.mt_encaisse, 0) > 0
          AND EXISTS (SELECT 1 FROM stdcontrat c WHERE c.idquittance = q.idquittance AND c.numeropolice = q.numeropolice
                        AND {CONTRAT_VALIDE})
    """, {"debut": debut})
    cheques = _une(cursor, """
        SELECT COUNT(*) FILTER (WHERE dateecheance <= %s) AS a_deposer, COUNT(*) FILTER (WHERE dateecheance < %s) AS echus,
               COALESCE(SUM(montantinitial) FILTER (WHERE dateecheance <= %s), 0) AS montant
        FROM stdcheque WHERE statut = 'A_DEPOSER'
    """, [jour + timedelta(days=31), jour, jour + timedelta(days=31)])
    return {
        "Mois": {"Pieces": encaisse["pieces_mois"], "Montant": _franc(encaisse["mois"])},
        "Annee": {"Pieces": encaisse["pieces_annee"], "Montant": _franc(encaisse["annee"])},
        "ResteAEncaisser": {
            "Nombre": reste["nombre"], "Montant": _franc(reste["montant"]),
            "NombreAnterieur": reste["nombre_ant"], "MontantAnterieur": _franc(reste["montant_ant"]),
        },
        "Cheques": {"ADeposer": cheques["a_deposer"], "Echus": cheques["echus"], "Montant": _franc(cheques["montant"])},
    }


def _reversements():
    """Primes encaissées à reverser aux compagnies : mêmes lignes que l'écran des reversements, toutes compagnies."""
    lignes = views_finance._lignes(
        views_finance.SQL_LIGNES_ENCAISSEMENT + """
        WHERE NOT COALESCE(e.piece_annulee, FALSE) AND de.montant_encaissement > COALESCE(de.montantreglement, 0)
          AND e.dateencaissement::date >= %s
        """,
        [views_finance.debut_reversements()],
    )
    restes = views_finance._restes_nets({l["numeroquittance"] for l in lignes})
    a_reverser = [l for l in (views_finance._ligne_encaissement(l, restes) for l in lignes if not views_finance._est_decaissement(l))
                  if l["ResteAReverser"] > 0]
    plus_ancien = min((l["DateEncaissement"] for l in a_reverser if l["DateEncaissement"]), default=None)
    return {
        "Nombre": len(a_reverser), "Montant": _franc(sum(l["ResteAReverser"] for l in a_reverser)),
        "Compagnies": len({l["IdCompagnie"] for l in a_reverser}), "PlusAncien": plus_ancien,
    }


def _commissions(jour):
    recap = views_finance.recapitulatif_commissions(jour=jour)
    total = recap["Total"]
    return {
        "AReclamer": _franc(total["EnAttenteAReclamer"]), "Reclamees": _franc(total["EnAttenteReclamee"]),
        "Payees": _franc(total["CommissionPayee"]), "TauxRecouvrement": total["TauxRecouvrement"],
        "BordereauxEnAttente": len(recap["Reclamations"]),
    }


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def cockpit(request):
    jour = timezone.localdate()
    utilisateur = request.user
    resultat = {"Jour": jour.isoformat(), "Exercice": jour.year}
    with connection.cursor() as cursor:
        if a_le_droit(utilisateur, "contrats.view"):
            resultat["Production"] = _production(cursor, jour)
        if a_le_droit(utilisateur, "devis.view"):
            resultat["Devis"] = _devis(cursor, jour)
        if a_le_droit(utilisateur, "encaissements.view"):
            resultat["Caisse"] = _caisse(cursor, jour)
        if a_le_droit(utilisateur, "sinistres.view"):
            s = _une(cursor, "SELECT COUNT(*) AS n, COALESCE(SUM(montant_reclame), 0) AS m FROM institutionnel_sinistredelegue "
                             "WHERE statut <> ALL(%s)", [list(SINISTRES_CLOS)])
            resultat["Sinistres"] = {"Ouverts": s["n"], "MontantReclame": _franc(s["m"])}
        if a_le_droit(utilisateur, "crm.view"):
            resultat["Questionnaires"] = {"ATraiter": _une(
                cursor, "SELECT COUNT(*) AS n FROM lephare_questionnaire_prospect WHERE statut <> %s", [QUESTIONNAIRE_TRAITE])["n"]}
    if a_le_droit(utilisateur, "reversements.view"):
        resultat["Reversements"] = _reversements()
    if a_le_droit(utilisateur, "commissions.view"):
        resultat["Commissions"] = _commissions(jour)
    return Response(resultat)


# Cloche de la barre du haut : alertes à suivre, et non plus le journal des messages affichés (consigne du 2026-10-26 :
# « pas besoin d'incrémenter la cloche quand on enregistre un devis, un contrat… : affiche juste le message »)
ALERTE_ECHEANCE_JOURS = 30
ALERTES_MAX = 50


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def alertes(request):
    """
    GET /api/alertes/ : alertes de la cloche, selon les droits.

    Devis (devis.view) : devis non confirmés dont l'échéance (date d'expiration) tombe dans les N prochains jours, ou
    échus depuis N jours au plus (la confirmation d'un devis expiré est bloquée : il faut relancer le client avant).
    N = « devis.alerte_echeance_jours » (Administration > Le cabinet, 30 par défaut). Les saisies jamais enregistrées
    (sans numéro) et les devis à prime nulle sont écartés. Les chèques à déposer restent lus par /api/chequesalertes/.
    """
    jour = timezone.localdate()
    resultat = {"Jour": jour.isoformat()}
    if a_le_droit(request.user, "devis.view"):
        jours = int(valeur_parametre("devis.alerte_echeance_jours", ALERTE_ECHEANCE_JOURS))
        with connection.cursor() as cursor:
            lignes = _lignes(cursor, f"""
                SELECT d.iddevis, d.numerodevis, d.idproduit, d.dateexpiration::date AS dateexpiration, d.primettc,
                       TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client, p.libelleproduit AS produit
                FROM stddevis d
                LEFT JOIN stdclient cl ON cl.idclient = d.idclient
                LEFT JOIN stdproduit p ON p.idproduit = d.idproduit
                WHERE {DEVIS_NON_CONFIRME} AND COALESCE(TRIM(d.numerodevis), '') <> '' AND COALESCE(d.primettc, 0) > 0
                  AND d.dateexpiration::date BETWEEN %s AND %s
                ORDER BY d.dateexpiration, d.iddevis
                LIMIT %s
            """, [jour - timedelta(days=jours), jour + timedelta(days=jours), ALERTES_MAX])
        devis = [{
            "IdDevis": d["iddevis"], "NumeroDevis": d["numerodevis"], "IdProduit": d["idproduit"], "Produit": d["produit"],
            "Client": d["client"], "DateExpiration": _iso(d["dateexpiration"]), "Jours": (d["dateexpiration"] - jour).days,
            "PrimeTtc": _franc(d["primettc"]),
        } for d in lignes]
        resultat["Devis"] = {
            "Jours": jours,
            "AEcheance": [d for d in devis if d["Jours"] >= 0],
            "Echus": sorted((d for d in devis if d["Jours"] < 0), key=lambda d: d["Jours"], reverse=True),
        }
    return Response(resultat)
