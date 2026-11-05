"""
Apporteurs d'affaires : rattachement aux affaires, commissions et règlements (demande du 2026-11-05). La fiche de l'apporteur reste
configuration_api.Apporteur (stdapporteur).

Affaire : un devis et, une fois émis, sa police. Le rattachement couvre le contrat du devis et les mouvements suivants de la même police
(avenants, renouvellements), jusqu'au retrait de l'apporteur. Un montant forfaitaire ne vaut que pour la quittance de son devis.

Taux : copié sur le rattachement à partir du taux général de l'apporteur, puis indépendant de lui. Plusieurs apporteurs peuvent partager une
affaire, chacun avec son taux.

Commission d'une quittance = taux convenu x assiette, arrondie au franc :
- COMMISSION : commission du cabinet (stdcontrat.commissionintermediaire), hors accessoires, assiette par défaut ;
- PRIME_NETTE : prime nette du contrat ;
- FORFAIT : montant convenu.
Une ristourne donne une commission négative, déduite du prochain règlement.

Les lignes de commission sont générées à la lecture (synchroniser), pour couvrir toutes les façons d'émettre une quittance (confirmation,
transport, reprise). À payer : le montant suit le contrat. Payée : figée. Contrat annulé : la ligne à payer est annulée ; si elle était déjà
payée, le mouvement d'annulation porte une ligne négative à déduire. Contrat supprimé : la ligne à payer est annulée.

Une commission se règle en entier. La prime non soldée est signalée, sans bloquer : c'est au cabinet de décider d'une avance.
"""

import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import DatabaseError, IntegrityError, connection, transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .renouvellement import AUTHENTIFICATION, _lignes
from .reste_encaissement import sql_reste

logger = logging.getLogger(__name__)

ZERO = Decimal("0")
ASSIETTES = {"COMMISSION": "Commission du cabinet", "PRIME_NETTE": "Prime nette", "FORFAIT": "Montant convenu"}
ASSIETTES_AU_TAUX = ("COMMISSION", "PRIME_NETTE")
STATUTS = {"A_PAYER": "À payer", "PAYEE": "Payée", "ANNULEE": "Annulée"}
MODES = {"ESP": "Espèces", "CHQ": "Chèque", "VIR": "Virement", "MOB": "Mobile money"}
CODES_ANNULATION = ("ANL", "ANP")
MAX_LIGNES = 500
VERROU_NUMERO = 880206


class ErreurApporteur(Exception):
    """Saisie refusée : message affiché tel quel."""


def _franc(valeur):
    return Decimal(str(valeur or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _nombre(valeur):
    return float(valeur) if valeur is not None else 0.0


def _entier(valeur):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return 0


def _texte(valeur, longueur=300):
    return str(valeur or "").strip()[:longueur]


def _iso(valeur):
    return valeur.isoformat() if hasattr(valeur, "isoformat") else (valeur or None)


def _taux(valeur):
    try:
        taux = Decimal(str(valeur if valeur not in (None, "") else 0).replace(",", "."))
    except InvalidOperation as erreur:
        raise ErreurApporteur("Le taux de commission n'est pas un nombre.") from erreur
    if taux < 0 or taux > 100:
        raise ErreurApporteur("Le taux de commission est compris entre 0 et 100 %.")
    return taux


def _date(valeur, champ):
    if not valeur:
        return None
    if isinstance(valeur, date):
        return valeur
    try:
        return date.fromisoformat(str(valeur).strip()[:10])
    except ValueError as erreur:
        raise ErreurApporteur(f"{champ} : date illisible.") from erreur


def _nom_utilisateur(user):
    return ((user.get_full_name() if hasattr(user, "get_full_name") else "") or getattr(user, "email", "") or "")[:150]


def montant_commission(assiette, taux, forfait=ZERO):
    """Commission d'une quittance : taux convenu x assiette, au franc. Forfait : montant convenu."""
    return _franc(forfait) if forfait else _franc(Decimal(str(assiette or 0)) * Decimal(str(taux or 0)) / 100)


# ------------------------------------------------------------------ génération des commissions
def synchroniser(cursor, ids=None):
    """Crée les lignes des quittances émises depuis la dernière lecture et remet à jour celles qui restent à payer."""
    filtre = "AND l.idrattachement = ANY(%s)" if ids is not None else ""
    liens = _lignes(cursor, f"""
        SELECT l.idrattachement, l.idapporteur, l.iddevis, l.taux, l.assiette, l.montantforfait, b.idcontrat AS idbase, b.numeropolice
        FROM lephare_affaire_apporteur l
        JOIN LATERAL (SELECT c.idcontrat, c.numeropolice FROM stdcontrat c WHERE c.iddevis = l.iddevis ORDER BY c.idcontrat LIMIT 1) b ON TRUE
        WHERE l.actif {filtre}""", [list(ids)] if ids is not None else [])
    if liens:
        polices = list({l["numeropolice"] for l in liens})
        mouvements, par_id = {}, {}
        for m in _lignes(cursor, """
                SELECT c.idcontrat, c.iddevis, c.idquittance, c.numeropolice, c.primenette, c.commissionintermediaire, COALESCE(c.idcontratannulation, 0) AS annulation,
                       TRIM(a.codeavenant) AS code, TRIM(a.libelleavenant) AS mouvement, q.numeroquittance, q.dateemission::date AS dateemission,
                       TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client
                FROM stdcontrat c
                JOIN stdavenant a ON a.idavenant = c.idavenant
                JOIN stdquittance q ON q.idquittance = c.idquittance
                LEFT JOIN stdclient cl ON cl.idclient = c.idclient
                WHERE c.numeropolice = ANY(%(p)s)
                   OR c.idcontrat IN (SELECT x.idcontratannulation FROM stdcontrat x WHERE x.numeropolice = ANY(%(p)s) AND COALESCE(x.idcontratannulation, 0) <> 0)
                ORDER BY c.idcontrat""", {"p": polices}):
            par_id[m["idcontrat"]] = m
            mouvements.setdefault(m["numeropolice"], []).append(m)
        existantes = {}
        for ligne in _lignes(cursor, """SELECT idcommission, idrattachement, idcontrat, idquittance, assiettemontant, taux, montant, statut
                                        FROM lephare_commission_apporteur WHERE idrattachement = ANY(%s)""", [[l["idrattachement"] for l in liens]]):
            existantes[(ligne["idrattachement"], ligne["idquittance"])] = ligne
        # Apporteur retiré puis rattaché de nouveau : une quittance déjà payée ne repart pas une seconde fois
        cursor.execute("SELECT idapporteur, idquittance FROM lephare_commission_apporteur WHERE statut = 'PAYEE' AND idapporteur = ANY(%s)", [list({l["idapporteur"] for l in liens})])
        deja_payees = set(cursor.fetchall())
        for lien in liens:
            _synchroniser_lien(cursor, lien, mouvements.get(lien["numeropolice"], []), par_id, existantes, deja_payees)
    # Quittance disparue : contrat supprimé
    cursor.execute("""UPDATE lephare_commission_apporteur c SET statut = 'ANNULEE', motifannulation = 'Contrat supprimé', dateannulation = now(), datemodification = now()
                      WHERE c.statut = 'A_PAYER' AND NOT EXISTS (SELECT 1 FROM stdquittance q WHERE q.idquittance = c.idquittance)""")


def _ecrire_ligne(cursor, lien, m, ligne, assiette, montant, deja_payees):
    """Crée la commission d'une quittance, ou remet à jour celle qui reste à payer. Payée ou annulée : on n'y touche plus."""
    if ligne is None:
        if montant and (lien["idapporteur"], m["idquittance"]) not in deja_payees:
            cursor.execute(
                """INSERT INTO lephare_commission_apporteur (idrattachement, idapporteur, idcontrat, idquittance, numeropolice, numeroquittance, mouvement, client, dateemission,
                       assiette, assiettemontant, taux, montant)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (idrattachement, idquittance) DO NOTHING""",
                [lien["idrattachement"], lien["idapporteur"], m["idcontrat"], m["idquittance"], lien["numeropolice"], m["numeroquittance"], (m["mouvement"] or "")[:60], (m["client"] or "")[:250],
                 m["dateemission"], lien["assiette"], assiette, lien["taux"], montant],
            )
    elif ligne["statut"] == "A_PAYER":
        if not montant:
            cursor.execute("DELETE FROM lephare_commission_apporteur WHERE idcommission = %s", [ligne["idcommission"]])
        elif ligne["montant"] != montant or ligne["taux"] != lien["taux"] or ligne["assiettemontant"] != assiette:
            cursor.execute("""UPDATE lephare_commission_apporteur SET assiette = %s, assiettemontant = %s, taux = %s, montant = %s, datemodification = now()
                              WHERE idcommission = %s""", [lien["assiette"], assiette, lien["taux"], montant, ligne["idcommission"]])


def _synchroniser_lien(cursor, lien, mouvements, par_id, existantes, deja_payees):
    forfait = lien["assiette"] == "FORFAIT"
    cle = lien["idrattachement"]
    couverts = [m for m in mouvements if m["idcontrat"] >= lien["idbase"] and (not forfait or m["iddevis"] == lien["iddevis"])]
    paye_par_annulation = {}
    for m in couverts:
        if m["code"] in CODES_ANNULATION:
            continue
        ligne = existantes.get((cle, m["idquittance"]))
        if m["annulation"]:
            if ligne and ligne["statut"] == "A_PAYER":
                cursor.execute("""UPDATE lephare_commission_apporteur SET statut = 'ANNULEE', motifannulation = 'Contrat annulé', dateannulation = now(), datemodification = now()
                                  WHERE idcommission = %s""", [ligne["idcommission"]])
                ligne["statut"] = "ANNULEE"
            elif ligne and ligne["statut"] == "PAYEE":
                paye_par_annulation[m["annulation"]] = paye_par_annulation.get(m["annulation"], ZERO) + ligne["montant"]
            continue
        if forfait:
            assiette, montant = lien["montantforfait"], _franc(lien["montantforfait"])
        else:
            assiette = (m["commissionintermediaire"] if lien["assiette"] == "COMMISSION" else m["primenette"]) or ZERO
            montant = montant_commission(assiette, lien["taux"])
        _ecrire_ligne(cursor, lien, m, ligne, assiette, montant, deja_payees)
    # Contrat annulé après le paiement de sa commission : ligne négative sur le mouvement d'annulation, déduite du prochain règlement.
    # Elle disparaît si le règlement est annulé à son tour. L'annulation peut porter un autre numéro de police (reprises d'URANUS).
    annulations = set(paye_par_annulation) | {m["idcontrat"] for m in couverts if m["code"] in CODES_ANNULATION}
    for id_annulation in annulations:
        m = par_id.get(id_annulation)
        if m:
            _ecrire_ligne(cursor, lien, m, existantes.get((cle, m["idquittance"])), ZERO, -paye_par_annulation.get(id_annulation, ZERO), deja_payees)


# ------------------------------------------------------------------ affaire
def _affaire(cursor, id_devis=0, id_contrat=0):
    """Devis et police de l'affaire. Un avenant ou un renouvellement non confirmé relève déjà de sa police."""
    if id_contrat:
        cursor.execute("SELECT iddevis FROM stdcontrat WHERE idcontrat = %s", [id_contrat])
        ligne = cursor.fetchone()
        if not ligne:
            raise ErreurApporteur("Contrat introuvable.")
        id_devis = ligne[0]
    lignes = _lignes(cursor, """
        SELECT d.iddevis, TRIM(d.numerodevis) AS numerodevis, COALESCE(d.confirme, FALSE) AS confirme, COALESCE(d.archive, FALSE) AS archive, d.idoldhist,
               d.primenette, d.primettc, d.commissionintermediaire, d.accessoireintermediaire, d.dateeffet::date AS dateeffet, d.dateexpiration::date AS dateexpiration,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client, TRIM(p.libelleproduit) AS branche, co.raisonsociale AS compagnie,
               ct.idcontrat, ct.numeropolice
        FROM stddevis d
        LEFT JOIN stdclient cl ON cl.idclient = d.idclient
        LEFT JOIN stdproduit p ON p.idproduit = d.idproduit
        LEFT JOIN stdcompagnie co ON co.idcompagnie = d.idcompagnie
        LEFT JOIN LATERAL (SELECT c.idcontrat, c.numeropolice FROM stdcontrat c WHERE c.iddevis = d.iddevis ORDER BY c.idcontrat DESC LIMIT 1) ct ON TRUE
        WHERE d.iddevis = %s""", [id_devis])
    if not lignes:
        raise ErreurApporteur("Devis introuvable.")
    affaire = lignes[0]
    affaire["police"] = affaire["numeropolice"]
    if not affaire["police"] and affaire["idoldhist"]:
        cursor.execute("SELECT numeropolice FROM stdcontrat WHERE iddevis = %s ORDER BY idcontrat DESC LIMIT 1", [affaire["idoldhist"]])
        ancien = cursor.fetchone()
        affaire["police"] = ancien[0] if ancien else None
    return affaire


def _devis_de_la_police(cursor, police):
    if not police:
        return []
    cursor.execute("SELECT DISTINCT iddevis FROM stdcontrat WHERE numeropolice = %s", [police])
    return [ligne[0] for ligne in cursor.fetchall()]


def _etat_reglement(emis, payee, a_payer, annulee):
    """État de règlement d'un apporteur sur une affaire, tel qu'il s'affiche."""
    if not emis:
        return "EN_ATTENTE", "En attente d'émission"
    if not (payee or a_payer or annulee):
        return "AUCUNE", "Pas de commission"
    if a_payer and payee:
        return "PARTIELLE", "Partiellement payée"
    if a_payer:
        return "A_PAYER", "À payer"
    if payee:
        return "PAYEE", "Payée"
    return "ANNULEE", "Annulée"


def _lignes_commission(cursor, condition, parametres):
    return _lignes(cursor, f"""
        SELECT c.idcommission, c.idrattachement, c.idapporteur, c.idcontrat, c.idquittance, c.numeropolice, c.numeroquittance, c.mouvement, c.client, c.dateemission, c.assiette,
               c.assiettemontant, c.taux, c.montant, c.statut, c.motifannulation, c.dateannulation, c.annulepar, a.code, TRIM(a.nom || ' ' || COALESCE(a.prenoms, '')) AS apporteur,
               q.primettc, COALESCE(q.mt_encaisse, 0) AS encaisse, {sql_reste("q")} AS reste, r.idreglement, r.numero AS numeroreglement, r.datereglement
        FROM lephare_commission_apporteur c
        JOIN stdapporteur a ON a.idapporteur = c.idapporteur
        LEFT JOIN stdquittance q ON q.idquittance = c.idquittance
        LEFT JOIN LATERAL (SELECT x.idreglement, x.numero, x.datereglement FROM lephare_detail_reglement_apporteur d
                           JOIN lephare_reglement_apporteur x ON x.idreglement = d.idreglement
                           WHERE d.idcommission = c.idcommission AND x.statut = 'V' ORDER BY x.idreglement DESC LIMIT 1) r ON TRUE
        WHERE {condition}""", parametres)


def _json_commission(c):
    reste = c["reste"]
    return {
        "IdCommission": c["idcommission"], "IdRattachement": c["idrattachement"], "IdApporteur": c["idapporteur"], "Apporteur": c["apporteur"], "Code": c["code"],
        "IdContrat": c["idcontrat"], "NumeroPolice": (c["numeropolice"] or "").strip(), "NumeroQuittance": (c["numeroquittance"] or "").strip(), "Mouvement": c["mouvement"], "Client": c["client"],
        "DateEmission": _iso(c["dateemission"]), "Assiette": c["assiette"], "LibelleAssiette": ASSIETTES.get(c["assiette"], c["assiette"]), "AssietteMontant": _nombre(c["assiettemontant"]),
        "Taux": _nombre(c["taux"]), "Montant": _nombre(c["montant"]), "Statut": c["statut"], "LibelleStatut": STATUTS.get(c["statut"], c["statut"]),
        "MotifAnnulation": c["motifannulation"], "DateAnnulation": _iso(c["dateannulation"]), "AnnulePar": c["annulepar"],
        "PrimeTtc": _nombre(c["primettc"]), "Encaisse": _nombre(c["encaisse"]), "Reste": _nombre(reste), "PrimeSoldee": c["primettc"] is not None and not reste,
        "IdReglement": c["idreglement"], "NumeroReglement": c["numeroreglement"] or "", "DateReglement": _iso(c["datereglement"]),
    }


def _bloc_affaire(cursor, affaire):
    """Apporteurs de l'affaire : taux, commissions générées, état de règlement."""
    devis = {affaire["iddevis"], *_devis_de_la_police(cursor, affaire["police"])}
    liens = _lignes(cursor, """
        SELECT l.idrattachement, l.idapporteur, l.iddevis, l.numerodevis, l.taux, l.assiette, l.montantforfait, l.origine, l.observation, l.actif, l.motifretrait, l.dateretrait, l.retirepar,
               l.operateur, l.datecreation, a.code, TRIM(a.nom || ' ' || COALESCE(a.prenoms, '')) AS apporteur, a.actif AS apporteuractif, a.tauxretrocession,
               EXISTS (SELECT 1 FROM stdcontrat c WHERE c.iddevis = l.iddevis) AS emis
        FROM lephare_affaire_apporteur l JOIN stdapporteur a ON a.idapporteur = l.idapporteur
        WHERE l.iddevis = ANY(%s) ORDER BY l.actif DESC, l.idrattachement""", [list(devis)])
    synchroniser(cursor, [l["idrattachement"] for l in liens if l["actif"]])
    lignes = _lignes_commission(cursor, "c.idrattachement = ANY(%s) ORDER BY c.idcontrat, c.idcommission", [[l["idrattachement"] for l in liens]])
    resultat, total_genere, total_prevu = [], ZERO, ZERO
    for lien in liens:
        siennes = [c for c in lignes if c["idrattachement"] == lien["idrattachement"]]
        somme = lambda statut: sum((c["montant"] for c in siennes if c["statut"] == statut), ZERO)  # noqa: E731,B023
        payee, a_payer, annulee = somme("PAYEE"), somme("A_PAYER"), somme("ANNULEE")
        code, libelle = _etat_reglement(lien["emis"], bool(payee), bool(a_payer), bool(annulee))
        prevu = ZERO
        if lien["actif"] and not lien["emis"]:
            base = affaire["commissionintermediaire"] if lien["assiette"] == "COMMISSION" else affaire["primenette"]
            prevu = montant_commission(base, lien["taux"], lien["montantforfait"] if lien["assiette"] == "FORFAIT" else ZERO)
        total_genere += payee + a_payer
        total_prevu += prevu
        resultat.append({
            "IdRattachement": lien["idrattachement"], "IdApporteur": lien["idapporteur"], "Code": lien["code"], "Apporteur": lien["apporteur"], "ApporteurActif": lien["apporteuractif"],
            "IdDevis": lien["iddevis"], "NumeroDevis": lien["numerodevis"], "Taux": _nombre(lien["taux"]), "TauxGeneral": None if lien["tauxretrocession"] is None else _nombre(lien["tauxretrocession"]),
            "Assiette": lien["assiette"], "LibelleAssiette": ASSIETTES.get(lien["assiette"], lien["assiette"]), "MontantForfait": _nombre(lien["montantforfait"]),
            "Origine": lien["origine"], "Observation": lien["observation"], "Actif": lien["actif"], "MotifRetrait": lien["motifretrait"], "DateRetrait": _iso(lien["dateretrait"]),
            "RetirePar": lien["retirepar"], "Operateur": lien["operateur"], "DateCreation": _iso(lien["datecreation"]), "Emis": lien["emis"],
            "CommissionPrevue": _nombre(prevu), "CommissionGeneree": _nombre(payee + a_payer), "Payee": _nombre(payee), "APayer": _nombre(a_payer), "Annulee": _nombre(annulee),
            "EtatReglement": code, "LibelleEtat": libelle, "Lignes": [_json_commission(c) for c in siennes],
        })
    # Revenu du cabinet sur les mouvements couverts : commission et accessoires ; devis pas encore émis : ses montants
    cabinet = (affaire["commissionintermediaire"] or ZERO) + (affaire["accessoireintermediaire"] or ZERO)
    if affaire["police"] and liens:
        cursor.execute("""SELECT SUM(COALESCE(c.commissionintermediaire, 0) + COALESCE(c.accessoireintermediaire, 0)) FROM stdcontrat c
                          WHERE c.numeropolice = %s AND COALESCE(c.idcontratannulation, 0) = 0
                            AND c.idcontrat >= (SELECT MIN(b.idcontrat) FROM stdcontrat b WHERE b.iddevis = ANY(%s))""",
                       [affaire["police"], [l["iddevis"] for l in liens]])
        emis = cursor.fetchone()[0]
        if emis is not None:
            cabinet = emis
    total = total_genere + total_prevu
    alerte = ""
    if total > cabinet and total > 0:
        alerte = (f"Les commissions des apporteurs ({_franc(total):,} F) dépassent la commission du cabinet sur cette affaire ({_franc(cabinet):,} F).").replace(",", " ")
    return {
        "IdDevis": affaire["iddevis"], "NumeroDevis": affaire["numerodevis"], "NumeroPolice": (affaire["police"] or "").strip(), "IdContrat": affaire["idcontrat"], "Client": affaire["client"],
        "Branche": affaire["branche"], "Compagnie": affaire["compagnie"] or "", "Confirme": affaire["confirme"], "Archive": affaire["archive"], "PrimeNette": _nombre(affaire["primenette"]),
        "CommissionCabinet": _nombre(cabinet), "Apporteurs": resultat, "TotalCommissions": _nombre(total), "Alerte": alerte,
    }


def _controler_taux_cumules(cursor, devis, assiette, taux, sauf=None):
    """Sur la commission du cabinet, les apporteurs ne peuvent pas se partager plus de 100 %."""
    if assiette != "COMMISSION":
        return
    cursor.execute("""SELECT COALESCE(SUM(taux), 0) FROM lephare_affaire_apporteur WHERE iddevis = ANY(%s) AND actif AND assiette = 'COMMISSION' AND idrattachement <> %s""",
                   [list(devis), sauf or 0])
    cumul = cursor.fetchone()[0] or ZERO
    if cumul + taux > 100:
        raise ErreurApporteur(f"Les apporteurs de cette affaire ont déjà {cumul:g} % de la commission du cabinet : {taux:g} % de plus dépasserait 100 %.")


def rattacher(cursor, donnees, user):
    affaire = _affaire(cursor, _entier(donnees.get("IdDevis")), _entier(donnees.get("IdContrat")))
    id_apporteur = _entier(donnees.get("IdApporteur"))
    apporteurs = _lignes(cursor, "SELECT idapporteur, actif, TRIM(nom) AS nom, code FROM stdapporteur WHERE idapporteur = %s", [id_apporteur])
    if not apporteurs:
        raise ErreurApporteur("Choisissez un apporteur.")
    if not apporteurs[0]["actif"]:
        raise ErreurApporteur(f"L'apporteur {apporteurs[0]['code']} est désactivé : réactivez-le pour lui rattacher une affaire.")
    if affaire["archive"]:
        raise ErreurApporteur("Ce devis est archivé.")
    assiette = _texte(donnees.get("Assiette")).upper() or "COMMISSION"
    if assiette not in ASSIETTES_AU_TAUX:
        raise ErreurApporteur("Choisissez l'assiette de la commission.")
    taux = _taux(donnees.get("Taux"))
    if taux <= 0:
        raise ErreurApporteur("Saisissez le taux de commission convenu pour cet apporteur.")
    devis = {affaire["iddevis"], *_devis_de_la_police(cursor, affaire["police"])}
    cursor.execute("SELECT 1 FROM lephare_affaire_apporteur WHERE iddevis = ANY(%s) AND idapporteur = %s AND actif LIMIT 1", [list(devis), id_apporteur])
    if cursor.fetchone():
        raise ErreurApporteur(f"{apporteurs[0]['code']} - {apporteurs[0]['nom']} est déjà rattaché à cette affaire : modifiez son taux.")
    _controler_taux_cumules(cursor, devis, assiette, taux)
    cursor.execute(
        """INSERT INTO lephare_affaire_apporteur (idapporteur, iddevis, numerodevis, taux, assiette, observation, idoperateur, operateur)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING idrattachement""",
        [id_apporteur, affaire["iddevis"], affaire["numerodevis"] or "", taux, assiette, _texte(donnees.get("Observation")), getattr(user, "id", None), _nom_utilisateur(user)],
    )
    return affaire


def _lien(cursor, id_rattachement, verrou=True):
    lignes = _lignes(cursor, f"SELECT * FROM lephare_affaire_apporteur WHERE idrattachement = %s {'FOR UPDATE' if verrou else ''}", [id_rattachement])
    if not lignes:
        raise ErreurApporteur("Rattachement introuvable.")
    return lignes[0]


def modifier_rattachement(cursor, id_rattachement, donnees):
    """Taux convenu corrigé : les commissions à payer suivent, les commissions déjà payées gardent leur taux."""
    lien = _lien(cursor, id_rattachement)
    if not lien["actif"]:
        raise ErreurApporteur("Cet apporteur a été retiré de l'affaire.")
    affaire = _affaire(cursor, lien["iddevis"])
    assiette = _texte(donnees.get("Assiette")).upper() or lien["assiette"]
    if lien["assiette"] == "FORFAIT" or assiette not in ASSIETTES_AU_TAUX:
        raise ErreurApporteur("Un montant convenu ne se change pas en taux : retirez l'apporteur et rattachez-le de nouveau.")
    taux = _taux(donnees.get("Taux"))
    if taux <= 0:
        raise ErreurApporteur("Saisissez le taux de commission convenu pour cet apporteur.")
    _controler_taux_cumules(cursor, {lien["iddevis"], *_devis_de_la_police(cursor, affaire["police"])}, assiette, taux, sauf=id_rattachement)
    cursor.execute("UPDATE lephare_affaire_apporteur SET taux = %s, assiette = %s, datemodification = now() WHERE idrattachement = %s", [taux, assiette, id_rattachement])
    return affaire


def retirer(cursor, id_rattachement, motif, user):
    """Apporteur retiré : plus de commission sur les mouvements suivants, celles à payer sont annulées, celles déjà payées restent."""
    motif = _texte(motif)
    if len(motif) < 5:
        raise ErreurApporteur("Précisez le motif du retrait.")
    lien = _lien(cursor, id_rattachement)
    if not lien["actif"]:
        raise ErreurApporteur("Cet apporteur a déjà été retiré.")
    affaire = _affaire(cursor, lien["iddevis"])
    nom = _nom_utilisateur(user)
    synchroniser(cursor, [id_rattachement])
    cursor.execute("""UPDATE lephare_commission_apporteur SET statut = 'ANNULEE', motifannulation = %s, dateannulation = now(), annulepar = %s, datemodification = now()
                      WHERE idrattachement = %s AND statut = 'A_PAYER'""", [f"Retrait de l'apporteur : {motif}"[:300], nom, id_rattachement])
    cursor.execute("""UPDATE lephare_affaire_apporteur SET actif = FALSE, motifretrait = %s, dateretrait = now(), retirepar = %s, datemodification = now()
                      WHERE idrattachement = %s""", [motif, nom, id_rattachement])
    return affaire


def rattacher_apporteur_package(cursor, id_devis, id_apporteur, mode, valeur, familles, id_utilisateur):
    """
    Oreole Santé : l'apporteur choisi dans le parcours devient un rattachement. Convention au taux = taux sur la prime nette (prime HT), au
    montant par famille = montant convenu pour ce devis ; sans convention, l'apporteur est noté sans commission.
    """
    cursor.execute("SELECT idrattachement, idapporteur FROM lephare_affaire_apporteur WHERE iddevis = %s AND origine = 'OREOLE' AND actif", [id_devis])
    for id_lien, apporteur in cursor.fetchall():
        if apporteur != id_apporteur:
            cursor.execute("SELECT 1 FROM lephare_commission_apporteur WHERE idrattachement = %s LIMIT 1", [id_lien])
            if cursor.fetchone():
                continue
            cursor.execute("DELETE FROM lephare_affaire_apporteur WHERE idrattachement = %s", [id_lien])
    if not id_apporteur:
        return
    valeur = Decimal(str(valeur or 0))
    forfait = mode == "FAMILLE" and valeur > 0
    assiette = "FORFAIT" if forfait else "PRIME_NETTE"
    taux, montant = (ZERO, valeur * familles) if forfait else ((valeur if mode != "FAMILLE" else ZERO), ZERO)
    if forfait and not familles:
        return
    affaire = _affaire(cursor, id_devis)
    if not forfait:
        # Au taux, le rattachement existant couvre déjà les mouvements suivants de la police
        devis = {id_devis, *_devis_de_la_police(cursor, affaire["police"])}
        cursor.execute("SELECT idrattachement FROM lephare_affaire_apporteur WHERE iddevis = ANY(%s) AND idapporteur = %s AND actif AND iddevis <> %s LIMIT 1",
                       [list(devis), id_apporteur, id_devis])
        if cursor.fetchone():
            return
    cursor.execute("SELECT idrattachement FROM lephare_affaire_apporteur WHERE iddevis = %s AND idapporteur = %s AND actif", [id_devis, id_apporteur])
    existant = cursor.fetchone()
    if existant:
        cursor.execute("""UPDATE lephare_affaire_apporteur SET taux = %s, assiette = %s, montantforfait = %s, datemodification = now()
                          WHERE idrattachement = %s AND origine = 'OREOLE'""", [taux, assiette, montant, existant[0]])
        return
    from sante.cartes import nom_utilisateur  # module voisin, importé ici car sante dépend de production

    cursor.execute(
        """INSERT INTO lephare_affaire_apporteur (idapporteur, iddevis, numerodevis, taux, assiette, montantforfait, origine, idoperateur, operateur)
           VALUES (%s, %s, %s, %s, %s, %s, 'OREOLE', %s, %s)""",
        [id_apporteur, id_devis, affaire["numerodevis"] or "", taux, assiette, montant, id_utilisateur or None, nom_utilisateur(id_utilisateur)],
    )


def retirer_du_devis(cursor, id_devis):
    """Devis supprimé : ses rattachements sans commission disparaissent, les autres restent dans l'historique, retirés."""
    cursor.execute("""DELETE FROM lephare_affaire_apporteur l WHERE l.iddevis = %s
                      AND NOT EXISTS (SELECT 1 FROM lephare_commission_apporteur c WHERE c.idrattachement = l.idrattachement)""", [id_devis])
    cursor.execute("""UPDATE lephare_affaire_apporteur SET actif = FALSE, motifretrait = 'Devis supprimé', dateretrait = now(), datemodification = now()
                      WHERE iddevis = %s AND actif""", [id_devis])


def commission_payee_du_contrat(cursor, id_quittance):
    """Commission déjà versée à un apporteur sur cette quittance : le contrat ne se supprime pas."""
    cursor.execute("""SELECT TRIM(a.nom) FROM lephare_commission_apporteur c JOIN stdapporteur a ON a.idapporteur = c.idapporteur
                      WHERE c.idquittance = %s AND c.statut = 'PAYEE' LIMIT 1""", [id_quittance])
    ligne = cursor.fetchone()
    return ligne[0] if ligne else None


# ------------------------------------------------------------------ règlements
def _numero_reglement(cursor, jour):
    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [VERROU_NUMERO])
    prefixe = f"RA-{jour.year}-"
    cursor.execute("SELECT COALESCE(MAX(SUBSTRING(numero FROM 9)::int), 0) + 1 FROM lephare_reglement_apporteur WHERE numero LIKE %s", [f"{prefixe}%"])
    return f"{prefixe}{cursor.fetchone()[0]:04d}"


def regler(cursor, donnees, user):
    # Un contrat annulé depuis la dernière lecture ne se règle pas
    synchroniser(cursor)
    id_apporteur = _entier(donnees.get("IdApporteur"))
    ids = sorted({_entier(i) for i in donnees.get("Commissions") or [] if _entier(i)})
    if not ids:
        raise ErreurApporteur("Choisissez au moins une commission à régler.")
    jour = _date(donnees.get("DateReglement"), "Date du règlement") or date.today()
    if jour > date.today():
        raise ErreurApporteur("La date du règlement ne peut pas être dans le futur.")
    mode = _texte(donnees.get("Mode")).upper()
    if mode not in MODES:
        raise ErreurApporteur("Choisissez le mode de règlement.")
    reference = _texte(donnees.get("Reference"), 60)
    id_banque = _entier(donnees.get("IdBanque")) or None
    if mode != "ESP" and not reference:
        raise ErreurApporteur(f"{MODES[mode]} : saisissez la référence du règlement.")
    if mode in ("CHQ", "VIR"):
        if not id_banque:
            raise ErreurApporteur(f"{MODES[mode]} : choisissez la banque.")
        cursor.execute("SELECT 1 FROM stdbanque WHERE idbanque = %s", [id_banque])
        if not cursor.fetchone():
            raise ErreurApporteur("Banque introuvable.")
    lignes = _lignes(cursor, "SELECT idcommission, idapporteur, montant, statut, numeroquittance FROM lephare_commission_apporteur WHERE idcommission = ANY(%s) ORDER BY idcommission FOR UPDATE", [ids])
    if len(lignes) != len(ids):
        raise ErreurApporteur("Une commission choisie n'existe plus : actualisez la liste.")
    if {l["idapporteur"] for l in lignes} != {id_apporteur}:
        raise ErreurApporteur("Un règlement ne concerne qu'un seul apporteur.")
    pas_a_payer = [l for l in lignes if l["statut"] != "A_PAYER"]
    if pas_a_payer:
        raise ErreurApporteur(f"La commission de la quittance {pas_a_payer[0]['numeroquittance']} n'est plus à payer : actualisez la liste.")
    total = sum((l["montant"] for l in lignes), ZERO)
    if total <= 0:
        raise ErreurApporteur("Le total à régler doit être positif : les commissions à déduire dépassent celles à payer.")
    numero = _numero_reglement(cursor, jour)
    cursor.execute(
        """INSERT INTO lephare_reglement_apporteur (numero, idapporteur, datereglement, mode, idbanque, reference, montant, observation, idoperateur, operateur)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING idreglement""",
        [numero, id_apporteur, jour, mode, id_banque, reference, total, _texte(donnees.get("Observation")), getattr(user, "id", None), _nom_utilisateur(user)],
    )
    id_reglement = cursor.fetchone()[0]
    for ligne in lignes:
        cursor.execute("INSERT INTO lephare_detail_reglement_apporteur (idreglement, idcommission, montant) VALUES (%s, %s, %s)", [id_reglement, ligne["idcommission"], ligne["montant"]])
    cursor.execute("UPDATE lephare_commission_apporteur SET statut = 'PAYEE', datemodification = now() WHERE idcommission = ANY(%s)", [ids])
    return {"IdReglement": id_reglement, "Numero": numero, "Montant": _nombre(total), "Commissions": len(lignes)}


def annuler_reglement(cursor, id_reglement, motif, user):
    motif = _texte(motif)
    if len(motif) < 5:
        raise ErreurApporteur("Précisez le motif de l'annulation.")
    lignes = _lignes(cursor, "SELECT * FROM lephare_reglement_apporteur WHERE idreglement = %s FOR UPDATE", [id_reglement])
    if not lignes:
        raise ErreurApporteur("Règlement introuvable.")
    if lignes[0]["statut"] == "A":
        raise ErreurApporteur("Ce règlement est déjà annulé.")
    cursor.execute("""UPDATE lephare_commission_apporteur SET statut = 'A_PAYER', datemodification = now()
                      WHERE statut = 'PAYEE' AND idcommission IN (SELECT idcommission FROM lephare_detail_reglement_apporteur WHERE idreglement = %s)""", [id_reglement])
    cursor.execute("""UPDATE lephare_reglement_apporteur SET statut = 'A', motifannulation = %s, dateannulation = now(), annulepar = %s WHERE idreglement = %s""",
                   [motif, _nom_utilisateur(user), id_reglement])
    return lignes[0]


def annuler_commission(cursor, id_commission, motif, user):
    motif = _texte(motif)
    if len(motif) < 5:
        raise ErreurApporteur("Précisez le motif de l'annulation.")
    lignes = _lignes(cursor, "SELECT statut FROM lephare_commission_apporteur WHERE idcommission = %s FOR UPDATE", [id_commission])
    if not lignes:
        raise ErreurApporteur("Commission introuvable.")
    if lignes[0]["statut"] == "PAYEE":
        raise ErreurApporteur("Cette commission est payée : annulez d'abord son règlement.")
    if lignes[0]["statut"] == "ANNULEE":
        raise ErreurApporteur("Cette commission est déjà annulée.")
    cursor.execute("""UPDATE lephare_commission_apporteur SET statut = 'ANNULEE', motifannulation = %s, dateannulation = now(), annulepar = %s, datemodification = now()
                      WHERE idcommission = %s""", [motif, _nom_utilisateur(user), id_commission])


# ------------------------------------------------------------------ lectures
def _filtres_commissions(parametres):
    """Par apporteur, par affaire (police, quittance, client) et par période (date d'émission de la quittance)."""
    condition, valeurs = ["TRUE"], []
    if _entier(parametres.get("apporteur")):
        condition.append("c.idapporteur = %s")
        valeurs.append(_entier(parametres.get("apporteur")))
    statut = _texte(parametres.get("statut")).upper()
    if statut in STATUTS:
        condition.append("c.statut = %s")
        valeurs.append(statut)
    texte = _texte(parametres.get("q"), 100)
    if texte:
        condition.append("(c.numeropolice ILIKE %s OR c.numeroquittance ILIKE %s OR c.client ILIKE %s)")
        valeurs += [f"%{texte}%"] * 3
    du, au = _date(parametres.get("du"), "Date de début"), _date(parametres.get("au"), "Date de fin")
    if du:
        condition.append("c.dateemission >= %s")
        valeurs.append(du)
    if au:
        condition.append("c.dateemission <= %s")
        valeurs.append(au)
    return " AND ".join(condition), valeurs


def liste_commissions(cursor, parametres):
    synchroniser(cursor)
    condition, valeurs = _filtres_commissions(parametres)
    cursor.execute(f"""SELECT c.statut, COUNT(*), COALESCE(SUM(c.montant), 0) FROM lephare_commission_apporteur c WHERE {condition} GROUP BY c.statut""", valeurs)
    totaux = {"A_PAYER": 0.0, "PAYEE": 0.0, "ANNULEE": 0.0}
    nombres = {"A_PAYER": 0, "PAYEE": 0, "ANNULEE": 0}
    for statut, nombre, montant in cursor.fetchall():
        totaux[statut], nombres[statut] = _nombre(montant), nombre
    lignes = _lignes_commission(cursor, f"{condition} ORDER BY c.dateemission DESC NULLS LAST, c.idcommission DESC LIMIT %s", [*valeurs, MAX_LIGNES + 1])
    return {
        "Lignes": [_json_commission(c) for c in lignes[:MAX_LIGNES]], "Tronque": len(lignes) > MAX_LIGNES, "Totaux": totaux, "Nombres": nombres,
    }


def liste_affaires(cursor, parametres):
    """Une ligne par apporteur et par affaire : qui, à quel taux, combien généré, où en est le règlement."""
    synchroniser(cursor)
    condition, valeurs = ["TRUE"], []
    if _entier(parametres.get("apporteur")):
        condition.append("l.idapporteur = %s")
        valeurs.append(_entier(parametres.get("apporteur")))
    texte = _texte(parametres.get("q"), 100)
    if texte:
        condition.append("(l.numerodevis ILIKE %s OR ct.numeropolice ILIKE %s OR cl.nom ILIKE %s OR a.nom ILIKE %s OR a.code ILIKE %s)")
        valeurs += [f"%{texte}%"] * 5
    du, au = _date(parametres.get("du"), "Date de début"), _date(parametres.get("au"), "Date de fin")
    if du:
        condition.append("l.datecreation::date >= %s")
        valeurs.append(du)
    if au:
        condition.append("l.datecreation::date <= %s")
        valeurs.append(au)
    lignes = _lignes(cursor, f"""
        SELECT l.idrattachement, l.idapporteur, l.iddevis, l.numerodevis, l.taux, l.assiette, l.montantforfait, l.actif, l.datecreation, l.operateur, a.code,
               TRIM(a.nom || ' ' || COALESCE(a.prenoms, '')) AS apporteur, ct.idcontrat, ct.numeropolice, TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client,
               TRIM(p.libelleproduit) AS branche,
               COALESCE(SUM(x.montant) FILTER (WHERE x.statut = 'PAYEE'), 0) AS payee, COALESCE(SUM(x.montant) FILTER (WHERE x.statut = 'A_PAYER'), 0) AS apayer,
               COALESCE(SUM(x.montant) FILTER (WHERE x.statut = 'ANNULEE'), 0) AS annulee
        FROM lephare_affaire_apporteur l
        JOIN stdapporteur a ON a.idapporteur = l.idapporteur
        LEFT JOIN stddevis d ON d.iddevis = l.iddevis
        LEFT JOIN stdclient cl ON cl.idclient = d.idclient
        LEFT JOIN stdproduit p ON p.idproduit = d.idproduit
        LEFT JOIN LATERAL (SELECT c.idcontrat, c.numeropolice FROM stdcontrat c WHERE c.iddevis = l.iddevis ORDER BY c.idcontrat DESC LIMIT 1) ct ON TRUE
        LEFT JOIN lephare_commission_apporteur x ON x.idrattachement = l.idrattachement
        WHERE {' AND '.join(condition)}
        GROUP BY l.idrattachement, a.code, a.nom, a.prenoms, ct.idcontrat, ct.numeropolice, cl.nom, cl.prenoms, p.libelleproduit
        ORDER BY l.idrattachement DESC LIMIT %s""", [*valeurs, MAX_LIGNES])
    resultat = []
    for l in lignes:
        code, libelle = _etat_reglement(bool(l["idcontrat"]), bool(l["payee"]), bool(l["apayer"]), bool(l["annulee"]))
        resultat.append({
            "IdRattachement": l["idrattachement"], "IdApporteur": l["idapporteur"], "Code": l["code"], "Apporteur": l["apporteur"], "IdDevis": l["iddevis"], "NumeroDevis": l["numerodevis"],
            "IdContrat": l["idcontrat"], "NumeroPolice": (l["numeropolice"] or "").strip(), "Client": l["client"], "Branche": l["branche"] or "", "Taux": _nombre(l["taux"]),
            "Assiette": l["assiette"], "LibelleAssiette": ASSIETTES.get(l["assiette"], l["assiette"]), "MontantForfait": _nombre(l["montantforfait"]), "Actif": l["actif"],
            "DateCreation": _iso(l["datecreation"]), "Operateur": l["operateur"], "CommissionGeneree": _nombre(l["payee"] + l["apayer"]), "Payee": _nombre(l["payee"]),
            "APayer": _nombre(l["apayer"]), "Annulee": _nombre(l["annulee"]), "EtatReglement": code, "LibelleEtat": libelle,
        })
    return {"Lignes": resultat, "Tronque": len(lignes) >= MAX_LIGNES}


def liste_reglements(cursor, parametres):
    condition, valeurs = ["TRUE"], []
    if _entier(parametres.get("apporteur")):
        condition.append("r.idapporteur = %s")
        valeurs.append(_entier(parametres.get("apporteur")))
    du, au = _date(parametres.get("du"), "Date de début"), _date(parametres.get("au"), "Date de fin")
    if du:
        condition.append("r.datereglement >= %s")
        valeurs.append(du)
    if au:
        condition.append("r.datereglement <= %s")
        valeurs.append(au)
    reglements = _lignes(cursor, f"""
        SELECT r.*, a.code, TRIM(a.nom || ' ' || COALESCE(a.prenoms, '')) AS apporteur, b.libelle AS banque
        FROM lephare_reglement_apporteur r JOIN stdapporteur a ON a.idapporteur = r.idapporteur LEFT JOIN stdbanque b ON b.idbanque = r.idbanque
        WHERE {' AND '.join(condition)} ORDER BY r.datereglement DESC, r.idreglement DESC LIMIT %s""", [*valeurs, MAX_LIGNES])
    details = {}
    if reglements:
        for d in _lignes(cursor, """SELECT d.idreglement, c.numeropolice, c.numeroquittance, c.client, c.taux, d.montant FROM lephare_detail_reglement_apporteur d
                                    JOIN lephare_commission_apporteur c ON c.idcommission = d.idcommission WHERE d.idreglement = ANY(%s) ORDER BY d.iddetail""",
                         [[r["idreglement"] for r in reglements]]):
            details.setdefault(d["idreglement"], []).append({
                "NumeroPolice": (d["numeropolice"] or "").strip(), "NumeroQuittance": (d["numeroquittance"] or "").strip(), "Client": d["client"], "Taux": _nombre(d["taux"]), "Montant": _nombre(d["montant"]),
            })
    return {"Lignes": [{
        "IdReglement": r["idreglement"], "Numero": r["numero"], "IdApporteur": r["idapporteur"], "Code": r["code"], "Apporteur": r["apporteur"], "DateReglement": _iso(r["datereglement"]),
        "Mode": r["mode"], "LibelleMode": MODES.get(r["mode"], r["mode"]), "Banque": (r["banque"] or "").strip(), "Reference": r["reference"], "Montant": _nombre(r["montant"]),
        "Observation": r["observation"], "Statut": r["statut"], "MotifAnnulation": r["motifannulation"], "DateAnnulation": _iso(r["dateannulation"]), "AnnulePar": r["annulepar"],
        "Operateur": r["operateur"], "DateCreation": _iso(r["datecreation"]), "Details": details.get(r["idreglement"], []),
    } for r in reglements]}


def synthese(cursor):
    """Par apporteur : nombre d'affaires et commissions générées, payées, à payer et annulées."""
    synchroniser(cursor)
    lignes = _lignes(cursor, """
        SELECT a.idapporteur, (SELECT COUNT(*) FROM lephare_affaire_apporteur l WHERE l.idapporteur = a.idapporteur AND l.actif) AS affaires,
               COALESCE(SUM(c.montant) FILTER (WHERE c.statut = 'PAYEE'), 0) AS payee, COALESCE(SUM(c.montant) FILTER (WHERE c.statut = 'A_PAYER'), 0) AS apayer,
               COALESCE(SUM(c.montant) FILTER (WHERE c.statut = 'ANNULEE'), 0) AS annulee
        FROM stdapporteur a LEFT JOIN lephare_commission_apporteur c ON c.idapporteur = a.idapporteur GROUP BY a.idapporteur""")
    return {str(l["idapporteur"]): {"Affaires": l["affaires"], "Payee": _nombre(l["payee"]), "APayer": _nombre(l["apayer"]), "Annulee": _nombre(l["annulee"])} for l in lignes}


def rechercher_affaires(cursor, texte):
    """Devis et polices à rattacher, par numéro ou par client."""
    texte = _texte(texte, 80)
    if len(texte) < 3:
        return {"Lignes": []}
    motif = f"%{texte}%"
    lignes = _lignes(cursor, """
        SELECT d.iddevis, TRIM(d.numerodevis) AS numerodevis, COALESCE(d.confirme, FALSE) AS confirme, ct.idcontrat, ct.numeropolice, d.primettc,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client, TRIM(p.libelleproduit) AS branche, d.dateeffet::date AS dateeffet
        FROM stddevis d
        LEFT JOIN stdclient cl ON cl.idclient = d.idclient
        LEFT JOIN stdproduit p ON p.idproduit = d.idproduit
        LEFT JOIN LATERAL (SELECT c.idcontrat, c.numeropolice FROM stdcontrat c WHERE c.iddevis = d.iddevis ORDER BY c.idcontrat DESC LIMIT 1) ct ON TRUE
        WHERE NOT COALESCE(d.archive, FALSE) AND (d.numerodevis ILIKE %s OR ct.numeropolice ILIKE %s OR cl.nom ILIKE %s OR cl.prenoms ILIKE %s)
        ORDER BY d.iddevis DESC LIMIT 20""", [motif] * 4)
    return {"Lignes": [{
        "IdDevis": l["iddevis"], "NumeroDevis": l["numerodevis"], "Confirme": l["confirme"], "IdContrat": l["idcontrat"], "NumeroPolice": (l["numeropolice"] or "").strip(),
        "Client": l["client"], "Branche": l["branche"] or "", "PrimeTtc": _nombre(l["primettc"]), "DateEffet": _iso(l["dateeffet"]),
    } for l in lignes]}


# ------------------------------------------------------------------ routes
def _executer(fonction, code=status.HTTP_200_OK):
    """Exécute dans une transaction ; les lectures aussi, car elles génèrent les commissions des nouvelles quittances."""
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            return Response(fonction(cursor), status=code)
    except ErreurApporteur as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
    except IntegrityError:
        logger.exception("Apporteurs : conflit en base")
        return Response({"error": "Enregistrement impossible : cet élément vient d'être modifié. Actualisez la page."}, status=status.HTTP_409_CONFLICT)
    except DatabaseError as erreur:
        logger.exception("Apporteurs : erreur de base")
        return Response({"error": str(erreur).split("\n")[0]}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_affaire(request):
    id_devis, id_contrat = _entier(request.query_params.get("devis")), _entier(request.query_params.get("contrat"))
    return _executer(lambda c: _bloc_affaire(c, _affaire(c, id_devis, id_contrat)))


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_affaires(request):
    return _executer(lambda c: liste_affaires(c, request.query_params))


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_recherche_affaires(request):
    return _executer(lambda c: rechercher_affaires(c, request.query_params.get("q")))


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_synthese(request):
    return _executer(synthese)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_commissions(request):
    return _executer(lambda c: liste_commissions(c, request.query_params))


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_annulation_commission(request, id_commission):
    def executer(cursor):
        annuler_commission(cursor, id_commission, request.data.get("Motif") or request.headers.get("X-Motif"), request.user)
        return {"Message": "Commission annulée."}
    return _executer(executer)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_rattachements(request):
    def executer(cursor):
        return _bloc_affaire(cursor, rattacher(cursor, request.data, request.user))
    return _executer(executer, status.HTTP_201_CREATED)


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_rattachement(request, id_rattachement):
    def executer(cursor):
        return _bloc_affaire(cursor, modifier_rattachement(cursor, id_rattachement, request.data))
    return _executer(executer)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_retrait(request, id_rattachement):
    def executer(cursor):
        return _bloc_affaire(cursor, retirer(cursor, id_rattachement, request.data.get("Motif"), request.user))
    return _executer(executer)


@api_view(["GET", "POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_reglements(request):
    if request.method == "GET":
        return _executer(lambda c: liste_reglements(c, request.query_params))
    return _executer(lambda c: regler(c, request.data, request.user), status.HTTP_201_CREATED)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_annulation_reglement(request, id_reglement):
    def executer(cursor):
        reglement = annuler_reglement(cursor, id_reglement, request.data.get("Motif") or request.headers.get("X-Motif"), request.user)
        return {"Message": f"Règlement {reglement['numero']} annulé : ses commissions reviennent à payer."}
    return _executer(executer)
