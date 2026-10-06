"""
Flux financiers du cabinet après l'encaissement des primes (Code CIMA) :

1. État récapitulatif des encaissements : montant, mode, référence et statut de chaque ligne
   encaissée (quittance), par compagnie.
2. Reversement à la compagnie : le cabinet reverse la prime encaissée ENTIÈRE (le courtier ne
   déduit pas sa commission des primes à reverser). Procédures d'URANUS sp_enregistrement_reversement
   (montants par ligne d'encaissement, numéro de reversement) et sp_validation_reversement (paiement
   à la compagnie : chèque, virement…). Bordereau de reversement au modèle d'OREOLE (Compagnie,
   Client, Branche, Police, Quittance, Avenant, dates, prime nette, accessoire, taxe, TTC, commission).
3. Réclamation des commissions : bordereau récapitulatif (en général mensuel) des quittances
   reversées cochées, qui réclame à l'assureur la commission due au cabinet.
4. Encaissement des commissions : règlement de l'assureur (chèque ou virement) imputé sur les
   lignes du bordereau ; états des commissions payées et non payées (chiffre d'affaires du
   cabinet = commissions, pas émissions).

Commission due d'une quittance = commission du contrat (stdcontrat.commissionintermediaire, la
colonne « Comm. Interm. » du bordereau) au prorata de la prime reversée sur la prime TTC.

Encaissements repris d'URANUS (saisis en décembre 2025, encaissés jusqu'au 14/11/2025) : réputés
reversés hors LE PHARE, ils ne sont pas proposés au reversement (DEBUT_REVERSEMENTS).
"""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import connection, transaction
from django.db.models import Sum
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from configuration_api.parametrage import valeur_parametre
from institutionnel.authentication import KnoxOrDemoTokenAuthentication

AUTHENTIFICATION = [KnoxOrDemoTokenAuthentication, BasicAuthentication]
# Premier jour des encaissements saisis dans LE PHARE (avant : reprise d'URANUS) ; réglable dans
# l'admin (Le cabinet > Règles de gestion, paramètre « finance.debut_reversements »)
DEBUT_REVERSEMENTS = date(2025, 12, 1)


def debut_reversements():
    return valeur_parametre("finance.debut_reversements", DEBUT_REVERSEMENTS)
ZERO = Decimal("0")


class ErreurFinance(Exception):
    """Saisie refusée : message affiché tel quel."""


class EcrituresAdministrateur(permissions.BasePermission):
    """Lecture pour tout utilisateur connecté ; reversements, réclamations et règlements de
    commissions réservés aux administrateurs (direction financière)."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and getattr(request.user, "is_admin", False))


def _franc(valeur):
    return Decimal(valeur or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _nombre(valeur):
    return float(valeur) if valeur is not None else 0.0


def _date(valeur, champ, obligatoire=True):
    if not valeur:
        if obligatoire:
            raise ErreurFinance(f"{champ} : à renseigner.")
        return None
    if isinstance(valeur, date):
        return valeur
    texte = str(valeur).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(texte, fmt).date()
        except ValueError:
            continue
    raise ErreurFinance(f"{champ} : date invalide ({valeur!r}).")


def _entier(valeur, champ, obligatoire=True):
    try:
        nombre = int(valeur or 0)
    except (TypeError, ValueError):
        raise ErreurFinance(f"{champ} : valeur invalide.")
    if obligatoire and nombre <= 0:
        raise ErreurFinance(f"{champ} : à renseigner.")
    return nombre


def _montant(valeur, champ):
    try:
        montant = Decimal(str(valeur).replace(" ", "").replace(",", "."))
    except (InvalidOperation, TypeError):
        raise ErreurFinance(f"{champ} : montant invalide.")
    if montant <= 0:
        raise ErreurFinance(f"{champ} : doit être positif.")
    return montant


def _lignes(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        colonnes = [c[0] for c in cursor.description]
        return [dict(zip(colonnes, ligne)) for ligne in cursor.fetchall()]


def _erreur(exc):
    message = str(exc).split("\n")[0]
    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


def _iso(valeur):
    if valeur is None:
        return None
    if isinstance(valeur, datetime):
        valeur = valeur.date()
    return valeur.isoformat()


# ------------------------------------------------------------------ lignes d'encaissement
# Une ligne par quittance encaissée : encaissement (mode, référence), quittance, contrat
# (avenant, commission), compagnie, branche, client, chèque éventuel
SQL_LIGNES_ENCAISSEMENT = """
    SELECT de.iddetailencaissement, e.idencaissement, e.numeropiece, e.dateencaissement::date AS dateencaissement,
           COALESCE(e.piece_annulee, FALSE) AS annulee, e.motifannulation,
           m.idmodeencaissement AS idmode, m.libellemodepaiement AS mode, UPPER(TRIM(COALESCE(m.abregereglement, ''))) AS abrege,
           COALESCE(NULLIF(TRIM(e.numerocheque), ''), NULLIF(TRIM(e.numerobordereau), ''), NULLIF(TRIM(e.numerorecuoperateur), ''),
                    NULLIF(TRIM(e.compte_compensation), ''), e.referencetransaction::text, '') AS reference,
           CASE WHEN UPPER(TRIM(COALESCE(b.libelle, ''))) IN ('', 'NEANT', 'AUCUNE', 'AUCUN') THEN NULL ELSE TRIM(b.libelle) END AS banque,
           de.montant_encaissement, COALESCE(de.montantreglement, 0) AS montantreverse,
           q.idquittance, q.numeroquittance, q.numeropolice, q.dateemission, q.dateeffet::date AS dateeffet,
           q.dateexpiration::date AS dateexpiration, q.primenette, q.accessoire, q.taxe, q.primettc,
           ct.idcontrat, ct.numeroavenant, COALESCE(ct.commissionintermediaire, 0) AS commission,
           cie.idcompagnie, cie.raisonsociale AS compagnie, p.libelleproduit AS branche,
           TRIM(cl.nom || ' ' || COALESCE(cl.prenoms, '')) AS client,
           ch.statut AS statutcheque
    FROM stddetailencaissement de
    JOIN stdencaissement e ON e.idencaissement = de.idencaissement
    JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
    LEFT JOIN LATERAL (SELECT c.idcontrat, c.numeroavenant, c.commissionintermediaire, c.idcompagnie
                       FROM stdcontrat c WHERE c.idquittance = q.idquittance ORDER BY c.idcontrat LIMIT 1) ct ON TRUE
    LEFT JOIN stdcompagnie cie ON cie.idcompagnie = COALESCE(ct.idcompagnie, q.idaperiteur)
    LEFT JOIN stdproduit p ON p.idproduit = q.idproduit
    LEFT JOIN stdclient cl ON cl.idclient = q.idclient
    LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
    LEFT JOIN stdbanque b ON b.idbanque = e.idbanque
    LEFT JOIN LATERAL (SELECT c.statut FROM stdchequeoperation op JOIN stdcheque c ON c.idcheque = op.idcheque
                       WHERE op.idencaissement = e.idencaissement ORDER BY op.idoperation DESC LIMIT 1) ch ON TRUE
"""

LIBELLES_STATUT = {
    "ANNULE": "Annulé",
    "IMPAYE": "Chèque impayé",
    "REVERSE": "Reversé à la compagnie",
    "PARTIEL": "Partiellement reversé",
    "A_REVERSER": "À reverser",
    "DECAISSEMENT": "Décaissement (déduit)",
    "DEDUIT": "Couvert par un décaissement",
    "REPRIS": "Repris d'URANUS",
}

# Modes qui sortent de l'argent d'une quittance (enregistrés en positif par la caisse) : leur
# montant est compté en négatif et déduit du reste à reverser de la quittance
MODES_DECAISSEMENT = {"DMA"}  # Décaissement de prime mal affectée


def _est_decaissement(ligne):
    return ligne["abrege"] in MODES_DECAISSEMENT


def _restes_nets(numeros_quittance):
    """Reste à reverser de chaque ligne d'encaissement, décaissements de la quittance déduits :
    reste net de la quittance = encaissé − reversé − décaissé (au moins 0), réparti sur ses
    lignes d'encaissement dans l'ordre chronologique."""
    if not numeros_quittance:
        return {}
    toutes = _lignes(
        SQL_LIGNES_ENCAISSEMENT
        + " WHERE de.numeroquittance = ANY(%s) AND NOT COALESCE(e.piece_annulee, FALSE) AND de.montant_encaissement > 0"
        + " ORDER BY e.dateencaissement, de.iddetailencaissement",
        [list(numeros_quittance)],
    )
    par_quittance = {}
    for l in toutes:
        par_quittance.setdefault(l["numeroquittance"], []).append(l)
    restes = {}
    for lignes in par_quittance.values():
        encaissements = [l for l in lignes if not _est_decaissement(l)]
        decaisse = sum((l["montant_encaissement"] for l in lignes if _est_decaissement(l)), ZERO)
        net = max(sum((max(l["montant_encaissement"] - l["montantreverse"], ZERO) for l in encaissements), ZERO) - decaisse, ZERO)
        for l in encaissements:
            part = min(max(l["montant_encaissement"] - l["montantreverse"], ZERO), net)
            restes[l["iddetailencaissement"]] = part
            net -= part
    return restes


def _statut_encaissement(ligne, reste_net=None):
    if ligne["annulee"]:
        return "IMPAYE" if ligne["statutcheque"] in ("IMPAYE", "REENCAISSE") else "ANNULE"
    if _est_decaissement(ligne):
        return "DECAISSEMENT"
    if ligne["montantreverse"] >= ligne["montant_encaissement"] > 0:
        return "REVERSE"
    if ligne["dateencaissement"] and ligne["dateencaissement"] < debut_reversements() and ligne["montantreverse"] == 0:
        return "REPRIS"
    if reste_net is not None and reste_net <= 0:
        return "DEDUIT"
    if ligne["montantreverse"] > 0:
        return "PARTIEL"
    return "A_REVERSER"


def _ligne_bordereau(ligne):
    """Colonnes du bordereau d'OREOLE (une quittance)."""
    return {
        "IdDetailEncaissement": ligne["iddetailencaissement"],
        "Compagnie": ligne["compagnie"] or "",
        "IdCompagnie": ligne["idcompagnie"],
        "Client": ligne["client"] or "",
        "Branche": ligne["branche"] or "",
        "NumeroPolice": ligne["numeropolice"] or "",
        "NumeroQuittance": ligne["numeroquittance"],
        "NumeroAvenant": (ligne["numeroavenant"] or "").strip(),
        "DateEmission": _iso(ligne["dateemission"]),
        "DateEffet": _iso(ligne["dateeffet"]),
        "DateExpiration": _iso(ligne["dateexpiration"]),
        "PrimeNette": _nombre(ligne["primenette"]),
        "Accessoire": _nombre(ligne["accessoire"]),
        "Taxe": _nombre(ligne["taxe"]),
        "PrimeTtc": _nombre(ligne["primettc"]),
        "Commission": _nombre(ligne["commission"]),
    }


def _ligne_encaissement(ligne, restes=None):
    """restes : reste à reverser net par ligne (_restes_nets), décaissements de la quittance déduits."""
    reste_net = (restes or {}).get(ligne["iddetailencaissement"]) if restes is not None else None
    statut = _statut_encaissement(ligne, reste_net)
    if statut in ("A_REVERSER", "PARTIEL"):
        reste = reste_net if reste_net is not None else max(ligne["montant_encaissement"] - ligne["montantreverse"], ZERO)
    else:
        reste = ZERO
    signe = -1 if statut == "DECAISSEMENT" else 1
    return {
        **_ligne_bordereau(ligne),
        "IdEncaissement": ligne["idencaissement"],
        "NumeroPiece": ligne["numeropiece"] or "",
        "DateEncaissement": _iso(ligne["dateencaissement"]),
        "Mode": ligne["mode"] or "",
        "IdMode": ligne["idmode"],
        "Reference": ligne["reference"] or "",
        "Banque": ligne["banque"] or "",
        # Décaissement : compté en négatif (déduit des totaux et du reste à reverser)
        "Montant": _nombre(ligne["montant_encaissement"]) * signe,
        "MontantReverse": _nombre(ligne["montantreverse"]),
        "ResteAReverser": _nombre(reste),
        "Statut": statut,
        "LibelleStatut": LIBELLES_STATUT[statut],
        "MotifAnnulation": (ligne["motifannulation"] or "").strip(),
    }


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def etat_encaissements(request):
    """GET /api/finance/encaissements/?du=&au=&compagnie=&mode=&statut= : état récapitulatif."""
    try:
        du = _date(request.query_params.get("du"), "Du", obligatoire=False) or date(date.today().year, 1, 1)
        au = _date(request.query_params.get("au"), "Au", obligatoire=False) or date.today()
    except ErreurFinance as erreur:
        return _erreur(erreur)
    # Contre-passations d'une annulation (montants négatifs) écartées : la ligne d'origine porte
    # le statut « Annulé » et son motif
    conditions, params = ["e.dateencaissement::date BETWEEN %s AND %s", "de.montant_encaissement > 0"], [du, au]
    if request.query_params.get("compagnie"):
        conditions.append("cie.idcompagnie = %s")
        params.append(int(request.query_params["compagnie"]))
    if request.query_params.get("mode"):
        conditions.append("e.idmodepaiement = %s")
        params.append(int(request.query_params["mode"]))
    brutes = _lignes(SQL_LIGNES_ENCAISSEMENT + " WHERE " + " AND ".join(conditions) + " ORDER BY e.dateencaissement, e.idencaissement, de.iddetailencaissement", params)
    restes = _restes_nets({l["numeroquittance"] for l in brutes})
    lignes = [_ligne_encaissement(l, restes) for l in brutes]
    statut = request.query_params.get("statut")
    if statut:
        lignes = [l for l in lignes if l["Statut"] == statut]

    def totaux(cle):
        resultat = {}
        for l in lignes:
            if l["Statut"] in ("ANNULE", "IMPAYE"):
                continue
            groupe = resultat.setdefault(l[cle] or "—", {"Libelle": l[cle] or "—", "Nombre": 0, "Montant": 0.0, "Reverse": 0.0})
            groupe["Nombre"] += 1
            groupe["Montant"] += l["Montant"]
            groupe["Reverse"] += l["MontantReverse"]
        return sorted(resultat.values(), key=lambda g: -g["Montant"])

    valides = [l for l in lignes if l["Statut"] not in ("ANNULE", "IMPAYE")]
    return Response({
        "Du": du.isoformat(), "Au": au.isoformat(),
        "Lignes": lignes,
        "ParMode": totaux("Mode"),
        "ParCompagnie": totaux("Compagnie"),
        "ParStatut": [
            {"Statut": s, "Libelle": LIBELLES_STATUT[s], "Nombre": sum(1 for l in lignes if l["Statut"] == s),
             "Montant": sum(l["Montant"] for l in lignes if l["Statut"] == s)}
            for s in LIBELLES_STATUT if any(l["Statut"] == s for l in lignes)
        ],
        "Total": {"Nombre": len(valides), "Montant": sum(l["Montant"] for l in valides),
                  "Reverse": sum(l["MontantReverse"] for l in valides),
                  "ResteAReverser": sum(l["ResteAReverser"] for l in valides)},
        "DebutReversements": debut_reversements().isoformat(),
    })


# ------------------------------------------------------------------ reversements
@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def lignes_a_reverser(request):
    """GET /api/finance/reversements/a-reverser/?compagnie= : primes encaissées non encore reversées."""
    try:
        id_compagnie = _entier(request.query_params.get("compagnie"), "Compagnie")
    except ErreurFinance as erreur:
        return _erreur(erreur)
    lignes = _lignes(
        SQL_LIGNES_ENCAISSEMENT + """
        WHERE cie.idcompagnie = %s AND NOT COALESCE(e.piece_annulee, FALSE)
          AND de.montant_encaissement > COALESCE(de.montantreglement, 0)
          AND e.dateencaissement::date >= %s
        ORDER BY e.dateencaissement, de.iddetailencaissement
        """,
        [id_compagnie, debut_reversements()],
    )
    # Décaissements jamais reversés : déduits du reste à reverser de leur quittance
    restes = _restes_nets({l["numeroquittance"] for l in lignes})
    resultat = [_ligne_encaissement(l, restes) for l in lignes if not _est_decaissement(l)]
    return Response({
        "Lignes": [l for l in resultat if l["ResteAReverser"] > 0],
        "DebutReversements": debut_reversements().isoformat(),
    })


def _entete_reversement(ligne):
    valide = bool(ligne["valide"])
    return {
        "IdReversement": ligne["idreversement"],
        "Numero": (ligne["numeroreversement"] or "").strip(),
        "DateReversement": _iso(ligne["datereversement"]),
        "IdCompagnie": ligne["idcompagnie"],
        "Compagnie": ligne["compagnie"] or "",
        "Montant": _nombre(ligne["montantreversement"]),
        "NombreQuittances": ligne["nombre"],
        "Commissions": _nombre(ligne["commissions"]),
        "Valide": valide,
        "DateValidation": _iso(ligne["datevalidation"]),
        "Mode": ligne["mode"] or "",
        "Reference": (ligne["numerocheque"] or ligne["comptecompensation"] or "").strip(),
        "Banque": ligne["banque"] or "",
        "Statut": "PAYE" if valide else "A_PAYER",
        "LibelleStatut": "Payé à la compagnie" if valide else "À payer à la compagnie",
    }


SQL_REVERSEMENTS = """
    SELECT r.idreversement, r.numeroreversement, r.datereversement, r.idcompagnie, cie.raisonsociale AS compagnie,
           r.montantreversement, r.valide, r.datevalidation, r.numerocheque, r.comptecompensation,
           m.libellemodepaiement AS mode, NULLIF(TRIM(b.libelle), '') AS banque,
           (SELECT COUNT(*) FROM stddetailreversement d WHERE d.idreversement = r.idreversement) AS nombre,
           (SELECT COALESCE(SUM(CASE WHEN q.primettc > 0 THEN ROUND(COALESCE(ct.commissionintermediaire, 0) * d.montantreverse / q.primettc, 0) ELSE 0 END), 0)
            FROM stddetailreversement d
            JOIN stddetailencaissement de ON de.iddetailencaissement = d.iddetailencaissement
            JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
            LEFT JOIN LATERAL (SELECT c.commissionintermediaire FROM stdcontrat c WHERE c.idquittance = q.idquittance ORDER BY c.idcontrat LIMIT 1) ct ON TRUE
            WHERE d.idreversement = r.idreversement) AS commissions
    FROM stdreversementcompagnie r
    LEFT JOIN stdcompagnie cie ON cie.idcompagnie = r.idcompagnie
    LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = r.idmodereversement
    LEFT JOIN stdbanque b ON b.idbanque = r.idbanque
    WHERE NOT COALESCE(r.pieceannulee, FALSE)
"""


def _lire_reversement(id_reversement):
    entetes = _lignes(SQL_REVERSEMENTS + " AND r.idreversement = %s", [id_reversement])
    if not entetes:
        return None
    lignes = _lignes(
        SQL_LIGNES_ENCAISSEMENT.replace(
            "FROM stddetailencaissement de",
            "FROM stddetailreversement dr JOIN stddetailencaissement de ON de.iddetailencaissement = dr.iddetailencaissement",
        ).replace("SELECT de.iddetailencaissement,", "SELECT dr.iddetailreversement, dr.montantreverse AS montantdetailreverse, de.iddetailencaissement,")
        + " WHERE dr.idreversement = %s ORDER BY e.dateencaissement, de.iddetailencaissement",
        [id_reversement],
    )
    details = []
    for l in lignes:
        part = (l["montantdetailreverse"] / l["primettc"]) if l["primettc"] else ZERO
        details.append({
            **_ligne_bordereau(l),
            "IdDetailReversement": l["iddetailreversement"],
            "NumeroPiece": l["numeropiece"] or "",
            "DateEncaissement": _iso(l["dateencaissement"]),
            "Mode": l["mode"] or "",
            "Reference": l["reference"] or "",
            "MontantReverse": _nombre(l["montantdetailreverse"]),
            "CommissionDue": _nombre(_franc(Decimal(l["commission"]) * part)),
        })
    return {**_entete_reversement(entetes[0]), "Lignes": details}


@api_view(["GET", "POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EcrituresAdministrateur])
def reversements(request):
    """GET /api/finance/reversements/?compagnie=&du=&au= ; POST : reverser des primes encaissées.
    POST { IdCompagnie, DateReversement, Lignes: [{ IdDetailEncaissement, Montant }] }"""
    if request.method == "GET":
        conditions, params = [], []
        if request.query_params.get("compagnie"):
            conditions.append("r.idcompagnie = %s")
            params.append(int(request.query_params["compagnie"]))
        try:
            for cle, operateur in (("du", ">="), ("au", "<=")):
                if request.query_params.get(cle):
                    conditions.append(f"r.datereversement {operateur} %s")
                    params.append(_date(request.query_params[cle], cle))
        except ErreurFinance as erreur:
            return _erreur(erreur)
        sql = SQL_REVERSEMENTS + "".join(f" AND {c}" for c in conditions) + " ORDER BY r.datereversement DESC, r.idreversement DESC"
        return Response({"Reversements": [_entete_reversement(l) for l in _lignes(sql, params)]})

    try:
        donnees = request.data
        id_compagnie = _entier(donnees.get("IdCompagnie"), "Compagnie")
        date_reversement = _date(donnees.get("DateReversement") or date.today(), "Date du reversement")
        lignes = donnees.get("Lignes") or []
        if not lignes:
            raise ErreurFinance("Cochez au moins une prime encaissée à reverser.")
        ids = [_entier(l.get("IdDetailEncaissement"), "Ligne d'encaissement") for l in lignes]
        montants = [_montant(l.get("Montant"), "Montant à reverser") for l in lignes]
        if len(set(ids)) != len(ids):
            raise ErreurFinance("Une même ligne d'encaissement est cochée deux fois.")
        # Les lignes doivent être des primes de cette compagnie, encaissées et non annulées
        controle = _lignes(
            SQL_LIGNES_ENCAISSEMENT + " WHERE de.iddetailencaissement = ANY(%s)", [ids]
        )
        par_id = {l["iddetailencaissement"]: l for l in controle}
        restes = _restes_nets({l["numeroquittance"] for l in controle})
        for id_ligne, montant in zip(ids, montants):
            ligne = par_id.get(id_ligne)
            if not ligne:
                raise ErreurFinance(f"Ligne d'encaissement {id_ligne} introuvable.")
            if ligne["idcompagnie"] != id_compagnie:
                raise ErreurFinance(f"La quittance {ligne['numeroquittance']} n'est pas une affaire de cette compagnie.")
            if ligne["annulee"]:
                raise ErreurFinance(f"L'encaissement de la quittance {ligne['numeroquittance']} est annulé.")
            if _est_decaissement(ligne):
                raise ErreurFinance(f"La quittance {ligne['numeroquittance']} : un décaissement ne se reverse pas.")
            # Reste net : décaissements de la quittance déduits
            reste = restes.get(id_ligne, ZERO)
            if montant > reste:
                raise ErreurFinance(
                    f"Quittance {ligne['numeroquittance']} : {f'{montant:,.0f}'.replace(',', ' ')} F dépasse le reste à reverser "
                    f"({f'{reste:,.0f}'.replace(',', ' ')} F, décaissements déduits)."
                )
        total = sum(montants)
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "CALL sp_enregistrement_reversement(%s, %s, %s::integer[], %s::numeric[], NULL, %s, 1, %s, '', '', '', '', 0, '')",
                [request.user.id, id_compagnie, ids, montants, date_reversement, total],
            )
            id_reversement, message = cursor.fetchone()
            if not id_reversement:
                raise ErreurFinance(message or "Le reversement n'a pas été enregistré.")
    except ErreurFinance as erreur:
        return _erreur(erreur)
    except Exception as erreur:  # message de la procédure (RAISE EXCEPTION)
        return _erreur(erreur)
    return Response(_lire_reversement(id_reversement), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def reversement(request, id_reversement):
    """GET /api/finance/reversements/<id>/ : en-tête et lignes du bordereau de reversement."""
    resultat = _lire_reversement(id_reversement)
    if not resultat:
        return Response({"error": "Reversement introuvable."}, status=status.HTTP_404_NOT_FOUND)
    return Response(resultat)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EcrituresAdministrateur])
def valider_reversement(request, id_reversement):
    """POST /api/finance/reversements/<id>/valider/ : paiement du reversement à la compagnie.
    { IdMode, IdBanque, NumeroCheque, NomEmetteur, ReferenceCompensation, DateReversement }"""
    try:
        donnees = request.data
        id_mode = _entier(donnees.get("IdMode"), "Mode de paiement")
        date_reversement = _date(donnees.get("DateReversement") or date.today(), "Date du paiement")
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "CALL sp_validation_reversement(%s, %s, %s, %s, %s, %s, %s, '', %s, '')",
                [
                    request.user.id, id_reversement, id_mode, date_reversement,
                    _entier(donnees.get("IdBanque"), "Banque", obligatoire=False) or 1,
                    str(donnees.get("NumeroCheque") or "").strip()[:50],
                    str(donnees.get("NomEmetteur") or "").strip()[:50],
                    str(donnees.get("ReferenceCompensation") or "").strip()[:50],
                ],
            )
    except ErreurFinance as erreur:
        return _erreur(erreur)
    except Exception as erreur:
        return _erreur(erreur)
    return Response(_lire_reversement(id_reversement))


# ------------------------------------------------------------------ commissions
# Lignes de reversements PAYÉS à la compagnie : commission due, réclamée, payée, reste
SQL_COMMISSIONS = """
    SELECT d.iddetailreversement, r.idreversement, r.numeroreversement, r.datereversement, r.idcompagnie,
           cie.raisonsociale AS compagnie, d.montantreverse, q.idquittance, q.numeroquittance, q.numeropolice,
           q.primenette, q.primettc, q.dateeffet::date AS dateeffet, p.libelleproduit AS branche,
           TRIM(cl.nom || ' ' || COALESCE(cl.prenoms, '')) AS client, ct.numeroavenant,
           CASE WHEN q.primettc > 0 THEN ROUND(COALESCE(ct.commissionintermediaire, 0) * d.montantreverse / q.primettc, 0) ELSE 0 END AS commissiondue,
           rc.id AS idreclamation, rc.reference AS reclamation,
           COALESCE((SELECT SUM(dp.montant_commission_paye) FROM std_detail_paiement_commission dp
                     WHERE dp.detail_reversement_id = d.iddetailreversement AND NOT dp.est_annule), 0) AS commissionpayee
    FROM stddetailreversement d
    JOIN stdreversementcompagnie r ON r.idreversement = d.idreversement
    JOIN stddetailencaissement de ON de.iddetailencaissement = d.iddetailencaissement
    JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
    LEFT JOIN LATERAL (SELECT c.numeroavenant, c.commissionintermediaire FROM stdcontrat c
                       WHERE c.idquittance = q.idquittance ORDER BY c.idcontrat LIMIT 1) ct ON TRUE
    LEFT JOIN stdcompagnie cie ON cie.idcompagnie = r.idcompagnie
    LEFT JOIN stdproduit p ON p.idproduit = q.idproduit
    LEFT JOIN stdclient cl ON cl.idclient = q.idclient
    LEFT JOIN LATERAL (SELECT x.id, x.reference FROM std_detail_reclamation_commission dx
                       JOIN std_reclamation_commission x ON x.id = dx.reclamation_id
                       WHERE dx.detail_reversement_id = d.iddetailreversement AND x.statut <> 'ANNULEE'
                       ORDER BY x.id DESC LIMIT 1) rc ON TRUE
    WHERE r.valide AND NOT COALESCE(r.pieceannulee, FALSE)
"""

LIBELLES_COMMISSION = {
    "A_RECLAMER": "À réclamer",
    "RECLAMEE": "Réclamée, non payée",
    "PARTIELLE": "Partiellement payée",
    "PAYEE": "Payée",
}


def _ligne_commission(l):
    due, payee = _franc(l["commissiondue"]), _franc(l["commissionpayee"])
    if due > 0 and payee >= due:
        statut = "PAYEE"
    elif payee > 0:
        statut = "PARTIELLE"
    elif l["idreclamation"]:
        statut = "RECLAMEE"
    else:
        statut = "A_RECLAMER"
    return {
        "IdDetailReversement": l["iddetailreversement"],
        "IdReversement": l["idreversement"],
        "NumeroReversement": (l["numeroreversement"] or "").strip(),
        "DateReversement": _iso(l["datereversement"]),
        "IdCompagnie": l["idcompagnie"],
        "Compagnie": l["compagnie"] or "",
        "IdQuittance": l["idquittance"],
        "NumeroQuittance": l["numeroquittance"],
        "NumeroPolice": l["numeropolice"] or "",
        "NumeroAvenant": (l["numeroavenant"] or "").strip(),
        "Branche": l["branche"] or "",
        "Client": l["client"] or "",
        "DateEffet": _iso(l["dateeffet"]),
        "PrimeNette": _nombre(l["primenette"]),
        "PrimeTtc": _nombre(l["primettc"]),
        "MontantReverse": _nombre(l["montantreverse"]),
        "CommissionDue": _nombre(due),
        "CommissionPayee": _nombre(payee),
        "Reste": _nombre(max(due - payee, ZERO)),
        "IdReclamation": l["idreclamation"],
        "Reclamation": l["reclamation"] or "",
        "Statut": statut,
        "LibelleStatut": LIBELLES_COMMISSION[statut],
    }


def _commissions(id_compagnie=None, du=None, au=None, ids=None, id_reclamation=None):
    conditions, params = [], []
    if id_compagnie:
        conditions.append("r.idcompagnie = %s")
        params.append(id_compagnie)
    if du:
        conditions.append("r.datereversement >= %s")
        params.append(du)
    if au:
        conditions.append("r.datereversement <= %s")
        params.append(au)
    if ids is not None:
        conditions.append("d.iddetailreversement = ANY(%s)")
        params.append(list(ids))
    if id_reclamation:
        conditions.append("d.iddetailreversement IN (SELECT detail_reversement_id FROM std_detail_reclamation_commission WHERE reclamation_id = %s)")
        params.append(id_reclamation)
    sql = SQL_COMMISSIONS + "".join(f" AND {c}" for c in conditions) + " ORDER BY r.datereversement, d.iddetailreversement"
    return [_ligne_commission(l) for l in _lignes(sql, params)]


def _totaux_commissions(lignes):
    return {
        "Nombre": len(lignes),
        "PrimesReversees": sum(l["MontantReverse"] for l in lignes),
        "CommissionDue": sum(l["CommissionDue"] for l in lignes),
        "CommissionPayee": sum(l["CommissionPayee"] for l in lignes),
        "Reste": sum(l["Reste"] for l in lignes),
    }


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def etat_commissions(request):
    """GET /api/finance/commissions/?compagnie=&du=&au=&statut= : quittances reversées et leur commission.
    statut : A_RECLAMER, RECLAMEE, PARTIELLE, PAYEE ou PAYEES / NON_PAYEES (regroupements)."""
    try:
        du = _date(request.query_params.get("du"), "Du", obligatoire=False)
        au = _date(request.query_params.get("au"), "Au", obligatoire=False)
    except ErreurFinance as erreur:
        return _erreur(erreur)
    id_compagnie = int(request.query_params.get("compagnie") or 0) or None
    lignes = _commissions(id_compagnie, du, au)
    statut = request.query_params.get("statut")
    if statut == "PAYEES":
        lignes = [l for l in lignes if l["CommissionPayee"] > 0]
    elif statut == "NON_PAYEES":
        lignes = [l for l in lignes if l["Reste"] > 0]
    elif statut:
        lignes = [l for l in lignes if l["Statut"] == statut]
    par_compagnie = {}
    for l in lignes:
        groupe = par_compagnie.setdefault(l["Compagnie"], [])
        groupe.append(l)
    return Response({
        "Lignes": lignes,
        "Total": _totaux_commissions(lignes),
        "ParCompagnie": [{"Compagnie": c, **_totaux_commissions(ls)} for c, ls in sorted(par_compagnie.items())],
    })


def _reclamation_json(reclamation, avec_lignes=False):
    from commissions.models import PaiementCommission

    paiements = PaiementCommission.objects.filter(reclamation=reclamation).select_related("banque").order_by("date_paiement", "id")
    total_paye = paiements.aggregate(t=Sum("montant_total"))["t"] or ZERO
    resultat = {
        "IdReclamation": reclamation.id,
        "Reference": reclamation.reference,
        "IdCompagnie": reclamation.compagnie_id,
        "Compagnie": reclamation.compagnie.RaisonSociale,
        "PeriodeDebut": _iso(reclamation.periode_debut),
        "PeriodeFin": _iso(reclamation.periode_fin),
        "DateEmission": _iso(reclamation.date_emission),
        "MontantPrimes": _nombre(reclamation.montant_primes),
        "MontantCommissions": _nombre(reclamation.montant_commissions),
        "MontantPaye": _nombre(total_paye),
        "Reste": _nombre(max(reclamation.montant_commissions - total_paye, ZERO)),
        "Statut": reclamation.statut,
        "LibelleStatut": dict(reclamation.STATUTS).get(reclamation.statut, reclamation.statut),
        "NombreQuittances": reclamation.details.count(),
        "Notes": reclamation.notes,
        "Paiements": [
            {
                "IdPaiement": p.id, "Reference": p.reference, "DatePaiement": _iso(p.date_paiement),
                "Mode": p.get_mode_paiement_display(), "ReferencePaiement": p.reference_paiement,
                "Banque": p.banque.libelle if p.banque else "", "Montant": _nombre(p.montant_total),
            }
            for p in paiements
        ],
    }
    if avec_lignes:
        resultat["Lignes"] = _commissions(id_reclamation=reclamation.id)
    return resultat


def _prochaine_reference(prefixe, modele, champ="reference"):
    annee = date.today().year
    debut = f"{prefixe}-{annee}-"
    derniere = modele.objects.filter(**{f"{champ}__startswith": debut}).order_by(f"-{champ}").values_list(champ, flat=True).first()
    rang = int(derniere.rsplit("-", 1)[1]) + 1 if derniere else 1
    return f"{debut}{rang:04d}"


@api_view(["GET", "POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EcrituresAdministrateur])
def reclamations(request):
    """GET /api/finance/commissions/reclamations/?compagnie= ; POST : bordereau récapitulatif de
    reversement (réclamation des commissions) { IdCompagnie, PeriodeDebut, PeriodeFin,
    DetailsReversement: [id], Notes }"""
    from commissions.models import DetailReclamationCommission, ReclamationCommission
    from configuration_api.models import Compagnie

    if request.method == "GET":
        requete = ReclamationCommission.objects.select_related("compagnie").order_by("-date_emission", "-id")
        if request.query_params.get("compagnie"):
            requete = requete.filter(compagnie_id=int(request.query_params["compagnie"]))
        return Response({"Reclamations": [_reclamation_json(r) for r in requete]})

    try:
        donnees = request.data
        id_compagnie = _entier(donnees.get("IdCompagnie"), "Compagnie")
        compagnie = Compagnie.objects.filter(pk=id_compagnie).first()
        if not compagnie:
            raise ErreurFinance("Compagnie inconnue.")
        debut = _date(donnees.get("PeriodeDebut"), "Début de période")
        fin = _date(donnees.get("PeriodeFin"), "Fin de période")
        if debut > fin:
            raise ErreurFinance("Le début de la période dépasse sa fin.")
        ids = sorted({_entier(i, "Ligne de reversement") for i in (donnees.get("DetailsReversement") or [])})
        if not ids:
            raise ErreurFinance("Cochez au moins une quittance reversée.")
        lignes = _commissions(ids=ids)
        if len(lignes) != len(ids):
            raise ErreurFinance("Certaines quittances ne sont pas dans un reversement payé à la compagnie.")
        for l in lignes:
            if l["IdCompagnie"] != id_compagnie:
                raise ErreurFinance(f"La quittance {l['NumeroQuittance']} a été reversée à une autre compagnie.")
            if l["IdReclamation"]:
                raise ErreurFinance(f"La quittance {l['NumeroQuittance']} est déjà réclamée ({l['Reclamation']}).")
            if l["CommissionDue"] <= 0:
                raise ErreurFinance(f"La quittance {l['NumeroQuittance']} n'a pas de commission.")
        with transaction.atomic():
            reclamation = ReclamationCommission.objects.create(
                reference=_prochaine_reference("RC", ReclamationCommission),
                compagnie=compagnie, periode_debut=debut, periode_fin=fin,
                montant_primes=sum(Decimal(str(l["MontantReverse"])) for l in lignes),
                montant_commissions=sum(Decimal(str(l["CommissionDue"])) for l in lignes),
                notes=str(donnees.get("Notes") or "")[:2000], created_by=request.user,
            )
            DetailReclamationCommission.objects.bulk_create([
                DetailReclamationCommission(
                    reclamation=reclamation, detail_reversement_id=l["IdDetailReversement"], quittance_id=l["IdQuittance"],
                    montant_prime_reversee=Decimal(str(l["MontantReverse"])), montant_commission=Decimal(str(l["CommissionDue"])),
                )
                for l in lignes
            ])
    except ErreurFinance as erreur:
        return _erreur(erreur)
    return Response(_reclamation_json(reclamation, avec_lignes=True), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def reclamation(request, id_reclamation):
    """GET /api/finance/commissions/reclamations/<id>/ : bordereau, lignes et règlements reçus."""
    from commissions.models import ReclamationCommission

    objet = ReclamationCommission.objects.select_related("compagnie").filter(pk=id_reclamation).first()
    if not objet:
        return Response({"error": "Bordereau de réclamation introuvable."}, status=status.HTTP_404_NOT_FOUND)
    return Response(_reclamation_json(objet, avec_lignes=True))


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EcrituresAdministrateur])
def annuler_reclamation(request, id_reclamation):
    """POST /api/finance/commissions/reclamations/<id>/annuler/ : bordereau émis par erreur, sans règlement."""
    from commissions.models import ReclamationCommission

    objet = ReclamationCommission.objects.filter(pk=id_reclamation).first()
    if not objet:
        return Response({"error": "Bordereau de réclamation introuvable."}, status=status.HTTP_404_NOT_FOUND)
    if objet.paiements.exists():
        return _erreur("Ce bordereau a déjà reçu un règlement de commission : il ne peut plus être annulé.")
    objet.statut = "ANNULEE"
    objet.notes = (objet.notes + "\n" if objet.notes else "") + f"Annulé le {date.today():%d/%m/%Y} : {str(request.data.get('Motif') or '').strip()}"
    objet.save(update_fields=["statut", "notes"])
    return Response(_reclamation_json(objet))


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EcrituresAdministrateur])
def encaisser_commission(request, id_reclamation):
    """POST /api/finance/commissions/reclamations/<id>/paiements/ : règlement de l'assureur.
    { DatePaiement, Mode: CHQ|VIR, IdBanque, ReferencePaiement, Montant, Notes } ; le montant est
    imputé sur les lignes du bordereau, dans l'ordre, jusqu'à leur commission restante."""
    from commissions.models import DetailPaiementCommission, PaiementCommission, ReclamationCommission
    from configuration_api.models import Banque
    from production.models import DetailReversement, Quittance

    try:
        objet = ReclamationCommission.objects.select_related("compagnie").filter(pk=id_reclamation).first()
        if not objet:
            raise ErreurFinance("Bordereau de réclamation introuvable.")
        if objet.statut == "ANNULEE":
            raise ErreurFinance("Ce bordereau est annulé.")
        donnees = request.data
        mode = str(donnees.get("Mode") or "").upper()
        if mode not in ("CHQ", "VIR"):
            raise ErreurFinance("Mode de règlement : chèque ou virement.")
        reference_paiement = str(donnees.get("ReferencePaiement") or "").strip()[:50]
        if not reference_paiement:
            raise ErreurFinance("Référence du règlement (n° de chèque ou de virement) : à renseigner.")
        id_banque = _entier(donnees.get("IdBanque"), "Banque", obligatoire=False)
        banque = Banque.objects.filter(pk=id_banque).first() if id_banque else None
        montant = _montant(donnees.get("Montant"), "Montant du règlement")
        date_paiement = _date(donnees.get("DatePaiement") or date.today(), "Date du règlement")
        lignes = [l for l in _commissions(id_reclamation=objet.id) if l["Reste"] > 0]
        reste_total = sum(Decimal(str(l["Reste"])) for l in lignes)
        if montant > reste_total:
            raise ErreurFinance(
                f"Le règlement ({montant:,.0f} F) dépasse la commission restant due sur ce bordereau ({reste_total:,.0f} F).".replace(",", " ")
            )
        with transaction.atomic():
            paiement = PaiementCommission.objects.create(
                reference=_prochaine_reference("PC", PaiementCommission),
                compagnie=objet.compagnie, date_paiement=date_paiement, montant_total=montant,
                statut="VALIDE", notes=str(donnees.get("Notes") or "")[:2000], created_by=request.user,
                mode_paiement=mode, reference_paiement=reference_paiement, banque=banque, reclamation=objet,
            )
            a_imputer = montant
            for l in lignes:
                if a_imputer <= 0:
                    break
                part = min(Decimal(str(l["Reste"])), a_imputer)
                DetailPaiementCommission.objects.create(
                    paiement=paiement,
                    quittance=Quittance.objects.get(pk=l["IdQuittance"]),
                    detail_reversement=DetailReversement.objects.get(pk=l["IdDetailReversement"]),
                    montant_prime_reversee=Decimal(str(l["MontantReverse"])),
                    taux_commission=(Decimal(str(l["CommissionDue"])) * 100 / Decimal(str(l["MontantReverse"]))).quantize(Decimal("0.01")) if l["MontantReverse"] else ZERO,
                    montant_commission_du=Decimal(str(l["CommissionDue"])),
                    montant_commission_paye=part,
                    reference_affaire=l["NumeroQuittance"],
                )
                a_imputer -= part
            objet.statut = "PAYEE" if montant >= reste_total else "PARTIELLE"
            objet.save(update_fields=["statut"])
    except ErreurFinance as erreur:
        return _erreur(erreur)
    except ValueError as erreur:  # contrôles de DetailPaiementCommission.save
        return _erreur(erreur)
    return Response(_reclamation_json(objet, avec_lignes=True), status=status.HTTP_201_CREATED)
