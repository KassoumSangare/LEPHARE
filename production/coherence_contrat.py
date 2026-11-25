"""
Cohérence d'un contrat corrigé (Administration > Corrections > Corriger un contrat, 2026-11-25).

Un contrat, sa quittance et son devis portent le même souscripteur, la même compagnie et le même n° de police (vérifié en base
locale : aucun écart sur 21 492 quittances et 21 762 devis). L'écran d'administration ne modifiait que la ligne du contrat :
- un souscripteur corrigé laissait la quittance (caisse, relevé de compte) et le reste dû (solde) sur l'ancien client ;
- une compagnie corrigée laissait la quittance (apériteur) et le devis à l'ancienne : reversement et commission à la mauvaise ;
- un n° de police corrigé faisait sortir la quittance de la caisse (elle n'y figure que si sa police est celle du contrat) et
  séparait le mouvement corrigé des autres mouvements de la police.

propager() reporte la correction partout où elle compte, dans la transaction de l'enregistrement (et de la simulation, annulée) :
- souscripteur : quittance, devis, assuré s'il était le souscripteur (sauf assuré corrigé à l'écran), reste dû de la quittance
  transféré d'un solde client à l'autre ; refus si la nouvelle fiche est archivée ;
- compagnie : apériteur s'il était la compagnie, quittance, devis ; refus si une prime de la quittance a été reversée ou sa
  commission réclamée ou payée (annuler d'abord le bordereau ou la réclamation) ;
- n° de police : tous les mouvements de la police, leurs quittances, les polices rattachées (police connexe), commissions
  d'apporteur, voyages et certificats de transport ; refus si le numéro appartient déjà à une autre police.
« Toute la police » : souscripteur et compagnie corrigés aussi sur les autres mouvements de la police qui portaient l'ancien.

realigner() remet quittance et devis d'accord avec leur contrat (anomalie détectée par le centre des corrections).
"""

from decimal import Decimal

from .decaissements import SQL_REVERSE

ZERO = Decimal("0")
LONGUEUR_POLICE = 15
# Autres tables qui portent le n° de police du cabinet (présentes ou non selon les installations)
POLICE_AILLEURS = [
    ("stdcontrat", "numeropoliceconnexe", "Polices rattachées"), ("stddevis", "numeropoliceconnexe", "Devis rattachés"),
    ("lephare_commission_apporteur", "numeropolice", "Commissions d'apporteur"),
    ("lephare_transport_voyage", "numeropolice", "Voyages de transport"), ("stdcertificattransport", "numeropolice", "Certificats de transport"),
]


class ErreurCoherence(Exception):
    """Correction refusée : message affiché tel quel."""


def cles_contrat(contrat):
    """Valeurs qui doivent rester d'accord entre le contrat, sa quittance et son devis (lues avant l'enregistrement)."""
    return {
        "idclient": contrat.idclient_id, "idassure": contrat.idassure, "idcompagnie": contrat.idcompagnie_id,
        "idaperiteur": contrat.idaperiteur, "numeropolice": (contrat.numeropolice or "").strip(),
    }


def _table_existe(cursor, table):
    cursor.execute("SELECT to_regclass(%s)", [table])
    return cursor.fetchone()[0] is not None


def _nom_client(cursor, idclient):
    cursor.execute("SELECT TRIM(COALESCE(nom, '') || ' ' || COALESCE(prenoms, '')) FROM stdclient WHERE idclient = %s", [idclient])
    ligne = cursor.fetchone()
    return (ligne[0] if ligne else "") or f"Client n° {idclient}"


def _nom_compagnie(cursor, idcompagnie):
    cursor.execute("SELECT TRIM(raisonsociale) FROM stdcompagnie WHERE idcompagnie = %s", [idcompagnie])
    ligne = cursor.fetchone()
    return (ligne[0] if ligne else "") or f"Compagnie n° {idcompagnie}"


def _francs(valeur):
    return f"{Decimal(valeur or 0):,.0f} F".replace(",", " ")


def _mouvements(cursor, contrat, police, champ, ancienne, toute_la_police):
    """Le contrat corrigé, et avec « toute la police » les autres mouvements de la police qui portaient l'ancienne valeur."""
    ids = [contrat.pk]
    if toute_la_police and police:
        cursor.execute(f"SELECT idcontrat FROM stdcontrat WHERE numeropolice = %s AND idcontrat <> %s AND {champ} = %s ORDER BY idcontrat",
                       [police, contrat.pk, ancienne])
        ids += [r[0] for r in cursor.fetchall()]
    return ids


def _autres_mouvements(cursor, contrat, police, champ, ancienne):
    if not police:
        return 0
    cursor.execute(f"SELECT COUNT(*) FROM stdcontrat WHERE numeropolice = %s AND idcontrat <> %s AND {champ} = %s", [police, contrat.pk, ancienne])
    return cursor.fetchone()[0]


def _vers_client(cursor, ids, nouveau, ancien, assure_suit, propagations):
    """Quittances, devis (et assuré s'il était le souscripteur) des contrats ids vers le client nouveau ; reste dû des
    quittances déplacé d'un solde client à l'autre."""
    nom_nouveau = _nom_client(cursor, nouveau)
    noms = {}
    cursor.execute("""SELECT q.idquittance, TRIM(q.numeroquittance), q.idclient, COALESCE(q.primettc, 0) - COALESCE(q.mt_encaisse, 0)
                      FROM stdcontrat ct JOIN stdquittance q ON q.idquittance = ct.idquittance
                      WHERE ct.idcontrat = ANY(%s) AND q.idclient IS DISTINCT FROM %s""", [ids, nouveau])
    quittances = cursor.fetchall()
    soldes = {}
    for idq, numero, client_quittance, reste in quittances:
        cursor.execute("UPDATE stdquittance SET idclient = %s WHERE idquittance = %s", [nouveau, idq])
        noms.setdefault(client_quittance, _nom_client(cursor, client_quittance) if client_quittance else "")
        propagations.append({"Element": f"Quittance {numero}", "Champ": "Souscripteur", "Avant": noms[client_quittance], "Apres": nom_nouveau})
        if reste and client_quittance:
            soldes[client_quittance] = soldes.get(client_quittance, ZERO) - reste
            soldes[nouveau] = soldes.get(nouveau, ZERO) + reste
    for idclient, ecart in soldes.items():
        if not ecart:
            continue
        cursor.execute("SELECT COALESCE(solde, 0) FROM stdclient WHERE idclient = %s", [idclient])
        avant = cursor.fetchone()[0]
        cursor.execute("UPDATE stdclient SET solde = COALESCE(solde, 0) + %s WHERE idclient = %s", [ecart, idclient])
        propagations.append({"Element": f"Client {_nom_client(cursor, idclient)}", "Champ": "Solde (reste dû)",
                             "Avant": _francs(avant), "Apres": _francs(avant + ecart)})
    cursor.execute("""SELECT d.iddevis, TRIM(COALESCE(d.numerodevis::text, d.iddevis::text)), d.idclient FROM stdcontrat ct
                      JOIN stddevis d ON d.iddevis = ct.iddevis WHERE ct.idcontrat = ANY(%s) AND d.idclient IS DISTINCT FROM %s""", [ids, nouveau])
    for iddevis, numero, client_devis in cursor.fetchall():
        cursor.execute("UPDATE stddevis SET idclient = %s WHERE iddevis = %s", [nouveau, iddevis])
        if assure_suit:
            cursor.execute("UPDATE stddevis SET idassure = %s WHERE iddevis = %s AND idassure = %s", [nouveau, iddevis, ancien])
        noms.setdefault(client_devis, _nom_client(cursor, client_devis) if client_devis else "")
        propagations.append({"Element": f"Devis {numero}", "Champ": "Souscripteur", "Avant": noms[client_devis], "Apres": nom_nouveau})
    if assure_suit and ancien:
        cursor.execute("UPDATE stdcontrat SET idassure = %s WHERE idcontrat = ANY(%s) AND idassure = %s RETURNING idcontrat", [nouveau, ids, ancien])
        if cursor.fetchall():
            propagations.append({"Element": "Contrat", "Champ": "Assuré (il était le souscripteur)", "Avant": _nom_client(cursor, ancien), "Apres": nom_nouveau})


def _refus_compagnie(cursor, ids):
    """Quittances dont une prime est déjà reversée à la compagnie ou la commission réclamée ou payée."""
    cursor.execute(f"""
        SELECT DISTINCT TRIM(q.numeroquittance) FROM stdcontrat ct JOIN stdquittance q ON q.idquittance = ct.idquittance
        WHERE ct.idcontrat = ANY(%s) AND (
            EXISTS (SELECT 1 FROM stddetailencaissement de JOIN stdencaissement e ON e.idencaissement = de.idencaissement
                    WHERE de.numeroquittance = q.numeroquittance AND NOT COALESCE(e.piece_annulee, FALSE) AND {SQL_REVERSE})
            OR EXISTS (SELECT 1 FROM std_detail_reclamation_commission r WHERE r.quittance_id = q.idquittance)
            OR EXISTS (SELECT 1 FROM std_detail_paiement_commission p WHERE p.quittance_id = q.idquittance))""", [ids])
    return [r[0] for r in cursor.fetchall()]


def _vers_compagnie(cursor, ids, nouvelle, propagations):
    nom = _nom_compagnie(cursor, nouvelle)
    cursor.execute("""SELECT q.idquittance, TRIM(q.numeroquittance), q.idaperiteur FROM stdcontrat ct JOIN stdquittance q ON q.idquittance = ct.idquittance
                      WHERE ct.idcontrat = ANY(%s) AND q.idaperiteur IS DISTINCT FROM ct.idaperiteur""", [ids])
    for idq, numero, ancienne in cursor.fetchall():
        cursor.execute("UPDATE stdquittance q SET idaperiteur = ct.idaperiteur FROM stdcontrat ct WHERE q.idquittance = %s AND ct.idquittance = q.idquittance",
                       [idq])
        propagations.append({"Element": f"Quittance {numero}", "Champ": "Compagnie",
                             "Avant": _nom_compagnie(cursor, ancienne) if ancienne else "", "Apres": nom})
    cursor.execute("""SELECT d.iddevis, TRIM(COALESCE(d.numerodevis::text, d.iddevis::text)), d.idcompagnie, d.idcompagnie IS DISTINCT FROM ct.idcompagnie
                      FROM stdcontrat ct JOIN stddevis d ON d.iddevis = ct.iddevis
                      WHERE ct.idcontrat = ANY(%s) AND (d.idcompagnie IS DISTINCT FROM ct.idcompagnie OR d.idaperiteur IS DISTINCT FROM ct.idaperiteur)""", [ids])
    for iddevis, numero, ancienne, compagnie_changee in cursor.fetchall():
        cursor.execute("""UPDATE stddevis d SET idcompagnie = ct.idcompagnie, idaperiteur = ct.idaperiteur FROM stdcontrat ct
                          WHERE d.iddevis = %s AND ct.iddevis = d.iddevis""", [iddevis])
        if compagnie_changee:
            propagations.append({"Element": f"Devis {numero}", "Champ": "Compagnie", "Avant": _nom_compagnie(cursor, ancienne) if ancienne else "", "Apres": nom})


def _vers_police(cursor, ancienne, nouvelle, propagations):
    cursor.execute("UPDATE stdcontrat SET numeropolice = %s WHERE numeropolice = %s RETURNING idcontrat", [nouvelle, ancienne])
    mouvements = len(cursor.fetchall())
    cursor.execute("UPDATE stdquittance SET numeropolice = %s WHERE numeropolice = %s RETURNING idquittance", [nouvelle, ancienne])
    quittances = len(cursor.fetchall())
    if mouvements:
        propagations.append({"Element": f"{mouvements} autre{'s' if mouvements > 1 else ''} mouvement{'s' if mouvements > 1 else ''} de la police",
                             "Champ": "N° de police", "Avant": ancienne, "Apres": nouvelle})
    if quittances:
        propagations.append({"Element": f"{quittances} quittance{'s' if quittances > 1 else ''}", "Champ": "N° de police", "Avant": ancienne, "Apres": nouvelle})
    for table, colonne, libelle in POLICE_AILLEURS:
        if not _table_existe(cursor, table):
            continue
        cursor.execute(f'UPDATE {table} SET "{colonne}" = %s WHERE "{colonne}" = %s', [nouvelle, ancienne])
        if cursor.rowcount:
            propagations.append({"Element": f"{libelle} ({cursor.rowcount})", "Champ": "N° de police", "Avant": ancienne, "Apres": nouvelle})


def propager(cursor, contrat, avant, toute_la_police=False, saisis=()):
    """Correction du contrat (déjà écrite) reportée sur sa quittance, son devis, les soldes clients et, selon le cas, les autres
    mouvements de la police. saisis : champs du contrat corrigés à l'écran (un assuré ou un apériteur saisi n'est pas remplacé).
    Renvoie {"propagations": [...], "avertissements": [...]} ; refus : ErreurCoherence."""
    apres = cles_contrat(contrat)
    propagations, avertissements = [], []
    police = apres["numeropolice"]

    # 1. N° de police : toute la police, dans toutes les tables qui le portent
    if police != avant["numeropolice"]:
        if not police:
            raise ErreurCoherence("Le numéro de police ne peut pas être vide.")
        # Certificats de transport : 15 caractères (les n° de police du cabinet en ont 14 au plus)
        if len(police) > LONGUEUR_POLICE:
            raise ErreurCoherence(f"Le n° de police tient en {LONGUEUR_POLICE} caractères au plus.")
        cursor.execute("SELECT 1 FROM stdcontrat WHERE numeropolice = %s AND idcontrat <> %s LIMIT 1", [police, contrat.pk])
        if cursor.fetchone():
            raise ErreurCoherence(f"Le n° de police {police} appartient déjà à une autre police : choisissez un autre numéro.")
        if avant["numeropolice"]:
            _vers_police(cursor, avant["numeropolice"], police, propagations)

    # 2. Souscripteur
    if apres["idclient"] != avant["idclient"]:
        cursor.execute("SELECT COALESCE(statut, '') FROM stdclient WHERE idclient = %s", [apres["idclient"]])
        statut = cursor.fetchone()
        if not statut:
            raise ErreurCoherence(f"Aucun client ne porte le n° {apres['idclient']}.")
        if statut[0].strip() == "A":
            raise ErreurCoherence(f"La fiche du client n° {apres['idclient']} est archivée : restaurez-la d'abord ou choisissez sa fiche de référence.")
        ids = _mouvements(cursor, contrat, police, "idclient", avant["idclient"], toute_la_police)
        if len(ids) > 1:
            cursor.execute("UPDATE stdcontrat SET idclient = %s WHERE idcontrat = ANY(%s)", [apres["idclient"], ids[1:]])
            propagations.append({"Element": f"{len(ids) - 1} autre{'s' if len(ids) > 2 else ''} mouvement{'s' if len(ids) > 2 else ''} de la police",
                                 "Champ": "Souscripteur", "Avant": _nom_client(cursor, avant["idclient"]), "Apres": _nom_client(cursor, apres["idclient"])})
        _vers_client(cursor, ids, apres["idclient"], avant["idclient"], "idassure" not in saisis, propagations)
        restants = 0 if toute_la_police else _autres_mouvements(cursor, contrat, police, "idclient", avant["idclient"])
        if restants:
            avertissements.append(f"{restants} autre{'s' if restants > 1 else ''} mouvement{'s' if restants > 1 else ''} de la police "
                                  f"rest{'ent' if restants > 1 else 'e'} au nom de {_nom_client(cursor, avant['idclient'])}.")

    # 3. Compagnie
    if apres["idcompagnie"] != avant["idcompagnie"]:
        ids = _mouvements(cursor, contrat, police, "idcompagnie", avant["idcompagnie"], toute_la_police)
        bloquees = _refus_compagnie(cursor, ids)
        if bloquees:
            raise ErreurCoherence(
                f"Quittance{'s' if len(bloquees) > 1 else ''} {', '.join(bloquees)} : prime déjà reversée à "
                f"{_nom_compagnie(cursor, avant['idcompagnie'])} ou commission réclamée. Annulez d'abord le bordereau ou la réclamation, "
                "puis corrigez la compagnie.")
        if len(ids) > 1:
            cursor.execute("UPDATE stdcontrat SET idcompagnie = %s WHERE idcontrat = ANY(%s)", [apres["idcompagnie"], ids[1:]])
            propagations.append({"Element": f"{len(ids) - 1} autre{'s' if len(ids) > 2 else ''} mouvement{'s' if len(ids) > 2 else ''} de la police",
                                 "Champ": "Compagnie", "Avant": _nom_compagnie(cursor, avant["idcompagnie"]), "Apres": _nom_compagnie(cursor, apres["idcompagnie"])})
        # L'apériteur était la compagnie (cas de tout contrat sans coassurance) : il la suit, sauf s'il est corrigé à l'écran
        if "idaperiteur" not in saisis:
            cursor.execute("UPDATE stdcontrat SET idaperiteur = %s WHERE idcontrat = ANY(%s) AND idaperiteur = %s RETURNING idcontrat",
                           [apres["idcompagnie"], ids, avant["idcompagnie"]])
            if cursor.fetchall():
                propagations.append({"Element": "Contrat", "Champ": "Apériteur", "Avant": _nom_compagnie(cursor, avant["idcompagnie"]),
                                     "Apres": _nom_compagnie(cursor, apres["idcompagnie"])})
        _vers_compagnie(cursor, ids, apres["idcompagnie"], propagations)
        avertissements.append("Compagnie corrigée : vérifiez le taux de commission et les accessoires, réglés compagnie par compagnie.")
        restants = 0 if toute_la_police else _autres_mouvements(cursor, contrat, police, "idcompagnie", avant["idcompagnie"])
        if restants:
            avertissements.append(f"{restants} autre{'s' if restants > 1 else ''} mouvement{'s' if restants > 1 else ''} de la police "
                                  f"rest{'ent' if restants > 1 else 'e'} chez {_nom_compagnie(cursor, avant['idcompagnie'])}.")
    elif apres["idaperiteur"] != avant["idaperiteur"]:
        # Apériteur seul corrigé : quittance et devis le suivent (en base, l'apériteur de la quittance est toujours celui du contrat)
        _vers_compagnie(cursor, [contrat.pk], apres["idaperiteur"], propagations)
    return {"propagations": propagations, "avertissements": avertissements}


def ecarts(cursor, id_contrat):
    """Ce qui diffère entre le contrat, sa quittance et son devis (souscripteur, compagnie, n° de police)."""
    cursor.execute("""
        SELECT ct.idclient, q.idclient, d.idclient, ct.idcompagnie, ct.idaperiteur, q.idaperiteur, d.idcompagnie,
               TRIM(ct.numeropolice), TRIM(q.numeropolice), q.idquittance
        FROM stdcontrat ct LEFT JOIN stdquittance q ON q.idquittance = ct.idquittance LEFT JOIN stddevis d ON d.iddevis = ct.iddevis
        WHERE ct.idcontrat = %s""", [id_contrat])
    ligne = cursor.fetchone()
    if not ligne:
        raise ErreurCoherence("Contrat introuvable.")
    (client, client_q, client_d, compagnie, aperiteur, aperiteur_q, compagnie_d, police, police_q, idq) = ligne
    return {
        "client": (idq and client_q != client) or (client_d is not None and client_d != client),
        "compagnie": (idq and aperiteur_q != aperiteur) or (compagnie_d is not None and compagnie_d != compagnie),
        "police": bool(idq) and police_q != police,
        "quittance": idq,
    }


def realigner(cursor, contrat):
    """Quittance et devis remis d'accord avec leur contrat : souscripteur (et reste dû entre soldes), compagnie, n° de police."""
    propagations = []
    e = ecarts(cursor, contrat.pk)
    if not (e["client"] or e["compagnie"] or e["police"]):
        raise ErreurCoherence("Ce contrat, sa quittance et son devis sont déjà d'accord.")
    if e["compagnie"]:
        bloquees = _refus_compagnie(cursor, [contrat.pk])
        if bloquees:
            raise ErreurCoherence(f"Quittance {', '.join(bloquees)} : prime déjà reversée ou commission réclamée. Annulez d'abord le "
                                  "bordereau ou la réclamation.")
    if e["client"]:
        _vers_client(cursor, [contrat.pk], contrat.idclient_id, None, False, propagations)
    if e["compagnie"]:
        _vers_compagnie(cursor, [contrat.pk], contrat.idcompagnie_id, propagations)
    if e["police"]:
        cursor.execute("SELECT TRIM(numeropolice) FROM stdquittance WHERE idquittance = %s", [e["quittance"]])
        ancienne = cursor.fetchone()[0]
        cursor.execute("UPDATE stdquittance SET numeropolice = %s WHERE idquittance = %s", [contrat.numeropolice, e["quittance"]])
        propagations.append({"Element": "Quittance", "Champ": "N° de police", "Avant": ancienne, "Apres": contrat.numeropolice})
    return propagations
