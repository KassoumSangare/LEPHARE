"""
Règlements d'une police (fiche du contrat) : chaque encaissement de ses quittances (affaire nouvelle, renouvellements,
avenants), avec, à titre préventif, le nom de l'utilisateur qui l'a saisi (demande du 2026-11-23). Ce nom n'est envoyé
qu'avec le droit « Voir qui a encaissé » (encaissements.auteur) : sans lui, le serveur ne le lit même pas.

L'auteur est stdencaissement.idutilisateur, écrit à chaque encaissement depuis URANUS (mêmes comptes que LE PHARE). Seul
l'historique repris de l'ancien logiciel n'en a pas (pièces n° 1 à 28 455, écrites les 2 et 3 décembre 2025).
"""

from autorisations.rbac import a_le_droit

from .decaissements import SQL_REFERENCE

DROIT_AUTEUR = "encaissements.auteur"
LIGNES_MAX = 300
SQL_NOM_COMPTE = "COALESCE(NULLIF(TRIM(u.name), ''), NULLIF(TRIM(u.email), ''), 'Compte n° ' || u.id)"


def _lignes(cursor, sql, params):
    cursor.execute(sql, params)
    colonnes = [c[0] for c in cursor.description]
    return [dict(zip(colonnes, ligne)) for ligne in cursor.fetchall()]


def _heure(moment):
    if not hasattr(moment, "strftime"):
        return ""
    if getattr(moment, "tzinfo", None) is not None:
        from django.utils import timezone

        moment = timezone.localtime(moment)
    return "" if (moment.hour, moment.minute) == (0, 0) else moment.strftime("%H:%M")


def reglements_de_police(cursor, id_contrat, utilisateur):
    """{NumeroPolice, VoirAuteur, Reglements: [...]} ; None si le contrat n'existe pas."""
    police = _lignes(cursor, "SELECT TRIM(numeropolice) AS numeropolice FROM stdcontrat WHERE idcontrat = %s", [id_contrat])
    if not police:
        return None
    numero = police[0]["numeropolice"] or ""
    voir_auteur = a_le_droit(utilisateur, DROIT_AUTEUR)
    # Compte sans nom renseigné (compte n° 12, administrateur) : son adresse, sinon son numéro, jamais « Non enregistré »
    auteur = SQL_NOM_COMPTE if voir_auteur else "NULL"
    lignes = _lignes(cursor, f"""
        SELECT de.iddetailencaissement, e.idencaissement, TRIM(e.numeropiece) AS numeropiece, e.dateencaissement::date AS dateencaissement,
               COALESCE(e.created_at, e.datesaisie) AS datesaisie, TRIM(de.numeroquittance) AS numeroquittance,
               COALESCE(de.montant_encaissement, 0) AS montant, TRIM(COALESCE(m.libellemodepaiement, '')) AS mode,
               {SQL_REFERENCE} AS reference, COALESCE(e.piece_annulee, FALSE) AS annule,
               (SELECT a.codeavenant FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
                 WHERE c.idquittance = q.idquittance ORDER BY c.idcontrat DESC LIMIT 1) AS avenant,
               e.idutilisateur IS NOT NULL AS auteur_connu, {auteur} AS auteur
        FROM stdquittance q
        JOIN stddetailencaissement de ON de.numeroquittance = q.numeroquittance
        JOIN stdencaissement e ON e.idencaissement = de.idencaissement
        LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
        LEFT JOIN account_uranususer u ON u.id = e.idutilisateur
        WHERE TRIM(q.numeropolice) = %s AND %s <> ''
        ORDER BY e.dateencaissement DESC, de.iddetailencaissement DESC
        LIMIT {LIGNES_MAX}""", [numero, numero])
    # Montant marqué encaissé sans pièce de caisse (affaire antérieure saisie soldée, reprise d'URANUS) : une ligne pour l'écart,
    # avec pour auteur celui qui a saisi l'affaire antérieure (lephare_reprise)
    auteur_reprise = f"(SELECT {SQL_NOM_COMPTE} FROM lephare_reprise r JOIN account_uranususer u ON u.id = r.idutilisateur WHERE r.idquittance = q.idquittance ORDER BY r.id DESC LIMIT 1)"
    hors_caisse = _lignes(cursor, f"""
        SELECT TRIM(q.numeroquittance) AS numeroquittance, q.dateemission::date AS dateemission,
               COALESCE(q.mt_encaisse, 0) - COALESCE((SELECT SUM(de.montant_encaissement) FROM stddetailencaissement de
                   JOIN stdencaissement e ON e.idencaissement = de.idencaissement
                   WHERE de.numeroquittance = q.numeroquittance AND NOT COALESCE(e.piece_annulee, FALSE)), 0) AS ecart,
               (SELECT a.codeavenant FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
                 WHERE c.idquittance = q.idquittance ORDER BY c.idcontrat DESC LIMIT 1) AS avenant,
               {auteur_reprise if voir_auteur else "NULL"} AS auteur
        FROM stdquittance q
        WHERE TRIM(q.numeropolice) = %s AND %s <> ''""", [numero, numero])
    hors_caisse = [l for l in hors_caisse if (l["ecart"] or 0) > 1]
    return {
        "NumeroPolice": numero,
        "VoirAuteur": voir_auteur,
        "HorsCaisse": [{
            "Quittance": l["numeroquittance"] or "", "Avenant": (l["avenant"] or "").strip(), "Montant": float(l["ecart"]),
            "Date": l["dateemission"].isoformat() if l["dateemission"] else None,
            **({"EncaissePar": (l["auteur"] or "").strip()} if voir_auteur else {}),
        } for l in hors_caisse],
        "Reglements": [{
            "IdDetail": l["iddetailencaissement"], "IdEncaissement": l["idencaissement"], "NumeroPiece": l["numeropiece"] or "",
            "Date": l["dateencaissement"].isoformat() if l["dateencaissement"] else None, "Heure": _heure(l["datesaisie"]),
            "Quittance": l["numeroquittance"] or "", "Avenant": (l["avenant"] or "").strip(), "Montant": float(l["montant"]),
            "Mode": l["mode"], "Reference": l["reference"] or "", "Annule": bool(l["annule"]),
            **({"EncaissePar": (l["auteur"] or "").strip() if l["auteur_connu"] else ""} if voir_auteur else {}),
        } for l in lignes],
    }
