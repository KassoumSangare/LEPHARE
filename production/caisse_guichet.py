"""
Guichet de la caisse, écran « Encaissement des Primes » (demande du 2026-11-25 : « il y a trop d'erreurs ; propose un scénario
d'encaissement moderne qui ne prête pas à ambiguïté »).

L'écran suit quatre étapes : 1. le client, 2. ses quittances, 3. le règlement, 4. la vérification, puis le reçu. Ce module lui
fournit ce qui lui manquait pour lever les ambiguïtés :

- GET caisse/a-encaisser/ : TOUTES les quittances à encaisser. L'écran lisait /api/contrat/?a_encaisser=1, limité aux 200 derniers
  contrats : une quittance plus ancienne n'apparaissait pas et la caissière en choisissait une autre. Chaque ligne porte le client
  (n° d'assuré, téléphone : deux homonymes se distinguent), l'avenant et la période (deux quittances d'une même police se
  distinguent), et ce qui a déjà été réglé aujourd'hui sur la quittance (saisie en double).
  Même règle que /api/contrat/?a_encaisser=1 et que fn_liste_contrat_encaissement d'URANUS : contrat non annulé, quittance du
  contrat à la même police, reste dû d'au moins 5 F (production/reste_encaissement.py).
- GET caisse/clients/<id>/cheques/ : chèques du client qui peuvent encore régler (échéancier à déposer, solde d'un chèque déjà
  utilisé), choisis d'un clic au lieu d'être retapés.

Droit : encaissements.view (autorisations/garde.py), vérifié aussi ici.
"""

import logging

from django.db import DatabaseError, connection
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from autorisations.rbac import a_le_droit
from core.date_parser import date_emission_du_jour

from .decaissements import MODES_EXCLUS
from .renouvellement import AUTHENTIFICATION, _lignes
from .reste_encaissement import RELIQUAT_NEGLIGEABLE, reste_a_encaisser

logger = logging.getLogger(__name__)

SQL_A_ENCAISSER = """
    SELECT ct.idcontrat, TRIM(q.numeroquittance) AS numeroquittance, TRIM(ct.numeropolice) AS numeropolice,
           TRIM(COALESCE(ct.numeropolicecompagnie, '')) AS policecompagnie,
           cl.idclient, TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client,
           TRIM(COALESCE(cl.numero_assure, '')) AS numeroassure,
           COALESCE(NULLIF(TRIM(cl.mobile), ''), NULLIF(TRIM(cl.telephone), ''), NULLIF(TRIM(cl.fixe), ''), '') AS telephone,
           ct.idcompagnie, TRIM(COALESCE(co.raisonsociale, '')) AS compagnie,
           ct.idproduit, TRIM(COALESCE(p.libelleproduit, '')) AS produit,
           UPPER(TRIM(COALESCE(av.codeavenant, ''))) AS codeavenant, TRIM(COALESCE(av.libelleavenant, '')) AS avenant,
           COALESCE(q.dateemission, ct.dateemission)::date AS dateemission,
           COALESCE(q.dateeffet, ct.dateeffet)::date AS dateeffet,
           COALESCE(q.dateexpiration, ct.dateexpiration)::date AS dateexpiration,
           COALESCE(q.primettc, 0) AS primettc, COALESCE(q.mt_encaisse, 0) AS encaisse
    FROM stdcontrat ct
    JOIN stdquittance q ON q.idquittance = ct.idquittance AND q.numeropolice = ct.numeropolice
    LEFT JOIN stdclient cl ON cl.idclient = COALESCE(ct.idclient, q.idclient)
    LEFT JOIN stdcompagnie co ON co.idcompagnie = ct.idcompagnie
    LEFT JOIN stdproduit p ON p.idproduit = ct.idproduit
    LEFT JOIN stdavenant av ON av.idavenant = ct.idavenant
    WHERE ct.idcontratannulation = 0 AND COALESCE(q.primettc, 0) - COALESCE(q.mt_encaisse, 0) >= %s
    ORDER BY ct.idcontrat DESC
"""

# Règlements du jour, par quittance (pièces en cours, hors contre-passations et annulations)
SQL_REGLE_AUJOURDHUI = f"""
    SELECT TRIM(de.numeroquittance) AS numeroquittance, SUM(de.montant_encaissement) AS montant,
           MAX(COALESCE(e.created_at, e.datesaisie)) AS moment,
           (ARRAY_AGG(e.idutilisateur ORDER BY e.idencaissement DESC))[1] AS idutilisateur,
           (ARRAY_AGG(COALESCE(NULLIF(TRIM(u.name), ''), u.email) ORDER BY e.idencaissement DESC))[1] AS operateur
    FROM stdencaissement e
    JOIN stddetailencaissement de ON de.idencaissement = e.idencaissement
    LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
    LEFT JOIN account_uranususer u ON u.id = e.idutilisateur
    WHERE e.dateencaissement::date = %s AND NOT COALESCE(e.piece_annulee, FALSE) AND e.montantencaissement > 0
      AND COALESCE(UPPER(TRIM(m.abregereglement)), '') NOT IN {MODES_EXCLUS}
    GROUP BY 1
"""

# Chèques du client qui ont encore un solde : remis d'avance (échéancier, à déposer) ou déjà utilisés pour une partie
SQL_CHEQUES_CLIENT = """
    SELECT ch.idcheque, TRIM(ch.numerocheque) AS numero, ch.idbanque, TRIM(COALESCE(b.libelle, '')) AS banque,
           ch.montantinitial, ch.soldedisponible, ch.statut, ch.dateecheance
    FROM stdcheque ch
    LEFT JOIN stdbanque b ON b.idbanque = ch.idbanque
    WHERE ch.soldedisponible > 0 AND ch.statut IN ('A_DEPOSER', 'ENCAISSE')
      AND (ch.idclient = %(client)s OR EXISTS (
            SELECT 1 FROM stdchequeoperation op
            JOIN stdencaissement e ON e.idencaissement = op.idencaissement AND NOT COALESCE(e.piece_annulee, FALSE)
            JOIN stddetailencaissement de ON de.idencaissement = e.idencaissement
            JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
            WHERE op.idcheque = ch.idcheque AND q.idclient = %(client)s))
    ORDER BY (ch.statut = 'A_DEPOSER') DESC, ch.dateecheance NULLS LAST, ch.idcheque DESC
    LIMIT 50
"""


def _nombre(valeur):
    return float(valeur) if valeur is not None else 0.0


def _iso(valeur):
    return valeur.isoformat() if hasattr(valeur, "isoformat") else (valeur or "")


def _heure(moment):
    """Heure locale de la saisie (« » si la base ne garde que la date)."""
    if not hasattr(moment, "strftime"):
        return ""
    if getattr(moment, "tzinfo", None) is not None:
        from django.utils import timezone

        moment = timezone.localtime(moment)
    return "" if (moment.hour, moment.minute) == (0, 0) else moment.strftime("%H:%M")


def quittances_a_encaisser(user):
    """Toutes les quittances à encaisser, avec ce qui a été réglé aujourd'hui sur chacune. Le nom de la caissière qui a réglé
    n'est donné qu'avec le droit « Voir qui a encaissé » (encaissements.auteur) ; sinon « vous » ou « un autre utilisateur »."""
    voir_auteur = a_le_droit(user, "encaissements.auteur")
    with connection.cursor() as cursor:
        lignes = _lignes(cursor, SQL_A_ENCAISSER, [RELIQUAT_NEGLIGEABLE])
        aujourdhui = {l["numeroquittance"]: l for l in _lignes(cursor, SQL_REGLE_AUJOURDHUI, [date_emission_du_jour()])}
    resultat = []
    for l in lignes:
        regle = aujourdhui.get(l["numeroquittance"])
        reste = reste_a_encaisser(l["primettc"], l["encaisse"])
        if not reste:
            continue
        ligne = {
            "IdContrat": l["idcontrat"], "NumeroQuittance": l["numeroquittance"], "NumeroPolice": l["numeropolice"],
            "PoliceCompagnie": l["policecompagnie"], "IdClient": l["idclient"], "Client": l["client"],
            "NumeroAssure": l["numeroassure"], "Telephone": l["telephone"], "IdCompagnie": l["idcompagnie"],
            "Compagnie": l["compagnie"], "IdProduit": l["idproduit"], "Produit": l["produit"],
            "CodeAvenant": l["codeavenant"], "Avenant": l["avenant"], "DateEmission": _iso(l["dateemission"]),
            "DateEffet": _iso(l["dateeffet"]), "DateExpiration": _iso(l["dateexpiration"]),
            "PrimeTtc": _nombre(l["primettc"]), "Encaisse": _nombre(l["encaisse"]), "Reste": _nombre(reste),
            "RegleAujourdhui": None,
        }
        if regle:
            par = regle["operateur"] if voir_auteur else ("vous" if regle["idutilisateur"] == user.id else "un autre utilisateur")
            ligne["RegleAujourdhui"] = {"Montant": _nombre(regle["montant"]), "Heure": _heure(regle["moment"]), "Par": par or ""}
        resultat.append(ligne)
    return {"Quittances": resultat}


def cheques_du_client(id_client):
    with connection.cursor() as cursor:
        lignes = _lignes(cursor, SQL_CHEQUES_CLIENT, {"client": id_client})
    return {"Cheques": [{
        "IdCheque": l["idcheque"], "Numero": l["numero"], "IdBanque": l["idbanque"], "Banque": l["banque"],
        "MontantInitial": _nombre(l["montantinitial"]), "Solde": _nombre(l["soldedisponible"]), "Statut": l["statut"],
        "DateEcheance": _iso(l["dateecheance"]),
    } for l in lignes]}


def _refus():
    return Response({"erreur": "Accès refusé : droit « Consulter la caisse » requis."}, status=status.HTTP_403_FORBIDDEN)


def _reponse(fonction, *args):
    try:
        return Response(fonction(*args), status=status.HTTP_200_OK)
    except DatabaseError as erreur:
        logger.exception("Guichet de la caisse : erreur de base")
        return Response({"erreur": str(erreur).split("\n")[0]}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_a_encaisser(request):
    if not a_le_droit(request.user, "encaissements.view"):
        return _refus()
    return _reponse(quittances_a_encaisser, request.user)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_cheques_client(request, id_client):
    if not a_le_droit(request.user, "encaissements.view"):
        return _refus()
    return _reponse(cheques_du_client, id_client)
