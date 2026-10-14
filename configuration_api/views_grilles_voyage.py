"""
Grilles Voyage modifiables depuis l'admin (Paramétrage > Grilles Voyage).

Ce que lit le calcul (fn_grille_voyage, fn_garantie_offre_voyage, sp_creation_devis_voyage) :
- grille par offre (stdzonevoyageprimensia, NSIA) : une ligne par offre, durée et âge ; sans
  zone, elle vaut dans toutes les zones où l'offre est proposée ;
- grille par formule (stdzonevoyageprime, AMSA) : une ligne par formule, zone, durée et âge ;
- chaque ligne porte prime nette, accessoire et taux de taxe ; taxe = (prime nette + accessoire)
  x taux, prime TTC = prime nette + accessoire + taxe, arrondies au franc ; la prime TTC du
  document tarifaire peut être saisie (à 1 F près du calcul), la taxe vaut alors TTC - prime
  nette - accessoire (devis sans réduction : fn_garantie_offre_voyage reprend cette TTC) ;
- offres proposées par zone (stdoffrevoyagezone) et zone de chaque pays de destination
  (stdzonevoyagepays, une zone par pays et par compagnie).

Durées en jours de couverture, date d'effet et date d'expiration comprises. Lecture pour tout
utilisateur connecté, modification réservée aux administrateurs, chaque modification est
inscrite au journal d'audit.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import connection, transaction
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from institutionnel.authentication import KnoxOrDemoTokenAuthentication
from autorisations.journal import completer_audit
from autorisations.permissions import DroitDeLaRoute

AUTHENTIFICATION = [KnoxOrDemoTokenAuthentication, BasicAuthentication]
# Compagnies dont la grille est par offre ; les autres ont une grille par formule et par zone
GRILLE_PAR_OFFRE = {1}
CATEGORIE_VOYAGE = {1: "136", 21: "137", 14: "138"}
CATEGORIE_AUTRES = "135"
AGE_MAXIMUM = 120
DUREE_MAXIMUM = 3660


class ErreurGrille(Exception):
    """Saisie refusée : message affiché tel quel."""


class EstAdministrateur(DroitDeLaRoute):
    """Réglages (grilles Voyage, paramètres, produits, Dommages, Santé MINENE, Automobile…) : écriture selon le droit
    attribué à l'utilisateur pour la route (autorisations.permissions.DroitDeLaRoute), administrateurs compris."""


def _franc(valeur):
    return Decimal(valeur).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _lignes(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.fetchall()


def _par_offre(id_compagnie):
    return id_compagnie in GRILLE_PAR_OFFRE


def _categorie(id_compagnie):
    return CATEGORIE_VOYAGE.get(id_compagnie, CATEGORIE_AUTRES)


def _journal(request, description, details):
    details = details or {}
    completer_audit(
        request,
        description=description,
        avant=details.get("avant"),
        apres=details.get("apres", {k: v for k, v in details.items() if k != "avant"}),
    )


# ------------------------------------------------------------------ lecture
def _compagnies():
    return [
        {"IdCompagnie": i, "RaisonSociale": r, "GrilleParOffre": _par_offre(i)}
        for i, r in _lignes(
            """
            SELECT c.idcompagnie, c.raisonsociale FROM stdcompagnie c
            WHERE EXISTS (SELECT 1 FROM stdzonevoyage z WHERE z.id_compagnie = c.idcompagnie)
            ORDER BY c.idcompagnie
            """
        )
    ]


def _ligne_grille(ligne, par_offre):
    (id_ligne, cle, id_zone, d_min, d_max, a_min, a_max, prime, accessoire, taux, taxe, ttc) = ligne
    return {
        "Id": id_ligne,
        ("IdOffre" if par_offre else "IdTarif"): cle,
        "IdZone": id_zone,
        "DureeMin": d_min, "DureeMax": d_max, "AgeMin": a_min, "AgeMax": a_max,
        "PrimeNette": float(prime), "Accessoire": float(accessoire), "TauxTaxe": float(taux),
        "Taxe": float(taxe), "PrimeTtc": float(ttc),
    }


SQL_GRILLE_OFFRE = """
    SELECT g.id, g.id_offre, g.id_zone, g.duree_minimum, g.duree_maximum, g.age_minimum, g.age_maximum,
           g.prime_nette, g.accessoire, g.taux_taxe, g.taxe, g.prime_ttc
    FROM stdzonevoyageprimensia g
    JOIN stdoffre o ON o.idoffre = g.id_offre
    JOIN stdtarif t ON t.idtarif = o.idtarif
    WHERE t.codecategorie = %s
"""
SQL_GRILLE_FORMULE = """
    SELECT g.id, g.id_tarif, g.id_zone, g.duree_minimum, g.duree_maximum, g.age_minimum, g.age_maximum,
           g.prime_nette, g.accessoire, g.taux_taxe, g.taxe, g.prime_ttc
    FROM stdzonevoyageprime g
    JOIN stdzonevoyage z ON z.id_zone = g.id_zone
    WHERE z.id_compagnie = %s
"""


def _grille(id_compagnie):
    if _par_offre(id_compagnie):
        lignes = _lignes(SQL_GRILLE_OFFRE + " ORDER BY g.id_offre, g.id_zone NULLS FIRST, g.age_minimum, g.duree_minimum", [_categorie(id_compagnie)])
    else:
        lignes = _lignes(SQL_GRILLE_FORMULE + " ORDER BY g.id_tarif, g.id_zone, g.age_minimum, g.duree_minimum", [id_compagnie])
    return [_ligne_grille(l, _par_offre(id_compagnie)) for l in lignes]


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def grilles_voyage(request, id_compagnie=None):
    """GET /api/grillesvoyage/ (compagnies) ou /api/grillesvoyage/<idcompagnie>/ (paramétrage complet)"""
    compagnies = _compagnies()
    if id_compagnie is None:
        return Response({"Compagnies": compagnies})
    compagnie = next((c for c in compagnies if c["IdCompagnie"] == id_compagnie), None)
    if not compagnie:
        return Response({"error": "Aucune zone Voyage pour cette compagnie."}, status=status.HTTP_404_NOT_FOUND)

    zones = [
        {"IdZone": i, "Libelle": l, "Pays": n}
        for i, l, n in _lignes(
            """
            SELECT z.id_zone, z.libelle_zone, (SELECT COUNT(*) FROM stdzonevoyagepays zp WHERE zp.id_zone = z.id_zone)
            FROM stdzonevoyage z WHERE z.id_compagnie = %s ORDER BY z.id_zone
            """,
            [id_compagnie],
        )
    ]
    formules = []
    for id_tarif, libelle in _lignes(
        "SELECT idtarif, libelle FROM stdtarif WHERE idtarif <> 0 AND codecategorie = %s ORDER BY idtarif",
        [_categorie(id_compagnie)],
    ):
        offres = [
            {"IdOffre": o, "Libelle": lo or "", "Actif": bool(actif), "Zones": list(zs or [])}
            for o, lo, actif, zs in _lignes(
                """
                SELECT o.idoffre, o.libelleoffre, o.actif,
                       ARRAY(SELECT oz.id_zone FROM stdoffrevoyagezone oz WHERE oz.id_offre = o.idoffre ORDER BY oz.id_zone)
                FROM stdoffre o WHERE o.idtarif = %s AND o.ppr = 'V' AND o.idoffre <> 0 ORDER BY o.idoffre
                """,
                [id_tarif],
            )
        ]
        formules.append({"IdTarif": id_tarif, "Libelle": libelle, "Offres": offres})
    pays = [
        {"IdPays": i, "Libelle": l, "IdZone": z}
        for i, l, z in _lignes(
            """
            SELECT p.id_pays, p.libelle_pays,
                   (SELECT zp.id_zone FROM stdzonevoyagepays zp JOIN stdzonevoyage z ON z.id_zone = zp.id_zone
                    WHERE zp.id_pays = p.id_pays AND z.id_compagnie = %s LIMIT 1)
            FROM stdpays p ORDER BY p.libelle_pays
            """,
            [id_compagnie],
        )
    ]
    return Response({
        **compagnie,
        "Zones": zones,
        "Formules": formules,
        "Pays": pays,
        "Lignes": _grille(id_compagnie),
    })


# ------------------------------------------------------------------ lignes de grille
def _entier(donnees, champ, libelle, minimum=0, maximum=None):
    try:
        valeur = int(donnees.get(champ))
    except (TypeError, ValueError):
        raise ErreurGrille(f"{libelle} : nombre entier attendu.")
    if valeur < minimum or (maximum is not None and valeur > maximum):
        raise ErreurGrille(f"{libelle} : valeur hors limites ({minimum} à {maximum})." if maximum else f"{libelle} : au moins {minimum}.")
    return valeur


def _montant(donnees, champ, libelle, maximum=None):
    try:
        valeur = Decimal(str(donnees.get(champ)).replace(" ", "").replace(",", "."))
    except (InvalidOperation, TypeError):
        raise ErreurGrille(f"{libelle} : montant invalide.")
    if valeur < 0 or (maximum is not None and valeur > maximum):
        raise ErreurGrille(f"{libelle} : valeur hors limites.")
    return valeur


def _saisie_ligne(id_compagnie, donnees):
    par_offre = _par_offre(id_compagnie)
    ligne = {
        "duree_minimum": _entier(donnees, "DureeMin", "Durée minimum", 1, DUREE_MAXIMUM),
        "duree_maximum": _entier(donnees, "DureeMax", "Durée maximum", 1, DUREE_MAXIMUM),
        "age_minimum": _entier(donnees, "AgeMin", "Âge minimum", 0, AGE_MAXIMUM),
        "age_maximum": _entier(donnees, "AgeMax", "Âge maximum", 0, AGE_MAXIMUM),
        "prime_nette": _franc(_montant(donnees, "PrimeNette", "Prime nette")),
        "accessoire": _franc(_montant(donnees, "Accessoire", "Accessoire")),
        "taux_taxe": _montant(donnees, "TauxTaxe", "Taux de taxe", Decimal("100")),
    }
    if ligne["duree_minimum"] > ligne["duree_maximum"]:
        raise ErreurGrille("La durée minimum dépasse la durée maximum.")
    if ligne["age_minimum"] > ligne["age_maximum"]:
        raise ErreurGrille("L'âge minimum dépasse l'âge maximum.")
    if ligne["prime_nette"] <= 0:
        raise ErreurGrille("La prime nette doit être positive.")

    id_zone = donnees.get("IdZone") or None
    if id_zone is not None:
        id_zone = int(id_zone)
        if not _lignes("SELECT 1 FROM stdzonevoyage WHERE id_zone = %s AND id_compagnie = %s", [id_zone, id_compagnie]):
            raise ErreurGrille("Zone inconnue pour cette compagnie.")
    if par_offre:
        cle = _entier(donnees, "IdOffre", "Offre", 1)
        if not _lignes(
            "SELECT 1 FROM stdoffre o JOIN stdtarif t ON t.idtarif = o.idtarif WHERE o.idoffre = %s AND o.ppr = 'V' AND t.codecategorie = %s",
            [cle, _categorie(id_compagnie)],
        ):
            raise ErreurGrille("Offre inconnue pour cette compagnie.")
        ligne["id_offre"] = cle
    else:
        if id_zone is None:
            raise ErreurGrille("Choisissez la zone de la ligne.")
        cle = _entier(donnees, "IdTarif", "Formule", 1)
        if not _lignes("SELECT 1 FROM stdtarif WHERE idtarif = %s AND codecategorie = %s", [cle, _categorie(id_compagnie)]):
            raise ErreurGrille("Formule inconnue pour cette compagnie.")
        ligne["id_tarif"] = cle
    ligne["id_zone"] = id_zone
    taxe_au_taux = _franc((ligne["prime_nette"] + ligne["accessoire"]) * ligne["taux_taxe"] / 100)
    # Prime TTC du document tarifaire (facultative) : le document calcule taxe et TTC sur une
    # prime nette non arrondie, sa TTC peut donc s'écarter d'1 F du calcul au taux ; la taxe
    # enregistrée vaut alors TTC - prime nette - accessoire
    ttc_document = donnees.get("PrimeTtc")
    if ttc_document not in (None, "", 0, "0"):
        ttc_document = _franc(_montant(donnees, "PrimeTtc", "Prime TTC"))
        taxe = ttc_document - ligne["prime_nette"] - ligne["accessoire"]
        if abs(taxe - taxe_au_taux) > 1:
            raise ErreurGrille(
                f"Prime TTC : {ttc_document} F s'écarte de plus d'1 F de prime nette + accessoire + taxe à "
                f"{ligne['taux_taxe'].normalize()} % ({ligne['prime_nette'] + ligne['accessoire'] + taxe_au_taux} F). "
                "Videz le champ pour la calculer."
            )
        ligne["taxe"], ligne["prime_ttc"] = taxe, ttc_document
    else:
        ligne["taxe"] = taxe_au_taux
        ligne["prime_ttc"] = ligne["prime_nette"] + ligne["accessoire"] + taxe_au_taux
    return ligne


def _controler_chevauchement(id_compagnie, ligne, id_ligne=None):
    """Deux lignes de la même offre (ou formule) et de la même zone ne se chevauchent pas."""
    if _par_offre(id_compagnie):
        table, cle = "stdzonevoyageprimensia", "id_offre"
    else:
        table, cle = "stdzonevoyageprime", "id_tarif"
    conflit = _lignes(
        f"""
        SELECT duree_minimum, duree_maximum, age_minimum, age_maximum FROM {table}
        WHERE {cle} = %s AND id_zone IS NOT DISTINCT FROM %s AND id <> %s
          AND duree_minimum <= %s AND %s <= duree_maximum AND age_minimum <= %s AND %s <= age_maximum
        LIMIT 1
        """,
        [ligne[cle], ligne["id_zone"], id_ligne or 0, ligne["duree_maximum"], ligne["duree_minimum"],
         ligne["age_maximum"], ligne["age_minimum"]],
    )
    if conflit:
        d_min, d_max, a_min, a_max = conflit[0]
        raise ErreurGrille(
            f"Chevauchement avec la ligne {d_min}-{d_max} jours, {a_min}-{a_max} ans : une durée et un âge "
            "ne doivent correspondre qu'à une ligne."
        )


COLONNES = ["duree_minimum", "duree_maximum", "age_minimum", "age_maximum", "prime_nette", "accessoire",
            "taxe", "prime_ttc", "taux_taxe", "id_zone"]


def _table(id_compagnie):
    if _par_offre(id_compagnie):
        return "stdzonevoyageprimensia", "id_offre"
    return "stdzonevoyageprime", "id_tarif"


def _lire_ligne(id_compagnie, id_ligne):
    sql = (SQL_GRILLE_OFFRE if _par_offre(id_compagnie) else SQL_GRILLE_FORMULE) + " AND g.id = %s"
    params = [_categorie(id_compagnie) if _par_offre(id_compagnie) else id_compagnie, id_ligne]
    lignes = _lignes(sql, params)
    return _ligne_grille(lignes[0], _par_offre(id_compagnie)) if lignes else None


def _reponse_erreur(erreur):
    return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def creer_ligne(request, id_compagnie):
    """POST /api/grillesvoyage/<idcompagnie>/lignes/"""
    try:
        ligne = _saisie_ligne(id_compagnie, request.data)
        table, cle = _table(id_compagnie)
        with transaction.atomic():
            _controler_chevauchement(id_compagnie, ligne)
            colonnes = [cle] + COLONNES
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""INSERT INTO {table} ({', '.join(colonnes)}, prime_nette_ristourne, taxe_ristourne, prime_ttc_ristourne)
                        VALUES ({', '.join(['%s'] * len(colonnes))}, 0, 0, 0) RETURNING id""",
                    [ligne[c] for c in colonnes],
                )
                id_ligne = cursor.fetchone()[0]
            apres = _lire_ligne(id_compagnie, id_ligne)
            _journal(request, f"Ligne de grille Voyage ajoutée (compagnie {id_compagnie})", {"apres": apres})
    except ErreurGrille as erreur:
        return _reponse_erreur(erreur)
    return Response(apres, status=status.HTTP_201_CREATED)


@api_view(["PUT", "DELETE"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def ligne_grille(request, id_compagnie, id_ligne):
    """PUT / DELETE /api/grillesvoyage/<idcompagnie>/lignes/<id>/"""
    avant = _lire_ligne(id_compagnie, id_ligne)
    if not avant:
        return Response({"error": "Ligne de grille introuvable."}, status=status.HTTP_404_NOT_FOUND)
    table, cle = _table(id_compagnie)
    if request.method == "DELETE":
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {table} WHERE id = %s", [id_ligne])
            _journal(request, f"Ligne de grille Voyage supprimée (compagnie {id_compagnie})", {"avant": avant})
        return Response(status=status.HTTP_204_NO_CONTENT)
    try:
        ligne = _saisie_ligne(id_compagnie, request.data)
        with transaction.atomic():
            _controler_chevauchement(id_compagnie, ligne, id_ligne)
            colonnes = [cle] + COLONNES
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {table} SET {', '.join(f'{c} = %s' for c in colonnes)} WHERE id = %s",
                    [ligne[c] for c in colonnes] + [id_ligne],
                )
            apres = _lire_ligne(id_compagnie, id_ligne)
            _journal(request, f"Ligne de grille Voyage modifiée (compagnie {id_compagnie})", {"avant": avant, "apres": apres})
    except ErreurGrille as erreur:
        return _reponse_erreur(erreur)
    return Response(apres)


# ------------------------------------------------------------------ offres et pays
@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def offre_voyage(request, id_compagnie, id_offre):
    """PUT /api/grillesvoyage/<idcompagnie>/offres/<idoffre>/ : libellé, offre active, zones où elle est proposée"""
    offre = _lignes(
        """
        SELECT o.libelleoffre, o.actif, ARRAY(SELECT oz.id_zone FROM stdoffrevoyagezone oz WHERE oz.id_offre = o.idoffre ORDER BY 1)
        FROM stdoffre o JOIN stdtarif t ON t.idtarif = o.idtarif
        WHERE o.idoffre = %s AND o.ppr = 'V' AND t.codecategorie = %s
        """,
        [id_offre, _categorie(id_compagnie)],
    )
    if not offre:
        return Response({"error": "Offre inconnue pour cette compagnie."}, status=status.HTTP_404_NOT_FOUND)
    libelle, actif, zones = offre[0]
    nouveau_libelle = str(request.data.get("Libelle", libelle) or "").strip()[:120]
    if not nouveau_libelle:
        return _reponse_erreur("Le libellé de l'offre est obligatoire.")
    nouvel_actif = bool(request.data.get("Actif", actif))
    try:
        nouvelles_zones = sorted({int(z) for z in request.data.get("Zones", zones)})
    except (TypeError, ValueError):
        return _reponse_erreur("Zones invalides.")
    zones_compagnie = {z for (z,) in _lignes("SELECT id_zone FROM stdzonevoyage WHERE id_compagnie = %s", [id_compagnie])}
    if not set(nouvelles_zones) <= zones_compagnie:
        return _reponse_erreur("Zone inconnue pour cette compagnie.")
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("UPDATE stdoffre SET libelleoffre = %s, actif = %s WHERE idoffre = %s", [nouveau_libelle, nouvel_actif, id_offre])
        cursor.execute("DELETE FROM stdoffrevoyagezone WHERE id_offre = %s", [id_offre])
        for zone in nouvelles_zones:
            cursor.execute("INSERT INTO stdoffrevoyagezone (id_offre, id_zone) VALUES (%s, %s)", [id_offre, zone])
        _journal(
            request,
            f"Offre Voyage {id_offre} modifiée (compagnie {id_compagnie})",
            {"avant": {"Libelle": libelle, "Actif": actif, "Zones": list(zones or [])},
             "apres": {"Libelle": nouveau_libelle, "Actif": nouvel_actif, "Zones": nouvelles_zones}},
        )
    return Response({"IdOffre": id_offre, "Libelle": nouveau_libelle, "Actif": nouvel_actif, "Zones": nouvelles_zones})


@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def pays_zone(request, id_compagnie, id_pays):
    """PUT /api/grillesvoyage/<idcompagnie>/pays/<idpays>/ {IdZone} : zone du pays de destination (vide = non couvert)"""
    if not _lignes("SELECT 1 FROM stdpays WHERE id_pays = %s", [id_pays]):
        return Response({"error": "Pays inconnu."}, status=status.HTTP_404_NOT_FOUND)
    id_zone = request.data.get("IdZone") or None
    if id_zone is not None:
        id_zone = int(id_zone)
        if not _lignes("SELECT 1 FROM stdzonevoyage WHERE id_zone = %s AND id_compagnie = %s", [id_zone, id_compagnie]):
            return _reponse_erreur("Zone inconnue pour cette compagnie.")
    avant = _lignes(
        """
        SELECT zp.id_zone FROM stdzonevoyagepays zp JOIN stdzonevoyage z ON z.id_zone = zp.id_zone
        WHERE zp.id_pays = %s AND z.id_compagnie = %s
        """,
        [id_pays, id_compagnie],
    )
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM stdzonevoyagepays WHERE id_pays = %s AND id_zone IN (SELECT id_zone FROM stdzonevoyage WHERE id_compagnie = %s)",
            [id_pays, id_compagnie],
        )
        if id_zone is not None:
            cursor.execute("INSERT INTO stdzonevoyagepays (id_pays, id_zone) VALUES (%s, %s)", [id_pays, id_zone])
        _journal(
            request,
            f"Zone Voyage du pays {id_pays} modifiée (compagnie {id_compagnie})",
            {"avant": [z for (z,) in avant], "apres": id_zone},
        )
    return Response({"IdPays": id_pays, "IdZone": id_zone})
