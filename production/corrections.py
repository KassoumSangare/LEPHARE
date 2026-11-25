"""
Centre des corrections (Administration > Corrections, demande du 2026-11-25 : « en prévoyant les éventuelles erreurs qu'un
utilisateur peut commettre, repère les erreurs potentielles et prévois un module de correction pour chaque cas dans l'admin »).

- GET corrections/anomalies/ : erreurs de saisie probables trouvées dans les données, chacune avec ce qui permet de la
  corriger. Une détection n'est renvoyée qu'avec le droit de lecture de son domaine ; l'écran propose la correction selon le
  droit qu'elle exige.
- GET corrections/journal/ : corrections faites (journal d'audit), droit audit.view.
- Fiches clients en double (droit clients.merge, motif obligatoire) : GET corrections/clients/doublons/,
  GET corrections/clients/fusion/?garder=&fusionner= (aperçu), POST corrections/clients/fusion/ (customer/fusion.py).
- POST corrections/cheques/<id>/solde/ : solde d'un chèque recalculé d'après les règlements en cours (encaissements.cancel).
- POST corrections/contrats/<id>/realignement/ : quittance et devis remis d'accord avec leur contrat (contrats.admin_update,
  coherence_contrat.py).
"""

import logging
from decimal import Decimal
from urllib.parse import unquote

from django.db import DatabaseError, connection, transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from autorisations.journal import completer_audit
from autorisations.rbac import a_le_droit
from customer.fusion import ErreurFusion, apercu, doublons_probables, fusionner_fiches

from .coherence_contrat import ErreurCoherence, realigner
from .decaissements import MODES_EXCLUS
from .renouvellement import AUTHENTIFICATION, _lignes

logger = logging.getLogger(__name__)

MAX_LIGNES = 100
MOTIF_MINIMUM = 5
# Lignes saisies dans l'application (les pièces reprises de l'ancien logiciel n'ont pas d'auteur)
DEPUIS_URANUS = "e.idutilisateur IS NOT NULL"


class ErreurCorrection(Exception):
    """Correction refusée : message affiché tel quel."""


def _nombre(valeur):
    return float(valeur) if valeur is not None else 0.0


def _francs(valeur):
    return f"{Decimal(valeur or 0):,.0f} F".replace(",", " ")


def _date(valeur):
    return valeur.strftime("%d/%m/%Y") if hasattr(valeur, "strftime") else (valeur or "")


# ------------------------------------------------------------------ détections
def _clients(certains):
    def detecter(_cursor):
        groupes = [g for g in doublons_probables(limite=10_000)["Groupes"] if g["Certain"] == certains]
        lignes = [{
            "Libelle": g["Nom"],
            "Detail": " · ".join(f"n° {f['IdClient']} ({f['Contrats']} contrat{'s' if f['Contrats'] > 1 else ''})" for f in g["Fiches"]),
            "Garder": g["Fiches"][0]["IdClient"], "Fusionner": g["Fiches"][1]["IdClient"],
        } for g in groupes]
        return len(lignes), lignes[:MAX_LIGNES]
    return detecter


def _encaissements_doublons(cursor):
    lignes = _lignes(cursor, f"""
        SELECT TRIM(de.numeroquittance) AS quittance, de.montant_encaissement AS montant, e.dateencaissement::date AS jour,
               ARRAY_AGG(DISTINCT e.idencaissement ORDER BY e.idencaissement) AS pieces,
               STRING_AGG(DISTINCT TRIM(e.numeropiece), ', ') AS numeros,
               MAX(TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, ''))) AS client
        FROM stdencaissement e JOIN stddetailencaissement de ON de.idencaissement = e.idencaissement
        LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
        LEFT JOIN stdquittance q ON q.numeroquittance = de.numeroquittance LEFT JOIN stdclient cl ON cl.idclient = q.idclient
        WHERE NOT COALESCE(e.piece_annulee, FALSE) AND de.montant_encaissement > 0 AND {DEPUIS_URANUS}
          AND COALESCE(UPPER(TRIM(m.abregereglement)), '') NOT IN {MODES_EXCLUS}
        GROUP BY 1, 2, 3 HAVING COUNT(DISTINCT e.idencaissement) > 1 ORDER BY 3 DESC""")
    return len(lignes), [{
        "Libelle": f"Quittance {l['quittance']}{' · ' + l['client'] if l['client'] else ''}",
        "Detail": f"{len(l['pieces'])} pièces de {_francs(l['montant'])} le {_date(l['jour'])} : {l['numeros']}",
        "IdEncaissement": l["pieces"][-1], "Quittance": l["quittance"],
    } for l in lignes[:MAX_LIGNES]]


def _trop_percu(cursor):
    lignes = _lignes(cursor, """
        SELECT TRIM(q.numeroquittance) AS quittance, TRIM(q.numeropolice) AS police, q.primettc, q.mt_encaisse,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client
        FROM stdquittance q LEFT JOIN stdclient cl ON cl.idclient = q.idclient
        WHERE q.primettc > 0 AND COALESCE(q.mt_encaisse, 0) - q.primettc >= 5 ORDER BY q.mt_encaisse - q.primettc DESC""")
    return len(lignes), [{
        "Libelle": f"Quittance {l['quittance']} · {l['client']}",
        "Detail": f"Prime {_francs(l['primettc'])}, encaissé {_francs(l['mt_encaisse'])} : {_francs(l['mt_encaisse'] - l['primettc'])} de trop",
        "Quittance": l["quittance"],
    } for l in lignes[:MAX_LIGNES]]


def _sans_reference(cursor):
    lignes = _lignes(cursor, f"""
        SELECT e.idencaissement, TRIM(e.numeropiece) AS piece, TRIM(m.libellemodepaiement) AS mode, e.montantencaissement AS montant,
               e.dateencaissement::date AS jour, UPPER(TRIM(m.abregereglement)) AS code, COALESCE(TRIM(e.numerocheque), '') AS numero,
               COALESCE(e.idbanque, 1) AS banque,
               (SELECT STRING_AGG(DISTINCT TRIM(de.numeroquittance), ', ') FROM stddetailencaissement de WHERE de.idencaissement = e.idencaissement) AS quittances
        FROM stdencaissement e JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
        WHERE UPPER(TRIM(m.abregereglement)) IN ('CHQ', 'VIR', 'TRT') AND NOT COALESCE(e.piece_annulee, FALSE) AND e.montantencaissement > 0
          AND {DEPUIS_URANUS} AND (COALESCE(TRIM(e.numerocheque), '') = '' OR (UPPER(TRIM(m.abregereglement)) = 'CHQ' AND COALESCE(e.idbanque, 1) <= 1))
        ORDER BY e.dateencaissement DESC""")
    return len(lignes), [{
        "Libelle": f"Pièce {l['piece']} · {l['mode']} de {_francs(l['montant'])} le {_date(l['jour'])}",
        "Detail": ("sans numéro" if not l["numero"] else "") + (" et " if not l["numero"] and l["banque"] <= 1 and l["code"] == "CHQ" else "")
                  + ("sans banque" if l["banque"] <= 1 and l["code"] == "CHQ" else "") + f" · quittance {l['quittances'] or '-'}",
        "IdEncaissement": l["idencaissement"],
    } for l in lignes[:MAX_LIGNES]]


SQL_AFFECTE = """COALESCE((SELECT SUM(op.montantoperation) FROM stdchequeoperation op
                  JOIN stdencaissement e ON e.idencaissement = op.idencaissement AND NOT COALESCE(e.piece_annulee, FALSE)
                  WHERE op.idcheque = ch.idcheque), 0)"""


def _cheques_a_rapprocher(cursor):
    lignes = _lignes(cursor, f"""
        SELECT ch.idcheque, TRIM(ch.numerocheque) AS numero, TRIM(COALESCE(b.libelle, '')) AS banque, ch.montantinitial, ch.soldedisponible,
               {SQL_AFFECTE} AS affecte
        FROM stdcheque ch LEFT JOIN stdbanque b ON b.idbanque = ch.idbanque
        WHERE ch.statut = 'ENCAISSE' AND ABS(ch.montantinitial - ch.soldedisponible - {SQL_AFFECTE}) > 1 ORDER BY ch.idcheque DESC""")
    return len(lignes), [{
        "Libelle": f"Chèque n° {l['numero']} · {l['banque']}",
        "Detail": f"Montant {_francs(l['montantinitial'])}, règlements en cours {_francs(l['affecte'])} : solde attendu "
                  f"{_francs(l['montantinitial'] - l['affecte'])}, enregistré {_francs(l['soldedisponible'])}",
        "IdCheque": l["idcheque"], "Numero": l["numero"],
    } for l in lignes[:MAX_LIGNES]]


def _cheques_doublons(cursor):
    lignes = _lignes(cursor, """
        SELECT REGEXP_REPLACE(UPPER(ch.numerocheque), '[^0-9A-Z]', '', 'g') AS cle, TRIM(COALESCE(b.libelle, '')) AS banque,
               STRING_AGG(TRIM(ch.numerocheque) || ' (' || ch.statut || ')', ', ' ORDER BY ch.idcheque) AS numeros
        FROM stdcheque ch LEFT JOIN stdbanque b ON b.idbanque = ch.idbanque
        GROUP BY 1, 2 HAVING COUNT(*) > 1 ORDER BY 1""")
    return len(lignes), [{"Libelle": f"Chèque {l['cle']} · {l['banque']}", "Detail": f"Enregistré plusieurs fois : {l['numeros']}",
                          "Numero": l["cle"]} for l in lignes[:MAX_LIGNES]]


def _contrats_desaccord(cursor):
    lignes = _lignes(cursor, """
        SELECT ct.idcontrat, TRIM(ct.numeropolice) AS police,
               q.idclient IS DISTINCT FROM ct.idclient OR d.idclient IS DISTINCT FROM ct.idclient AS client,
               q.idaperiteur IS DISTINCT FROM ct.idaperiteur OR d.idcompagnie IS DISTINCT FROM ct.idcompagnie AS compagnie,
               q.numeropolice IS DISTINCT FROM ct.numeropolice AS numero
        FROM stdcontrat ct JOIN stdquittance q ON q.idquittance = ct.idquittance LEFT JOIN stddevis d ON d.iddevis = ct.iddevis
        WHERE ct.idcontratannulation = 0 AND (q.idclient IS DISTINCT FROM ct.idclient OR q.idaperiteur IS DISTINCT FROM ct.idaperiteur
          OR q.numeropolice IS DISTINCT FROM ct.numeropolice OR (d.iddevis IS NOT NULL AND (d.idclient IS DISTINCT FROM ct.idclient
          OR d.idcompagnie IS DISTINCT FROM ct.idcompagnie)))
        ORDER BY ct.idcontrat DESC""")
    return len(lignes), [{
        "Libelle": f"Police {l['police']}",
        "Detail": "Quittance ou devis sur un autre " + ", ".join(x for x, ok in (("souscripteur", l["client"]), ("compagnie", l["compagnie"]),
                                                                              ("n° de police", l["numero"])) if ok),
        "IdContrat": l["idcontrat"],
    } for l in lignes[:MAX_LIGNES]]


def _contrats_periode(cursor):
    lignes = _lignes(cursor, """
        SELECT idcontrat, TRIM(numeropolice) AS police, dateeffet::date AS effet, dateexpiration::date AS echeance
        FROM stdcontrat WHERE idcontratannulation = 0 AND dateexpiration < dateeffet ORDER BY idcontrat DESC""")
    return len(lignes), [{"Libelle": f"Police {l['police']}", "Detail": f"Effet le {_date(l['effet'])}, échéance le {_date(l['echeance'])}",
                          "IdContrat": l["idcontrat"]} for l in lignes[:MAX_LIGNES]]


# Code, domaine, titre, explication courte, droit pour voir, droit pour corriger, détection
DETECTIONS = [
    ("clients_doublons", "Clients", "Fiches clients en double", "Même nom et même téléphone, date de naissance ou pièce d'identité.",
     "clients.view", "clients.merge", _clients(True)),
    ("clients_homonymes", "Clients", "Clients de même nom à vérifier", "Même nom, sans autre point commun : doublon ou homonyme.",
     "clients.view", "clients.merge", _clients(False)),
    ("encaissements_doublons", "Caisse", "Encaissements saisis deux fois", "Même quittance, même montant, même jour, deux pièces.",
     "encaissements.view", "encaissements.cancel", _encaissements_doublons),
    ("quittances_trop_percues", "Caisse", "Quittances encaissées au-delà de la prime", "Le client a payé plus que la prime.",
     "encaissements.view", "encaissements.cancel", _trop_percu),
    ("reglements_sans_reference", "Caisse", "Chèques, virements ou traites sans référence", "Sans numéro, ou chèque sans banque.",
     "encaissements.view", "encaissements.cancel", _sans_reference),
    ("cheques_a_rapprocher", "Chèques", "Chèques au solde faux", "Montant du chèque moins les règlements en cours différent du solde enregistré.",
     "encaissements.view", "encaissements.cancel", _cheques_a_rapprocher),
    ("cheques_doublons", "Chèques", "Même chèque enregistré deux fois", "Même numéro, écrit autrement, à la même banque.",
     "encaissements.view", "encaissements.cancel", _cheques_doublons),
    ("contrats_desaccord", "Contrats", "Contrat, quittance et devis en désaccord", "Souscripteur, compagnie ou n° de police différents.",
     "contrats.view", "contrats.admin_update", _contrats_desaccord),
    ("contrats_periode", "Contrats", "Échéance avant la date d'effet", "Période du contrat impossible.",
     "contrats.view", "contrats.admin_update", _contrats_periode),
]


def anomalies(user):
    resultat = []
    with connection.cursor() as cursor:
        for code, domaine, titre, texte, lecture, correction, detecter in DETECTIONS:
            if not a_le_droit(user, lecture):
                continue
            try:
                nombre, lignes = detecter(cursor)
            except DatabaseError:
                logger.exception("Centre des corrections : détection %s impossible", code)
                nombre, lignes = None, []
            resultat.append({"Code": code, "Domaine": domaine, "Titre": titre, "Texte": texte, "Droit": correction,
                             "Nombre": nombre, "Lignes": lignes})
    return {"Anomalies": resultat}


# ------------------------------------------------------------------ journal des corrections
ACTIONS_CORRECTION = {
    "contrats.admin_update": "Contrat corrigé", "contrats.delete": "Contrat supprimé", "devis.delete": "Devis supprimé",
    "encaissements.cancel": "Encaissement annulé", "encaissements.correction": "Encaissement corrigé",
    "encaissements.cheque.reutilisation": "Chèque annulé réutilisé", "clients.merge": "Fiches clients fusionnées",
    "reversements.cancel": "Bordereau de reversement annulé", "commissions.cancel": "Commission annulée",
    "apporteurs.cancel": "Commission d'apporteur annulée", "archives.restore": "Élément restauré",
    "corrections.cheque_solde": "Solde d'un chèque recalculé", "corrections.contrat_realignement": "Quittance et devis réalignés",
}


def journal(page=1, taille=50):
    from institutionnel.models import AuditLogCima

    base = AuditLogCima.objects.filter(action__in=ACTIONS_CORRECTION.keys(), resultat="SUCCES").select_related("utilisateur").order_by("-date_creation", "-id")
    total = base.count()
    lignes = base[(page - 1) * taille: page * taille]
    return {"Total": total, "Page": page, "Taille": taille, "Lignes": [{
        "Id": l.id, "Date": l.date_creation.isoformat() if l.date_creation else "", "Action": ACTIONS_CORRECTION.get(l.action, l.action),
        "Code": l.action, "Auteur": (getattr(l.utilisateur, "name", "") or "").strip() or l.auteur, "Objet": f"{l.objet_type} {l.objet_id}".strip(),
        "Description": l.description, "Motif": l.motif,
    } for l in lignes]}


# ------------------------------------------------------------------ chèque : solde recalculé
def recalculer_solde_cheque(request, id_cheque, motif):
    from .models import Cheque

    with transaction.atomic(), connection.cursor() as cursor:
        cheque = Cheque.objects.select_for_update().filter(id_cheque=id_cheque).first()
        if not cheque:
            raise ErreurCorrection("Chèque introuvable.")
        if cheque.statut != Cheque.Statut.ENCAISSE:
            raise ErreurCorrection("Seul le solde d'un chèque encaissé se recalcule ; un chèque annulé se réutilise depuis le portefeuille.")
        cursor.execute(f"SELECT {SQL_AFFECTE} FROM stdcheque ch WHERE ch.idcheque = %s", [id_cheque])
        affecte = cursor.fetchone()[0] or Decimal("0")
        attendu = cheque.montant_initial - affecte
        if attendu < 0:
            raise ErreurCorrection(f"Les règlements en cours ({_francs(affecte)}) dépassent le montant du chèque ({_francs(cheque.montant_initial)}) : "
                                   "corrigez d'abord le montant du chèque ou le règlement en trop.")
        if abs(attendu - cheque.solde_disponible) <= 1:
            raise ErreurCorrection("Le solde de ce chèque est déjà juste.")
        avant = cheque.solde_disponible
        cheque.solde_disponible = attendu
        cheque.save(update_fields=["solde_disponible"])
    completer_audit(request, module="corrections", action="corrections.cheque_solde", objet_type="cheque", objet_id=id_cheque, motif=motif,
                    description=f"Solde du chèque n° {cheque.numero_cheque} recalculé : {_francs(avant)} -> {_francs(attendu)}",
                    avant={"SoldeDisponible": str(avant)}, apres={"SoldeDisponible": str(attendu)})
    return {"IdCheque": id_cheque, "Avant": _nombre(avant), "Apres": _nombre(attendu),
            "Message": f"Solde du chèque n° {cheque.numero_cheque} : {_francs(avant)} -> {_francs(attendu)}."}


# ------------------------------------------------------------------ contrat : quittance et devis réalignés
def realigner_contrat(request, id_contrat, motif):
    from .models import Contrat

    with transaction.atomic(), connection.cursor() as cursor:
        contrat = Contrat.objects.select_for_update().filter(pk=id_contrat).first()
        if not contrat:
            raise ErreurCorrection("Contrat introuvable.")
        try:
            propagations = realigner(cursor, contrat)
        except ErreurCoherence as erreur:
            raise ErreurCorrection(str(erreur))
    completer_audit(request, module="corrections", action="corrections.contrat_realignement", objet_type="contrat", objet_id=id_contrat, motif=motif,
                    description=f"Police {contrat.numeropolice} : quittance et devis remis d'accord avec le contrat",
                    apres={"Propagations": propagations})
    return {"IdContrat": id_contrat, "Propagations": propagations,
            "Message": f"Police {contrat.numeropolice} : quittance et devis remis d'accord avec le contrat."}


# ------------------------------------------------------------------ vues
def _motif(request):
    motif = request.data.get("motif") if hasattr(request, "data") else ""
    motif = " ".join(str(motif or unquote(request.headers.get("X-Motif", "") or "")).split())
    if len(motif) < MOTIF_MINIMUM:
        raise ErreurCorrection(f"Indiquez le motif de la correction ({MOTIF_MINIMUM} caractères au moins).")
    return motif


def _reponse(fonction, *args):
    try:
        return Response(fonction(*args), status=status.HTTP_200_OK)
    except (ErreurCorrection, ErreurFusion) as erreur:
        return Response({"erreur": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
    except DatabaseError as erreur:
        logger.exception("Centre des corrections : erreur de base")
        return Response({"erreur": str(erreur).split("\n")[0]}, status=status.HTTP_400_BAD_REQUEST)


def _refus(droit, libelle):
    return Response({"erreur": f"Accès refusé : droit « {libelle} » requis ({droit})."}, status=status.HTTP_403_FORBIDDEN)


def _entier(valeur):
    try:
        return int(str(valeur or "").strip())
    except ValueError:
        raise ErreurCorrection("Numéro de fiche illisible.")


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_anomalies(request):
    return _reponse(anomalies, request.user)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_journal(request):
    if not a_le_droit(request.user, "audit.view"):
        return _refus("audit.view", "Consulter le journal d'audit")
    try:
        page = max(1, int(request.query_params.get("page") or 1))
    except ValueError:
        page = 1
    return _reponse(journal, page)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_doublons_clients(request):
    if not a_le_droit(request.user, "clients.merge"):
        return _refus("clients.merge", "Regrouper des clients")
    return _reponse(doublons_probables)


@api_view(["GET", "POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_fusion_clients(request):
    if not a_le_droit(request.user, "clients.merge"):
        return _refus("clients.merge", "Regrouper des clients")
    if request.method == "GET":
        return _reponse(lambda: apercu(_entier(request.query_params.get("garder")), _entier(request.query_params.get("fusionner"))))

    def fusionner():
        garder, fusionner_id = _entier(request.data.get("garder")), _entier(request.data.get("fusionner"))
        motif = _motif(request)
        with transaction.atomic():
            bilan = fusionner_fiches(garder, fusionner_id, motif, request.user)
        completer_audit(request, module="clients", action="clients.merge", objet_type="client", objet_id=garder, motif=motif,
                        description=f"Fiche client n° {fusionner_id} fusionnée dans la fiche n° {garder} ({bilan['Nom']})",
                        apres=bilan)
        return bilan
    return _reponse(fusionner)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_solde_cheque(request, id_cheque):
    if not a_le_droit(request.user, "encaissements.cancel"):
        return _refus("encaissements.cancel", "Annuler un encaissement")
    return _reponse(lambda: recalculer_solde_cheque(request, id_cheque, _motif(request)))


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_realignement_contrat(request, id_contrat):
    if not a_le_droit(request.user, "contrats.admin_update"):
        return _refus("contrats.admin_update", "Modifier toutes les informations d'un contrat")
    return _reponse(lambda: realigner_contrat(request, id_contrat, _motif(request)))
