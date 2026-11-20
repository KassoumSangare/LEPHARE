"""
Règlement des ristournes en caisse (demande du 2026-11-20). Une ristourne est une quittance négative : la part de prime
rendue au client par un avenant de retrait ou de résiliation (production/avenants.py, nature R), ou reprise d'URANUS.
Elle se règle de deux façons, comme une prime à l'envers :

- remboursement : le client reçoit son argent, en espèces, par chèque ou virement du cabinet, par paiement mobile, ou
  directement de la compagnie (mode « A la compagnie », comme dans URANUS) ; la pièce de caisse est négative et sort de
  l'argent de la caisse du jour ;
- imputation : la ristourne paie une autre prime du même client, sans mouvement d'argent ; une seule pièce en mode
  « CMP Prime / Ristourne » (compensation) porte la ristourne en négatif et la ou les primes payées en positif, total nul.
  La prime ainsi payée suit le circuit de toute prime encaissée (reversement à sa compagnie).

Un règlement partiel garde la ristourne ouverte (sp_enregistrement_encaissement v7, migration production 0225). Une pièce
saisie par erreur s'annule ici (sp_annulation_encaissement, contre-passation), tant que rien n'en a été reversé.
La ristourne reste à récupérer auprès de la compagnie hors de ce module, comme dans URANUS (aucune ligne négative n'entre
dans un bordereau de reversement).

Routes : GET caisse/ristournes/ (à régler, réglées, modes), GET caisse/ristournes/<idquittance>/imputation/ (primes du
client), POST caisse/ristournes/<idquittance>/remboursement/ et /imputation/ (droit encaissements.create),
POST caisse/ristournes/reglements/<idencaissement>/annulation/ (droit encaissements.cancel, motif).
"""

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import DatabaseError, connection, transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from autorisations.journal import journaliser
from core.date_parser import date_emission_du_jour

from .models import Encaissement
from .renouvellement import AUTHENTIFICATION, _lignes
from .reste_encaissement import RELIQUAT_NEGLIGEABLE
from .views_bordereaux import _branche

logger = logging.getLogger(__name__)

MODULE = "encaissements"
LIBELLE_IMPUTATION = "CMP PRIME / RISTOURNE"
REGLEES_AFFICHEES = 300
MOTIF_MINIMUM = 5
CENTIME = Decimal("0.01")

# Ristourne à régler : quittance négative non soldée (reliquat de moins de 5 F négligé), hors quittance d'annulation
# (nature A, réglée avec la quittance qu'elle annule) et hors contrat annulé
SQL_QUITTANCE = """
    SELECT q.idquittance, q.numeroquittance, TRIM(COALESCE(q.nature, '')) AS nature, q.idclient, q.idproduit,
           q.dateemission::date AS dateemission, q.dateeffet::date AS dateeffet, q.dateexpiration::date AS dateexpiration,
           q.primettc, COALESCE(q.mt_encaisse, 0) AS regle, q.primettc - COALESCE(q.mt_encaisse, 0) AS reste,
           TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client,
           COALESCE(NULLIF(TRIM(ct.numeropolice), ''), TRIM(COALESCE(q.numeropolice, ''))) AS police,
           ct.idcontrat, COALESCE(ct.idcontratannulation, 0) <> 0 AS annule, TRIM(COALESCE(cie.raisonsociale, '')) AS compagnie,
           TRIM(COALESCE(p.libelleproduit, '')) AS branche, TRIM(COALESCE(a.codeavenant, '')) AS codeavenant,
           TRIM(COALESCE(a.libelleavenant, '')) AS mouvement, TRIM(COALESCE(ct.numeroavenant, '')) AS numeroavenant
    FROM stdquittance q
    LEFT JOIN LATERAL (SELECT c.* FROM stdcontrat c WHERE c.idquittance = q.idquittance ORDER BY c.idcontrat LIMIT 1) ct ON TRUE
    LEFT JOIN stdavenant a ON a.idavenant = ct.idavenant
    LEFT JOIN stdcompagnie cie ON cie.idcompagnie = COALESCE(ct.idcompagnie, q.idaperiteur)
    LEFT JOIN stdproduit p ON p.idproduit = q.idproduit
    LEFT JOIN stdclient cl ON cl.idclient = q.idclient
"""
CONDITION_A_REGLER = (f"q.primettc < 0 AND q.primettc - COALESCE(q.mt_encaisse, 0) <= -{RELIQUAT_NEGLIGEABLE} "
                      "AND TRIM(COALESCE(q.nature, '')) <> 'A' AND COALESCE(ct.idcontratannulation, 0) = 0")


class ErreurRistourne(Exception):
    """Règlement refusé : message affiché tel quel."""


def _nombre(valeur):
    return float(valeur or 0)


def _iso(valeur):
    if isinstance(valeur, datetime):
        valeur = valeur.date()
    return valeur.isoformat() if isinstance(valeur, date) else None


def _montant(valeur, libelle):
    try:
        montant = Decimal(str(valeur).replace(" ", "").replace(",", ".")).quantize(CENTIME)
    except (InvalidOperation, ValueError, TypeError) as erreur:
        raise ErreurRistourne(f"{libelle} : montant invalide.") from erreur
    if montant <= 0:
        raise ErreurRistourne(f"{libelle} : le montant doit être positif.")
    return montant


def _francs(valeur):
    valeur = Decimal(valeur)
    texte = f"{valeur:,.0f}" if valeur == valeur.to_integral_value() else f"{valeur:,.2f}"
    return texte.replace(",", " ").replace(".", ",")


def _ristourne_json(q):
    return {
        "IdQuittance": q["idquittance"], "NumeroQuittance": q["numeroquittance"], "IdClient": q["idclient"], "Client": q["client"],
        "NumeroPolice": q["police"], "IdContrat": q["idcontrat"], "Compagnie": q["compagnie"], "Branche": _branche(q["idproduit"], q["branche"]),
        "CodeAvenant": q["codeavenant"], "Mouvement": q["mouvement"], "NumeroAvenant": q["numeroavenant"],
        "DateEmission": _iso(q["dateemission"]), "DateEffet": _iso(q["dateeffet"]), "DateExpiration": _iso(q["dateexpiration"]),
        # Montants positifs à l'écran : la ristourne, ce qui en est déjà réglé, ce qui reste à rendre ou à imputer
        "Ristourne": _nombre(-q["primettc"]), "DejaRegle": _nombre(-q["regle"]), "Reste": _nombre(-q["reste"]),
    }


# ------------------------------------------------------------------ lectures
def modes_remboursement(cursor):
    """Modes d'un remboursement : espèces, chèque ou virement du cabinet, paiement mobile, et « A la compagnie » (la compagnie
    rembourse elle-même le client)."""
    modes = _lignes(cursor, """
        SELECT idmodeencaissement, TRIM(libellemodepaiement) AS libelle, UPPER(TRIM(COALESCE(abregereglement, ''))) AS abrege,
               COALESCE(banque, FALSE) AS banque
        FROM stdmodeencaissement
        WHERE UPPER(TRIM(COALESCE(abregereglement, ''))) IN ('ESP', 'CHQ', 'VIR', 'PYM') AND libellemodepaiement NOT ILIKE '%%PPA%%'
        ORDER BY idmodeencaissement
    """)
    return [{"IdMode": m["idmodeencaissement"], "Libelle": m["libelle"], "Abrege": m["abrege"], "Banque": m["banque"],
             "Compagnie": m["libelle"].lower() == "a la compagnie"} for m in modes]


def mode_imputation(cursor):
    cursor.execute("SELECT idmodeencaissement FROM stdmodeencaissement WHERE UPPER(TRIM(libellemodepaiement)) = %s ORDER BY 1 LIMIT 1",
                   [LIBELLE_IMPUTATION])
    ligne = cursor.fetchone()
    return ligne[0] if ligne else None


def ristournes_a_regler(cursor):
    return [_ristourne_json(q) for q in _lignes(
        cursor, SQL_QUITTANCE + f" WHERE {CONDITION_A_REGLER} ORDER BY q.dateemission DESC NULLS LAST, q.idquittance DESC")]


def ristournes_reglees(cursor, id_encaissement=None):
    """Pièces de caisse qui ont réglé une ristourne (remboursements et imputations), les plus récentes d'abord : une ligne
    négative sur une ristourne. Une contre-passation porte la ligne inverse (positive) : elle n'y figure pas, la pièce
    d'origine est marquée annulée."""
    filtre = "AND e.idencaissement = %s" if id_encaissement else ""
    pieces = _lignes(cursor, f"""
        SELECT e.idencaissement, TRIM(e.numeropiece) AS numeropiece, e.dateencaissement::date AS jour, e.montantencaissement,
               TRIM(COALESCE(m.libellemodepaiement, '')) AS mode, UPPER(TRIM(COALESCE(m.libellemodepaiement, ''))) = %s AS imputation,
               COALESCE(NULLIF(TRIM(e.numerocheque), ''), NULLIF(TRIM(e.numerobordereau), ''), NULLIF(TRIM(e.numerorecuoperateur), ''), '') AS reference,
               TRIM(COALESCE(bq.libelle, '')) AS banque, TRIM(COALESCE(e.nomtireurcheque, '')) AS beneficiaire,
               TRIM(COALESCE(e.motifcompensation, '')) AS motif, COALESCE(e.piece_annulee, FALSE) AS annulee,
               TRIM(COALESCE(e.motifannulation, '')) AS motifannulation, TRIM(COALESCE(u.name, '')) AS operateur,
               EXISTS (SELECT 1 FROM stddetailencaissement d2 WHERE d2.idencaissement = e.idencaissement
                         AND (COALESCE(d2.montantreglement, 0) > 0
                              OR EXISTS (SELECT 1 FROM stddetailreversement r WHERE r.iddetailencaissement = d2.iddetailencaissement))) AS reverse,
               e.dateencaissement::date >= date_trunc('year', CURRENT_DATE)::date AS exercice_courant
        FROM stdencaissement e
        LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
        LEFT JOIN stdbanque bq ON bq.idbanque = e.idbanque AND bq.idbanque <> 1
        LEFT JOIN account_uranususer u ON u.id = e.idutilisateur
        WHERE EXISTS (SELECT 1 FROM stddetailencaissement de JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
                      WHERE de.idencaissement = e.idencaissement AND q.primettc < 0 AND de.montant_encaissement < 0
                        AND TRIM(COALESCE(q.nature, '')) <> 'A') {filtre}
        ORDER BY e.dateencaissement DESC, e.idencaissement DESC
        LIMIT {REGLEES_AFFICHEES}
    """, [LIBELLE_IMPUTATION] + ([id_encaissement] if id_encaissement else []))
    if not pieces:
        return []
    lignes = {}
    for l in _lignes(cursor, """
        SELECT de.idencaissement, de.numeroquittance, de.montant_encaissement, q.primettc,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client, TRIM(COALESCE(q.numeropolice, '')) AS police
        FROM stddetailencaissement de JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
        LEFT JOIN stdclient cl ON cl.idclient = q.idclient
        WHERE de.idencaissement = ANY(%s) ORDER BY de.iddetailencaissement
    """, [[p["idencaissement"] for p in pieces]]):
        lignes.setdefault(l["idencaissement"], []).append(l)
    resultat = []
    for p in pieces:
        ls = lignes.get(p["idencaissement"], [])
        ristournes = [l for l in ls if l["primettc"] < 0]
        payees = [l for l in ls if l["primettc"] >= 0]
        resultat.append({
            "IdEncaissement": p["idencaissement"], "NumeroPiece": p["numeropiece"], "Date": _iso(p["jour"]),
            "Type": "IMPUTATION" if p["imputation"] else "REMBOURSEMENT", "Mode": p["mode"], "Reference": p["reference"],
            "Banque": p["banque"], "Beneficiaire": p["beneficiaire"], "Motif": p["motif"], "Operateur": p["operateur"],
            "Montant": _nombre(-sum((l["montant_encaissement"] for l in ristournes), Decimal(0))),
            "Client": ristournes[0]["client"] if ristournes else "",
            "Ristournes": [{"NumeroQuittance": l["numeroquittance"], "Police": l["police"], "Montant": _nombre(-l["montant_encaissement"])}
                           for l in ristournes],
            "PrimesPayees": [{"NumeroQuittance": l["numeroquittance"], "Police": l["police"], "Montant": _nombre(l["montant_encaissement"])}
                             for l in payees],
            "Annulee": p["annulee"], "MotifAnnulation": p["motifannulation"],
            # Seulement dans l'exercice en cours : un exercice passé ne se modifie plus
            "Annulable": not p["annulee"] and not p["reverse"] and p["exercice_courant"],
            "ExerciceCourant": p["exercice_courant"], "Reverse": p["reverse"],
        })
    return resultat


def primes_imputables(cursor, id_quittance):
    """Primes du client de la ristourne encore à payer, sur lesquelles l'imputer."""
    q = _ristourne(cursor, id_quittance)
    primes = _lignes(cursor, SQL_QUITTANCE + f"""
        WHERE q.idclient = %s AND q.primettc > 0 AND q.primettc - COALESCE(q.mt_encaisse, 0) >= {RELIQUAT_NEGLIGEABLE}
          AND TRIM(COALESCE(q.nature, '')) <> 'A' AND COALESCE(ct.idcontratannulation, 0) = 0
        ORDER BY q.dateeffet DESC NULLS LAST, q.idquittance DESC
    """, [q["idclient"]])
    return {
        "Ristourne": _ristourne_json(q),
        "Primes": [{
            "IdQuittance": p["idquittance"], "NumeroQuittance": p["numeroquittance"], "NumeroPolice": p["police"],
            "Compagnie": p["compagnie"], "Branche": _branche(p["idproduit"], p["branche"]), "CodeAvenant": p["codeavenant"],
            "Mouvement": p["mouvement"], "DateEffet": _iso(p["dateeffet"]),
            "DateExpiration": _iso(p["dateexpiration"]), "PrimeTtc": _nombre(p["primettc"]), "DejaPaye": _nombre(p["regle"]),
            "Reste": _nombre(p["reste"]),
        } for p in primes],
    }


def _ristourne(cursor, id_quittance, verrou=False):
    """Ristourne à régler, verrouillée au besoin ; refus expliqué sinon."""
    if verrou:
        cursor.execute("SELECT 1 FROM stdquittance WHERE idquittance = %s FOR UPDATE", [id_quittance])
    lignes = _lignes(cursor, SQL_QUITTANCE + " WHERE q.idquittance = %s", [id_quittance])
    if not lignes:
        raise ErreurRistourne("Quittance introuvable.")
    q = lignes[0]
    if q["primettc"] >= 0:
        raise ErreurRistourne(f"La quittance {q['numeroquittance']} n'est pas une ristourne : elle se règle à la caisse.")
    if q["nature"] == "A":
        raise ErreurRistourne(f"La quittance {q['numeroquittance']} annule une autre quittance : elle ne se rembourse pas ici.")
    if q["annule"]:
        raise ErreurRistourne(f"Le contrat de la quittance {q['numeroquittance']} est annulé.")
    if -q["reste"] < RELIQUAT_NEGLIGEABLE:
        raise ErreurRistourne(f"La ristourne {q['numeroquittance']} est déjà entièrement réglée.")
    return q


# ------------------------------------------------------------------ écritures
def _controler_partiel(cursor, partiel):
    """Règlement partiel d'une ristourne : seulement avec sp_enregistrement_encaissement v7 (migration production 0225). La v6
    plafonnait la quittance négative à son montant et comptait le solde du client sur toute la ristourne ; un règlement
    total y reste juste."""
    if not partiel:
        return
    cursor.execute("SELECT bool_or(prosrc LIKE '%%SQ.PrimeTTC < 0%%') FROM pg_proc WHERE proname = 'sp_enregistrement_encaissement'")
    if not cursor.fetchone()[0]:
        raise ErreurRistourne("Règlement partiel d'une ristourne impossible tant que la migration production 0225 n'est pas appliquée : "
                              "réglez la ristourne en entier.")


def _enregistrer(cursor, utilisateur, id_mode, id_banque, montant_total, numero, reference, compensation, nom, lignes):
    """Pièce de caisse par sp_enregistrement_encaissement (v7 : quittances négatives) ; renvoie son identifiant."""
    cursor.execute(
        "CALL sp_enregistrement_encaissement(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
        [utilisateur.id, id_mode, date_emission_du_jour(), id_banque, montant_total, numero, reference, compensation, nom[:50],
         ";".join(n for n, _ in lignes), ";".join(str(m) for _, m in lignes), 0, ""],
    )
    id_encaissement, message = cursor.fetchone()
    if not id_encaissement:
        raise ErreurRistourne(str(message or "Le règlement n'a pas pu être enregistré.").replace("Erreur : ", "").split("\n")[0])
    return id_encaissement


def _piece(cursor, id_encaissement):
    cursor.execute("SELECT TRIM(numeropiece) FROM stdencaissement WHERE idencaissement = %s", [id_encaissement])
    return (cursor.fetchone() or [""])[0]


def rembourser(utilisateur, id_quittance, d):
    montant = _montant(d.get("Montant"), "Montant du remboursement")
    beneficiaire = str(d.get("Beneficiaire") or "").strip()
    reference = str(d.get("Reference") or "").strip()[:50]
    try:
        id_mode = int(d.get("IdMode") or 0)
        id_banque = int(d.get("IdBanque") or 1)
    except (TypeError, ValueError) as erreur:
        raise ErreurRistourne("Mode ou banque invalide.") from erreur
    date_cheque = None
    if d.get("DateCheque"):
        try:
            date_cheque = date.fromisoformat(str(d["DateCheque"])[:10])
        except ValueError as erreur:
            raise ErreurRistourne("Date du chèque invalide.") from erreur
    with transaction.atomic(), connection.cursor() as cursor:
        mode = next((m for m in modes_remboursement(cursor) if m["IdMode"] == id_mode), None)
        if not mode:
            raise ErreurRistourne("Choisissez le mode de remboursement.")
        q = _ristourne(cursor, id_quittance, verrou=True)
        reste = -q["reste"]
        if montant > reste:
            raise ErreurRistourne(f"Le remboursement de {_francs(montant)} F dépasse le reste de la ristourne ({_francs(reste)} F).")
        beneficiaire = beneficiaire or q["client"]
        if not beneficiaire:
            raise ErreurRistourne("Indiquez le bénéficiaire du remboursement.")
        abrege = mode["Abrege"]
        if mode["Banque"] and id_banque <= 1:
            raise ErreurRistourne("La banque du chèque ou du virement est à renseigner.")
        if abrege == "CHQ" and not reference:
            raise ErreurRistourne("Le numéro du chèque est à renseigner.")
        if abrege == "PYM" and not reference:
            raise ErreurRistourne("Le numéro du reçu de l'opérateur est à renseigner.")
        _controler_partiel(cursor, reste - montant >= RELIQUAT_NEGLIGEABLE)
        id_encaissement = _enregistrer(
            cursor, utilisateur, id_mode, id_banque if mode["Banque"] else 1, -montant,
            reference if mode["Banque"] else "", reference if abrege == "PYM" else "", "", beneficiaire,
            [(q["numeroquittance"], -montant)])
        Encaissement.objects.filter(idencaissement=id_encaissement).update(
            ordre_reglement=Encaissement.ORDRE_COMPAGNIE if mode["Compagnie"] else Encaissement.ORDRE_CABINET,
            numero_bordereau=(reference or None) if abrege == "ESP" else None,
            numero_recu_operateur=(reference or None) if abrege == "PYM" else None,
            date_cheque=date_cheque if mode["Banque"] else None,
        )
        numero_piece = _piece(cursor, id_encaissement)
        journaliser(
            utilisateur=utilisateur, module=MODULE, action="encaissements.ristourne.remboursement", objet_type="encaissement",
            objet_id=id_encaissement, type_operation="ENCAISSEMENT",
            description=f"Ristourne {q['numeroquittance']} remboursée : {_francs(montant)} F, {mode['Libelle']}, pièce {numero_piece}",
            details={"Quittance": q["numeroquittance"], "Montant": str(montant), "Mode": mode["Libelle"], "Reference": reference,
                     "Beneficiaire": beneficiaire, "Piece": numero_piece},
        )
    return {"IdEncaissement": id_encaissement, "NumeroPiece": numero_piece, "Montant": _nombre(montant),
            "Reste": _nombre(reste - montant), "Type": "REMBOURSEMENT"}


def imputer(utilisateur, id_quittance, d):
    brutes = d.get("Lignes") or []
    if not isinstance(brutes, list) or not brutes:
        raise ErreurRistourne("Choisissez la ou les primes à payer avec la ristourne.")
    demandes = []
    for ligne in brutes:
        numero = str((ligne or {}).get("NumeroQuittance") or "").strip()
        if not numero:
            raise ErreurRistourne("Quittance à payer non précisée.")
        demandes.append((numero, _montant((ligne or {}).get("Montant"), f"Quittance {numero}")))
    if len({n for n, _ in demandes}) != len(demandes):
        raise ErreurRistourne("Une même prime figure deux fois dans l'imputation.")
    motif = str(d.get("Motif") or "").strip()[:255]
    with transaction.atomic(), connection.cursor() as cursor:
        id_mode = mode_imputation(cursor)
        if not id_mode:
            raise ErreurRistourne("Le mode « CMP Prime / Ristourne » n'existe pas dans les modes d'encaissement.")
        q = _ristourne(cursor, id_quittance, verrou=True)
        numeros = [n for n, _ in demandes]
        if q["numeroquittance"] in numeros:
            raise ErreurRistourne("La ristourne ne peut pas se payer elle-même.")
        cursor.execute("SELECT 1 FROM stdquittance WHERE numeroquittance = ANY(%s) FOR UPDATE", [numeros])
        cibles = {p["numeroquittance"]: p for p in _lignes(cursor, SQL_QUITTANCE + " WHERE q.numeroquittance = ANY(%s)", [numeros])}
        for numero, montant in demandes:
            p = cibles.get(numero)
            if not p:
                raise ErreurRistourne(f"Quittance {numero} introuvable.")
            if p["idclient"] != q["idclient"]:
                raise ErreurRistourne(f"La quittance {numero} est celle d'un autre client : la ristourne ne paie que les primes de son client.")
            if p["primettc"] <= 0 or p["nature"] == "A" or p["annule"]:
                raise ErreurRistourne(f"La quittance {numero} n'est pas une prime à payer.")
            if p["reste"] < RELIQUAT_NEGLIGEABLE:
                raise ErreurRistourne(f"La prime {numero} est déjà soldée.")
            if montant > p["reste"]:
                raise ErreurRistourne(f"Quittance {numero} : {_francs(montant)} F dépasse le reste à payer ({_francs(p['reste'])} F).")
        total = sum((m for _, m in demandes), Decimal(0))
        reste = -q["reste"]
        if total > reste:
            raise ErreurRistourne(f"L'imputation de {_francs(total)} F dépasse le reste de la ristourne ({_francs(reste)} F).")
        _controler_partiel(cursor, reste - total >= RELIQUAT_NEGLIGEABLE)
        motif = motif or (f"Ristourne {q['numeroquittance']} imputée sur "
                          + ", ".join(f"{n} ({_francs(m)} F)" for n, m in demandes))[:255]
        id_encaissement = _enregistrer(
            cursor, utilisateur, id_mode, 1, Decimal(0), "", "", q["numeroquittance"], q["client"] or "Client",
            [(q["numeroquittance"], -total)] + demandes)
        Encaissement.objects.filter(idencaissement=id_encaissement).update(
            motif_compensation=motif, ordre_reglement=Encaissement.ORDRE_CABINET)
        numero_piece = _piece(cursor, id_encaissement)
        journaliser(
            utilisateur=utilisateur, module=MODULE, action="encaissements.ristourne.imputation", objet_type="encaissement",
            objet_id=id_encaissement, type_operation="ENCAISSEMENT",
            description=f"Ristourne {q['numeroquittance']} imputée : {_francs(total)} F sur {', '.join(numeros)}, pièce {numero_piece}",
            details={"Quittance": q["numeroquittance"], "Montant": str(total), "Primes": {n: str(m) for n, m in demandes},
                     "Motif": motif, "Piece": numero_piece},
        )
    return {"IdEncaissement": id_encaissement, "NumeroPiece": numero_piece, "Montant": _nombre(total),
            "Reste": _nombre(reste - total), "Type": "IMPUTATION"}


def annuler(utilisateur, id_encaissement, motif):
    """Remboursement ou imputation saisi par erreur : contre-passé, la ristourne (et la prime payée) redeviennent à régler."""
    if len(motif) < MOTIF_MINIMUM:
        raise ErreurRistourne(f"Indiquez le motif de l'annulation ({MOTIF_MINIMUM} caractères au moins).")
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM stdencaissement WHERE idencaissement = %s FOR UPDATE", [id_encaissement])
        piece = next(iter(ristournes_reglees(cursor, id_encaissement)), None)
        if not piece:
            raise ErreurRistourne("Ce règlement n'est pas un remboursement ni une imputation de ristourne.")
        if piece["Annulee"]:
            raise ErreurRistourne("Ce règlement est déjà annulé.")
        if not piece["ExerciceCourant"]:
            raise ErreurRistourne("Règlement d'un exercice passé : il ne s'annule plus.")
        if not piece["Annulable"]:
            raise ErreurRistourne("Une prime payée par ce règlement a déjà été reversée à la compagnie : annulez d'abord le bordereau.")
        cursor.execute("CALL sp_annulation_encaissement(%s, %s, %s, %s, %s, %s);",
                       [id_encaissement, utilisateur.id, date_emission_du_jour(), f"Annulation : {motif}"[:255], 0, ""])
        ligne = cursor.fetchone()
        if not ligne or not ligne[0]:
            raise ErreurRistourne(str((ligne[1] if ligne else "") or "L'annulation n'a pas pu être enregistrée.").split("\n")[0])
        journaliser(
            utilisateur=utilisateur, module=MODULE, action="encaissements.ristourne.annulation", objet_type="encaissement",
            objet_id=id_encaissement, type_operation="ENCAISSEMENT", motif=motif,
            description=f"{'Imputation' if piece['Type'] == 'IMPUTATION' else 'Remboursement'} de ristourne annulé : pièce {piece['NumeroPiece']}",
            details={"Piece": piece["NumeroPiece"], "Montant": piece["Montant"], "Contrepassation": ligne[0]},
        )
    return {"IdEncaissement": id_encaissement, "IdContrepassation": ligne[0], "NumeroPiece": piece["NumeroPiece"]}


# ------------------------------------------------------------------ vues
def _refus(erreur):
    return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)


def _executer(fonction, *args, statut=status.HTTP_200_OK):
    try:
        return Response(fonction(*args), status=statut)
    except ErreurRistourne as erreur:
        return _refus(erreur)
    except DatabaseError as erreur:
        logger.exception("Ristourne : opération refusée par la base.")
        return _refus(str(erreur).splitlines()[0][:300] or "Opération impossible pour le moment.")


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def ristournes(request):
    def lire():
        with connection.cursor() as cursor:
            return {"ARegler": ristournes_a_regler(cursor), "Reglees": ristournes_reglees(cursor),
                    "Modes": modes_remboursement(cursor), "Imputation": bool(mode_imputation(cursor))}
    return _executer(lire)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def imputation_primes(request, idquittance):
    def lire():
        with connection.cursor() as cursor:
            return primes_imputables(cursor, idquittance)
    return _executer(lire)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def remboursement(request, idquittance):
    return _executer(rembourser, request.user, idquittance, request.data or {}, statut=status.HTTP_201_CREATED)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def imputation(request, idquittance):
    return _executer(imputer, request.user, idquittance, request.data or {}, statut=status.HTTP_201_CREATED)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def annulation(request, idencaissement):
    motif = str((request.data or {}).get("Motif") or "").strip()[:255]
    return _executer(annuler, request.user, idencaissement, motif)
