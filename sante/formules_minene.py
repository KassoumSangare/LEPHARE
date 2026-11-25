"""
Formule MINENE suivant la taille de la famille (règle de l'utilisateur du 2026-11-25 : « MINENE a plusieurs formules avec un
nombre maximal de personnes par formule : pour une famille de 2 à 3 personnes, au-delà on passe à la formule suivante ; de
même pour une famille de 4 à 6 personnes, en moins on passe à la formule précédente »).

Les tranches sont celles des Réglages Santé MINENE (lephare_sante_formule : SOLO 1, FAMILLE 2 à 3, FAMILLE PLUS 4 à 6, pour
chaque offre commerciale 70-80, 80-80, VTC). La base fait déjà monter une famille quand une personne s'ajoute
(sp_saisie_affilie_sante v6). Ce module range toute famille hors de sa tranche, dans les deux sens, d'un devis non confirmé :
- au retrait d'une personne (POST devissante/suppression/) : FAMILLE PLUS de 4 à 3 personnes -> FAMILLE, FAMILLE à 1 -> SOLO ;
- à l'enregistrement du devis : famille saisie dans une couverture trop grande ou trop petite, devis repris ;
- à l'aperçu des primes, sans rien garder (point de sauvegarde annulé par l'appelant), pour montrer la formule retenue.
La famille passe dans la couverture de la formule adaptée de la même offre commerciale, même collège et même zone, reprise
dans le devis ou créée avec les dates de la couverture d'origine ; une couverture vidée par ce passage est retirée (sauf
aperçu). Seules les familles de l'opérateur de la saisie sont rangées (la base ne tarife que les siennes).
"""

SQL_FAMILLES = """
    SELECT a.idadherent, a.idfiliale, fi.idoffresante, o.idtarif, fi.idcollege, fi.idzonecouverture,
           fi.date_effet::date, fi.date_expiration::date, f.option, f.personnesmin, f.personnesmax,
           (SELECT COUNT(*) FROM stdaffilie x WHERE x.idadherent = a.idadherent AND x.iddevis = a.iddevis) AS taille,
           TRIM(COALESCE(a.nom, '') || ' ' || COALESCE(a.prenom, '')) AS nom
    FROM stdadherent a
    JOIN stdfiliale fi ON fi.idfiliale = a.idfiliale
    JOIN stdoffre o ON o.idoffre = fi.idoffresante
    JOIN lephare_sante_formule f ON f.idoffre = fi.idoffresante
    WHERE a.iddevis = %s AND a.idoperateur = %s {filtre}
    ORDER BY a.idadherent
"""

SQL_FORMULE_ADAPTEE = """
    SELECT f.idoffre, f.option FROM lephare_sante_formule f JOIN stdoffre o ON o.idoffre = f.idoffre
    WHERE o.idtarif = %s AND COALESCE(o.actif, TRUE) AND %s BETWEEN f.personnesmin AND f.personnesmax
    ORDER BY f.personnesmax, o.idoffre LIMIT 1
"""


class ErreurFormule(Exception):
    """Aucune formule de l'offre n'accueille la famille : message affiché tel quel."""


def _couverture(cursor, user_id, id_devis, offre, college, zone, effet, expiration):
    """Couverture du devis pour cette formule (même collège et zone, celle de l'opérateur d'abord), créée au besoin."""
    cursor.execute("""SELECT idfiliale FROM stdfiliale WHERE iddevis = %s AND idoffresante = %s
                      AND idcollege IS NOT DISTINCT FROM %s AND idzonecouverture IS NOT DISTINCT FROM %s
                      ORDER BY (idoperateur = %s) DESC, idfiliale LIMIT 1""", [id_devis, offre, college, zone, user_id])
    ligne = cursor.fetchone()
    if ligne:
        return ligne[0]
    # Même appel que la saisie d'une couverture (enregistrer_filiale_sante), sans sa validation de transaction : la création
    # fait partie du rangement, annulée avec lui
    cursor.execute("CALL sp_saisie_filiale_sante(%s, %s, %s, %s, %s, CURRENT_DATE, %s, %s, %s, %s, %s);",
                   [college, offre, zone, effet, expiration, "S", user_id, 0, id_devis, ""])
    ligne = cursor.fetchone()
    if not ligne or not ligne[0]:
        raise ErreurFormule(f"Couverture de la formule n° {offre} non créée : {(ligne[2] if ligne and len(ligne) > 2 else '') or 'refus de la base'}.")
    return ligne[0]


def texte(reclassement):
    n = reclassement["Taille"]
    return (f"Famille {reclassement['Famille'] or reclassement['IdAdherent']} ({n} personne{'s' if n > 1 else ''}) : "
            f"elle passe de {reclassement['Avant']} à {reclassement['Apres']}.")


def ranger_familles(cursor, user_id, id_devis, id_adherent=None, retirer_vides=True):
    """Range dans la formule de leur taille les familles MINENE du devis (ou la seule famille id_adherent) qui sont hors de la
    tranche de leur formule. Renvoie la liste des passages {IdAdherent, Famille, Taille, Avant, Apres}. Devis confirmé :
    rien n'est changé. ErreurFormule si aucune formule de l'offre n'accueille une famille trop grande."""
    cursor.execute("SELECT COALESCE(confirme, FALSE) FROM stddevis WHERE iddevis = %s", [id_devis])
    devis = cursor.fetchone()
    if not devis or devis[0]:
        return []
    cursor.execute(SQL_FAMILLES.format(filtre="AND a.idadherent = %s" if id_adherent else ""),
                   [id_devis, user_id] + ([id_adherent] if id_adherent else []))
    familles = cursor.fetchall()
    passages, sources = [], set()
    for (adherent, filiale, offre, tarif, college, zone, effet, expiration, option, mini, maxi, taille, nom) in familles:
        if not taille or mini <= taille <= maxi:
            continue
        cursor.execute(SQL_FORMULE_ADAPTEE, [tarif, taille])
        adaptee = cursor.fetchone()
        if not adaptee:
            if taille > maxi:
                raise ErreurFormule(f"Famille {nom or adherent} : aucune formule de l'offre n'accueille une famille de {taille} personnes "
                                    f"({maxi} au plus en {option}).")
            continue
        nouvelle_offre, nouvelle_option = adaptee
        if nouvelle_offre == offre:
            continue
        cible = _couverture(cursor, user_id, id_devis, nouvelle_offre, college, zone, effet, expiration)
        cursor.execute("UPDATE stdadherent SET idfiliale = %s WHERE idadherent = %s AND iddevis = %s", [cible, adherent, id_devis])
        sources.add(filiale)
        passages.append({"IdAdherent": adherent, "Famille": nom, "Taille": taille, "Avant": option, "Apres": nouvelle_option})
    if retirer_vides and sources:
        # Couverture vidée par ces passages : elle ne couvre plus personne
        cursor.execute("""DELETE FROM stdfiliale fi WHERE fi.idfiliale = ANY(%s) AND fi.iddevis = %s
                          AND NOT EXISTS (SELECT 1 FROM stdadherent a WHERE a.idfiliale = fi.idfiliale)""", [list(sources), id_devis])
    return passages
