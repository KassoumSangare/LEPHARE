"""
Changement d'offre commerciale d'un devis de renouvellement MINENE (demande du 2026-11-23 : « permettre le changement de
l'offre commerciale au renouvellement en MINENE »), par exemple MINENE SANTE (70 % - 80 %) -> MINENE-SANTE (80 % - 80 %).

Le devis de renouvellement recopie les couvertures du contrat (sp_avenant_creation_devis_initial) : l'écran Santé ne
laissait plus changer d'offre commerciale qu'en retirant ces couvertures, donc les familles. Ici chaque couverture passe à
la formule de même option (SOLO, FAMILLE, FAMILLE PLUS : lephare_sante_formule) de la nouvelle offre, par la procédure de
saisie des couvertures (sp_saisie_filiale_sante : nom, contrôle de l'opérateur et des doublons) ; familles, collège, zone
et dates restent. Les primes sont recalculées à l'enregistrement du devis (sp_creation_devis_sante, aperçu de l'écran),
avec le taux d'ajustement de l'an dernier comme avant.
"""

from django.db import DatabaseError

from core.date_parser import date_emission_du_jour

from .utils import OFFRES_MINENE

ID_PRODUIT_SANTE = 5
CODE_AVENANT_RENOUVELLEMENT = "REN"


class ErreurOffreCommerciale(Exception):
    pass


def _lignes(cursor, sql, params):
    cursor.execute(sql, params)
    colonnes = [c[0] for c in cursor.description]
    return [dict(zip(colonnes, ligne)) for ligne in cursor.fetchall()]


def _message_procedure(erreur):
    """Message métier d'une procédure (« message: … » de son EXCEPTION), sans la trace PL/pgSQL."""
    texte = str(erreur)
    for ligne in texte.splitlines():
        if ligne.strip().lower().startswith("message:"):
            return ligne.split(":", 1)[1].strip()
    return texte.splitlines()[0][:300]


def formules_par_option(cursor, id_tarif):
    """{option (SOLO, FAMILLE, FAMILLE PLUS) : idoffre} des formules MINENE actives d'une offre commerciale."""
    return {
        l["option"]: l["idoffre"]
        for l in _lignes(cursor, """
            SELECT UPPER(TRIM(f.option)) AS option, f.idoffre
            FROM lephare_sante_formule f JOIN stdoffre o ON o.idoffre = f.idoffre
            WHERE o.idtarif = %s AND o.actif AND f.idoffre = ANY(%s)
            ORDER BY f.ordre, f.idoffre""", [id_tarif, list(OFFRES_MINENE)])
    }


def changer_offre_commerciale(cursor, id_utilisateur, id_devis, id_tarif):
    """Passe les couvertures d'un devis de renouvellement MINENE non confirmé aux formules de l'offre commerciale id_tarif.
    Renvoie {IdTarif, OffreCommerciale, Couvertures: [{IdFiliale, Avant, Apres}]}. À appeler dans une transaction."""
    devis = _lignes(cursor, """
        SELECT d.idproduit, COALESCE(d.confirme, FALSE) AS confirme, COALESCE(d.archive, FALSE) AS archive, a.codeavenant,
               d.dateeffet::date AS dateeffet, d.dateexpiration::date AS dateexpiration
        FROM stddevis d LEFT JOIN stdavenant a ON a.idavenant = d.idavenant
        WHERE d.iddevis = %s FOR UPDATE OF d""", [id_devis])
    if not devis:
        raise ErreurOffreCommerciale(f"Devis {id_devis} introuvable.")
    devis = devis[0]
    if devis["idproduit"] != ID_PRODUIT_SANTE:
        raise ErreurOffreCommerciale("Ce devis n'est pas un devis Santé.")
    if devis["confirme"]:
        raise ErreurOffreCommerciale("Devis déjà confirmé : l'offre commerciale ne peut plus changer.")
    if devis["archive"]:
        raise ErreurOffreCommerciale("Devis archivé : désarchivez-le pour le modifier.")
    if (devis["codeavenant"] or "").strip() != CODE_AVENANT_RENOUVELLEMENT:
        raise ErreurOffreCommerciale("L'offre commerciale d'un devis portant déjà des couvertures ne change qu'au renouvellement.")

    cible = _lignes(cursor, "SELECT TRIM(libelle) AS libelle FROM stdtarif WHERE idtarif = %s", [id_tarif])
    nouvelles = formules_par_option(cursor, id_tarif)
    if not cible or not nouvelles:
        raise ErreurOffreCommerciale("Offre commerciale inconnue ou hors MINENE.")

    couvertures = _lignes(cursor, """
        SELECT f.idfiliale, f.idcollege, f.idoffresante, f.idzonecouverture, f.date_effet::date AS date_effet,
               f.date_expiration::date AS date_expiration, COALESCE(NULLIF(TRIM(f.source), ''), 'S') AS source,
               UPPER(TRIM(sf.option)) AS option, TRIM(o.libelleoffre) AS libelle, o.idtarif
        FROM stdfiliale f
        LEFT JOIN lephare_sante_formule sf ON sf.idoffre = f.idoffresante
        LEFT JOIN stdoffre o ON o.idoffre = f.idoffresante
        WHERE f.iddevis = %s ORDER BY f.idfiliale""", [id_devis])
    if not couvertures:
        raise ErreurOffreCommerciale("Le devis n'a aucune couverture.")
    hors_minene = [c["libelle"] or str(c["idoffresante"]) for c in couvertures if c["idoffresante"] not in OFFRES_MINENE]
    if hors_minene:
        raise ErreurOffreCommerciale(f"Couvertures hors MINENE : {', '.join(hors_minene)}.")
    absentes = sorted({c["option"] or c["libelle"] for c in couvertures if nouvelles.get(c["option"]) is None})
    if absentes:
        raise ErreurOffreCommerciale(f"Aucune formule {', '.join(absentes)} dans l'offre « {cible[0]['libelle']} ».")

    libelles = {l["idoffre"]: l["libelle"] for l in _lignes(
        cursor, "SELECT idoffre, TRIM(libelleoffre) AS libelle FROM stdoffre WHERE idoffre = ANY(%s)", [list(nouvelles.values())])}
    date_emission = date_emission_du_jour()
    changees = []
    for c in couvertures:
        offre = nouvelles[c["option"]]
        if offre == c["idoffresante"]:
            continue
        try:
            cursor.execute(
                "CALL sp_saisie_filiale_sante(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [c["idcollege"], offre, c["idzonecouverture"], c["date_effet"] or devis["dateeffet"],
                 c["date_expiration"] or devis["dateexpiration"], date_emission, c["source"], id_utilisateur,
                 c["idfiliale"], id_devis, ""],
            )
            cursor.fetchone()
        except DatabaseError as erreur:
            raise ErreurOffreCommerciale(f"Couverture « {c['libelle']} » : {_message_procedure(erreur)}") from erreur
        changees.append({"IdFiliale": c["idfiliale"], "Avant": c["libelle"], "Apres": libelles.get(offre, str(offre))})

    # Ligne du devis et en-tête : nouvelle offre commerciale et formule correspondante
    correspondance = {c["idoffresante"]: nouvelles[c["option"]] for c in couvertures}
    for ancienne, nouvelle in correspondance.items():
        cursor.execute("UPDATE stddevisdetail SET idtarif = %s, idoffre = %s WHERE iddevis = %s AND idoffre = %s",
                       [id_tarif, nouvelle, id_devis, ancienne])
        cursor.execute("UPDATE stddevis SET idoffre = %s WHERE iddevis = %s AND idoffre = %s", [nouvelle, id_devis, ancienne])
    # Ligne portant une autre formule (ou aucune) : offre commerciale seule, la formule suit la première couverture
    premiere = nouvelles[couvertures[0]["option"]]
    cursor.execute(
        "UPDATE stddevisdetail SET idtarif = %s, idoffre = CASE WHEN COALESCE(idoffre, 0) = ANY(%s) THEN idoffre ELSE %s END"
        " WHERE iddevis = %s",
        [id_tarif, list(nouvelles.values()), premiere, id_devis],
    )
    cursor.execute("UPDATE stddevis SET idoffre = %s WHERE iddevis = %s AND NOT (COALESCE(idoffre, 0) = ANY(%s))",
                   [premiere, id_devis, list(nouvelles.values())])
    return {"IdTarif": id_tarif, "OffreCommerciale": cible[0]["libelle"], "Couvertures": changees}
