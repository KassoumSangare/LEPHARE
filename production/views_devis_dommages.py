"""
Devis Dommages (produit 9) : toutes les catégories de la branche (tarifs 4xx) — Assurance Caution,
Tous Risques Informatiques, Globale de Banque, Tous Risques Chantiers / Montage, Bris de Machines,
Perte d'Exploitation, Dommage Ouvrage, Dommages en Tous Lieux, Tous Risques Bijoutier, Risques
Exceptionnels, Globale Dommage.

URANUS ne savait tarifer que la TRI et la Caution (sp_creation_devis_tousrisquesinfo : sous-garanties
101, 62, 102 et 243 codées en dur). Ici, les garanties sont celles de l'offre de la catégorie pour la
compagnie (stdoffregarantie), avec les réglages de l'admin (Réglages Dommages : catégories ouvertes,
description du risque demandée, prorata, taux proposé et garanties obligatoires) :
- GET  /api/dommages/catalogue/?compagnie=<id>  catégories, garanties et taux de taxe de la compagnie ;
- POST /api/dommages/calcul/                     primes sans rien écrire (fn_garantie_offre_dommages) ;
- POST /api/dommages/devis/                      création ou « Modifier » (sp_creation_devis_dommages) ;
- GET  /api/dommages/devis/<id>/                 tout ce qui a été saisi et calculé sur le devis.
Les devis enregistrés par URANUS (sans « saisie ») sont relus depuis leurs garanties.
"""

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from configuration_api.models import DommageCategorie, DommageGarantie
from core.date_parser import date_emission_du_jour
from institutionnel.authentication import KnoxOrDemoTokenAuthentication

from .database import enregistrer_terme_devis

ID_INTERMEDIAIRE = 1
ID_PRODUIT_DOMMAGES = 9
ID_AVENANT_AFFAIRE_NOUVELLE = 1
AUTHENTIFICATION = [KnoxOrDemoTokenAuthentication, BasicAuthentication]
TYPES_CHAMP = {code for code, _ in DommageCategorie.TYPES_CHAMP}


class ErreurDevisDommages(Exception):
    """Erreur de saisie à afficher telle quelle à l'utilisateur."""


# ------------------------------------------------------------------ lecture de la saisie
def _date(valeur, champ):
    if isinstance(valeur, date):
        return valeur
    texte = str(valeur or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(texte, fmt).date()
        except ValueError:
            continue
    raise ErreurDevisDommages(f"{champ} : date invalide ({valeur!r}).")


def _entier(valeur, champ, obligatoire=True):
    try:
        nombre = int(valeur or 0)
    except (TypeError, ValueError):
        raise ErreurDevisDommages(f"{champ} : valeur invalide ({valeur!r}).")
    if obligatoire and nombre <= 0:
        raise ErreurDevisDommages(f"{champ} : à renseigner.")
    return nombre


def _decimal(valeur, champ, maximum=None, vide=Decimal("0")):
    if valeur is None or str(valeur).strip() == "":
        return vide
    try:
        nombre = Decimal(str(valeur).replace(" ", "").replace(",", "."))
    except InvalidOperation:
        raise ErreurDevisDommages(f"{champ} : nombre attendu ({valeur!r}).")
    if nombre < 0:
        raise ErreurDevisDommages(f"{champ} : la valeur ne peut pas être négative.")
    if maximum is not None and nombre > maximum:
        raise ErreurDevisDommages(f"{champ} : {maximum} au plus.")
    return nombre


def _nombre(valeur):
    return float(valeur) if valeur is not None else 0


def _iso(valeur):
    if valeur is None:
        return None
    if isinstance(valeur, datetime):
        valeur = valeur.date()
    return valeur.isoformat()


def _une_ligne(cursor, sql, params):
    cursor.execute(sql, params)
    return cursor.fetchone()


def _garanties_saisies(liste):
    """Liste des garanties de l'écran -> liste normalisée (p_liste_garantie de la procédure)."""
    if not isinstance(liste, list):
        raise ErreurDevisDommages("Garanties : liste attendue.")
    garanties = []
    vues = set()
    for g in liste:
        if not isinstance(g, dict):
            continue
        id_sg = _entier(g.get("IdSousGarantie") or g.get("id_garantie"), "Garantie")
        if id_sg in vues:
            continue
        vues.add(id_sg)
        libelle = str(g.get("Libelle") or f"garantie n° {id_sg}")
        franchise = {}
        for cle, cle_json in (("TauxFranchise", "taux_franchise"), ("FranchiseMinimum", "franchise_minimum"),
                              ("FranchiseMaximum", "franchise_maximum")):
            if g.get(cle) is not None and str(g.get(cle)).strip() != "":
                franchise[cle_json] = _decimal(g.get(cle), f"{libelle} : franchise",
                                               maximum=Decimal("100") if cle == "TauxFranchise" else None)
        garanties.append({
            "id_garantie": id_sg,
            "acquise": bool(g.get("Acquise")),
            "capital": _decimal(g.get("Capital"), f"{libelle} : capital"),
            "taux": _decimal(g.get("Taux"), f"{libelle} : taux de prime", maximum=Decimal("100")),
            "prime": _decimal(g.get("Prime"), f"{libelle} : prime"),
            **franchise,
        })
    return garanties


def _json(garanties):
    return json.dumps(garanties, default=lambda v: float(v) if isinstance(v, Decimal) else str(v))


# ------------------------------------------------------------------ catalogue
def _categories(cursor):
    """Catégories Dommages (stdtarif 4xx) avec leur offre et leurs réglages LE PHARE."""
    cursor.execute(
        """
        SELECT t.idtarif, t.libelle, t.codecategorie,
               (SELECT o.idoffre FROM stdoffre o WHERE o.idtarif = t.idtarif ORDER BY o.actif DESC, o.idoffre LIMIT 1),
               (SELECT o.libelleoffre FROM stdoffre o WHERE o.idtarif = t.idtarif ORDER BY o.actif DESC, o.idoffre LIMIT 1)
        FROM stdtarif t
        WHERE t.codecategorie LIKE '4%%' AND t.idtarif <> 0
        """
    )
    lignes = cursor.fetchall()
    reglages = {c.IdTarif: c for c in DommageCategorie.objects.all()}
    categories = []
    for id_tarif, libelle, code, id_offre, libelle_offre in lignes:
        r = reglages.get(id_tarif)
        categories.append({
            "IdTarif": id_tarif,
            "Libelle": libelle,
            "CodeCategorie": code,
            "IdOffre": id_offre or 0,
            "LibelleOffre": libelle_offre or "",
            # Catégorie sans réglage (ajoutée au référentiel depuis) : proposée, sans description
            "SaisieOuverte": r.SaisieOuverte if r else True,
            "Ordre": r.Ordre if r else 999,
            "Description": r.Description if r else "",
            "Prorata": r.Prorata if r else False,
            "ChampsRisque": [c for c in (r.ChampsRisque if r else []) if isinstance(c, dict) and c.get("Cle")],
        })
    categories.sort(key=lambda c: (c["Ordre"], c["Libelle"]))
    return categories


def garanties_offre(cursor, id_offre, id_compagnie, date_effet=None):
    """Garanties de l'offre pour la compagnie, avec franchise, taxe du produit 9 et réglages LE PHARE."""
    cursor.execute(
        """
        SELECT DISTINCT ON (og.idsousgarantie)
               og.idsousgarantie, sg.libellesousgarantie, sg.idgarantie, g.libellegarantie,
               og.tauxfranchise, og.franchiseminimum, og.franchisemaximum, og.ordreaffichage,
               (SELECT tt.tauxtaxe FROM stdtauxtaxegarantieproduit tt
                 WHERE tt.idgarantie = og.idsousgarantie AND tt.idproduit = 9
                   AND %s BETWEEN tt.debutvalidite AND tt.finvalidite
                 ORDER BY tt.debutvalidite DESC LIMIT 1)
        FROM stdoffregarantie og
        JOIN stdsousgarantie sg ON sg.idsousgarantie = og.idsousgarantie
        LEFT JOIN stdgarantie g ON g.idgarantie = sg.idgarantie
        WHERE og.idoffre = %s AND og.idcompagnie = %s
        ORDER BY og.idsousgarantie, og.idoffregarantie
        """,
        [date_effet or date.today(), id_offre, id_compagnie],
    )
    lignes = cursor.fetchall()
    reglages = {
        r.IdSousGarantie: r
        for r in DommageGarantie.objects.filter(IdOffre=id_offre, IdCompagnie=id_compagnie)
    }
    garanties = []
    for id_sg, libelle, id_g, libelle_g, tf, fmin, fmax, ordre, taxe in lignes:
        r = reglages.get(id_sg)
        garanties.append({
            "IdSousGarantie": id_sg,
            "Libelle": libelle,
            "IdGarantie": id_g,
            "LibelleGarantie": libelle_g or "",
            "TauxFranchise": _nombre(tf),
            "FranchiseMinimum": _nombre(fmin),
            "FranchiseMaximum": _nombre(fmax),
            "Ordre": ordre or 0,
            "TauxTaxe": _nombre(taxe) if taxe is not None else None,
            "TauxDefaut": _nombre(r.TauxDefaut) if r and r.TauxDefaut is not None else None,
            "Obligatoire": bool(r and r.Obligatoire),
        })
    garanties.sort(key=lambda g: (g["Ordre"], g["Libelle"]))
    return garanties


def _compagnies_dommages(cursor):
    """Compagnies ayant au moins une garantie Dommages paramétrée."""
    cursor.execute(
        """
        SELECT c.idcompagnie, c.raisonsociale, COUNT(DISTINCT o.idtarif)
        FROM stdoffregarantie og
        JOIN stdoffre o ON o.idoffre = og.idoffre
        JOIN stdtarif t ON t.idtarif = o.idtarif AND t.codecategorie LIKE '4%%'
        JOIN stdcompagnie c ON c.idcompagnie = og.idcompagnie
        WHERE c.idcompagnie <> 0
        GROUP BY c.idcompagnie, c.raisonsociale
        ORDER BY c.raisonsociale
        """
    )
    return [{"IdCompagnie": i, "RaisonSociale": n, "NbCategories": k} for i, n, k in cursor.fetchall()]


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def catalogue_dommages(request):
    """GET /api/dommages/catalogue/?compagnie=<id> : catégories et garanties de la compagnie."""
    try:
        id_compagnie = int(request.query_params.get("compagnie") or 0)
    except ValueError:
        id_compagnie = 0
    with connection.cursor() as cursor:
        compagnies = _compagnies_dommages(cursor)
        if not id_compagnie and compagnies:
            id_compagnie = next((c["IdCompagnie"] for c in compagnies if c["IdCompagnie"] == 1), compagnies[0]["IdCompagnie"])
        categories = _categories(cursor)
        for categorie in categories:
            categorie["Garanties"] = (
                garanties_offre(cursor, categorie["IdOffre"], id_compagnie) if categorie["IdOffre"] and id_compagnie else []
            )
        taux_commission = _une_ligne(
            cursor, "SELECT fn_get_taux_commission(%s, %s, %s)", [ID_PRODUIT_DOMMAGES, id_compagnie, date.today()]
        )[0] if id_compagnie else 0
    return Response({
        "IdCompagnie": id_compagnie,
        "TauxCommission": _nombre(taux_commission),
        "Compagnies": compagnies,
        "Categories": categories,
    })


# ------------------------------------------------------------------ calcul
def _categorie(cursor, id_tarif):
    categorie = next((c for c in _categories(cursor) if c["IdTarif"] == id_tarif), None)
    if not categorie:
        raise ErreurDevisDommages("Cette catégorie n'appartient pas à la branche Dommages.")
    if not categorie["IdOffre"]:
        raise ErreurDevisDommages(f"Aucune offre n'est paramétrée pour la catégorie « {categorie['Libelle']} ».")
    return categorie


def _calculer(cursor, id_compagnie, categorie, garanties, taux_reduction, date_effet, date_expiration, accessoire):
    cursor.execute(
        """
        SELECT idgarantie, libellegarantie, idsousgarantie, libellesousgarantie, acquise, capital, tauxprime,
               primeannuelle, primenette, tauxtaxe, taxe, tauxfranchise, franchiseminimum, franchisemaximum,
               textefranchise, accessoirecompagnie, accessoireintermediaire, taxeaccessoire, primettc, coefficientprorata
        FROM fn_garantie_offre_dommages(%s, %s, %s::jsonb, %s, %s, %s, %s, %s)
        """,
        [id_compagnie, categorie["IdOffre"], _json(garanties), taux_reduction, date_effet, date_expiration,
         categorie["Prorata"], accessoire],
    )
    lignes, cumul = [], None
    for l in cursor.fetchall():
        if l[2] == 0:
            cumul = l
            continue
        lignes.append({
            "IdGarantie": l[0],
            "LibelleGarantie": l[1] or "",
            "IdSousGarantie": l[2],
            "Libelle": l[3],
            "Acquise": bool(l[4]),
            "Capital": _nombre(l[5]),
            "Taux": _nombre(l[6]),
            "PrimeAnnuelle": _nombre(l[7]),
            "PrimeNette": _nombre(l[8]),
            "TauxTaxe": _nombre(l[9]),
            "Taxe": _nombre(l[10]),
            "TauxFranchise": _nombre(l[11]),
            "FranchiseMinimum": _nombre(l[12]),
            "FranchiseMaximum": _nombre(l[13]),
            "TexteFranchise": l[14] or "",
        })
    taux_commission = _une_ligne(
        cursor, "SELECT fn_get_taux_commission(%s, %s, %s)", [ID_PRODUIT_DOMMAGES, id_compagnie, date_emission_du_jour()]
    )[0] or 0
    pn = _nombre(cumul[8]) if cumul else 0
    acc_cie, acc_int, taxe_acc = (_nombre(cumul[15]), _nombre(cumul[16]), _nombre(cumul[17])) if cumul else (0, 0, 0)
    return {
        "Lignes": lignes,
        "Cumul": {
            "PrimeAnnuelle": _nombre(cumul[7]) if cumul else 0,
            "PrimeNette": pn,
            "TaxeGaranties": (_nombre(cumul[10]) - taxe_acc) if cumul else 0,
            "TaxeAccessoire": taxe_acc,
            "Taxe": _nombre(cumul[10]) if cumul else 0,
            "AccessoireCompagnie": acc_cie,
            "AccessoireIntermediaire": acc_int,
            "Accessoire": acc_cie + acc_int,
            "PrimeTtc": _nombre(cumul[18]) if cumul else 0,
            "CoefficientProrata": _nombre(cumul[19]) if cumul else 1,
            "TauxCommission": _nombre(taux_commission),
            "Commission": round(pn * _nombre(taux_commission) / 100),
        },
    }


def _accessoire(valeur):
    """None : barème de la compagnie ; sinon accessoire imposé."""
    if valeur is None or str(valeur).strip() == "":
        return None
    return _decimal(valeur, "Accessoire")


def _lire_parametres_calcul(donnees, cursor):
    id_compagnie = _entier(donnees.get("IdCompagnie"), "Compagnie")
    id_tarif = _entier(donnees.get("IdTarif"), "Catégorie")
    categorie = _categorie(cursor, id_tarif)
    date_effet = _date(donnees.get("DateEffet"), "Date d'effet")
    date_expiration = _date(donnees.get("DateExpiration"), "Date d'expiration")
    if date_expiration < date_effet:
        raise ErreurDevisDommages("La date d'expiration doit suivre la date d'effet.")
    return {
        "id_compagnie": id_compagnie,
        "categorie": categorie,
        "date_effet": date_effet,
        "date_expiration": date_expiration,
        "taux_reduction": _decimal(donnees.get("TauxReduction"), "Réduction", maximum=Decimal("100")),
        "garanties": _garanties_saisies(donnees.get("Garanties") or []),
        "accessoire": _accessoire(donnees.get("Accessoire")),
    }


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def calcul_dommages(request):
    """POST /api/dommages/calcul/ : garanties et prime, sans écriture."""
    try:
        with connection.cursor() as cursor:
            p = _lire_parametres_calcul(request.data, cursor)
            return Response(_calculer(cursor, p["id_compagnie"], p["categorie"], p["garanties"], p["taux_reduction"],
                                      p["date_effet"], p["date_expiration"], p["accessoire"]))
    except ErreurDevisDommages as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)


# ------------------------------------------------------------------ enregistrement
def _controler(cursor, donnees, p):
    """Contrôles avant la procédure. Renvoie (id_devis, id_avenant, garanties autorisées hors offre)."""
    id_devis = _entier(donnees.get("IdDevis"), "Devis", obligatoire=False)
    id_avenant = ID_AVENANT_AFFAIRE_NOUVELLE
    deja_sur_le_devis = set()
    categorie_du_devis = None
    if id_devis:
        devis = _une_ligne(cursor, "SELECT idproduit, confirme, idavenant FROM stddevis WHERE iddevis = %s", [id_devis])
        if not devis:
            raise ErreurDevisDommages("Devis inexistant : modification impossible.")
        if devis[0] != ID_PRODUIT_DOMMAGES:
            raise ErreurDevisDommages("Ce devis n'est pas un devis Dommages.")
        if devis[1]:
            raise ErreurDevisDommages("Devis déjà confirmé (contrat émis) : modification impossible.")
        id_avenant = devis[2] or ID_AVENANT_AFFAIRE_NOUVELLE
        cursor.execute(
            """
            SELECT g.idgarantie, dd.idtarif FROM stddevisdetail dd
            LEFT JOIN stddevisdetgarantie g ON g.iddevisdet = dd.iddevisdetail
            WHERE dd.iddevis = %s
            """,
            [id_devis],
        )
        for id_sg, id_tarif in cursor.fetchall():
            categorie_du_devis = id_tarif
            if id_sg:
                deja_sur_le_devis.add(id_sg)

    categorie = p["categorie"]
    if not categorie["SaisieOuverte"] and categorie["IdTarif"] != categorie_du_devis:
        raise ErreurDevisDommages(f"La catégorie « {categorie['Libelle']} » est fermée à la saisie (Réglages Dommages).")
    if not _une_ligne(cursor, "SELECT 1 FROM stdcompagnie WHERE idcompagnie = %s", [p["id_compagnie"]]):
        raise ErreurDevisDommages("Compagnie inconnue.")

    offre = {g["IdSousGarantie"]: g for g in garanties_offre(cursor, categorie["IdOffre"], p["id_compagnie"], p["date_effet"])}
    if not offre and not deja_sur_le_devis:
        raise ErreurDevisDommages(
            f"Aucune garantie n'est paramétrée pour « {categorie['Libelle']} » chez cette compagnie (Réglages Dommages)."
        )
    saisies = {g["id_garantie"]: g for g in p["garanties"]}
    for id_sg, g in saisies.items():
        if id_sg not in offre and id_sg not in deja_sur_le_devis:
            raise ErreurDevisDommages(f"La garantie n° {id_sg} ne fait pas partie de l'offre de cette catégorie.")
    # Garanties obligatoires toujours retenues
    for id_sg, g in offre.items():
        if g["Obligatoire"]:
            if id_sg in saisies:
                saisies[id_sg]["acquise"] = True
            else:
                p["garanties"].append({"id_garantie": id_sg, "acquise": True, "capital": Decimal(0), "taux": Decimal(0), "prime": Decimal(0)})
    retenues = [g for g in p["garanties"] if g["acquise"]]
    if not retenues:
        raise ErreurDevisDommages("Retenez au moins une garantie.")
    for g in retenues:
        libelle = offre.get(g["id_garantie"], {}).get("Libelle", f"garantie n° {g['id_garantie']}")
        if g["taux"] > 0 and g["capital"] <= 0:
            raise ErreurDevisDommages(f"{libelle} : saisissez le capital auquel s'applique le taux de prime.")

    # Description du risque : champs obligatoires de la catégorie
    risque = donnees.get("Risque") or {}
    if not isinstance(risque, dict):
        raise ErreurDevisDommages("Description du risque : données attendues sous forme de fiche.")
    champs = {c["Cle"]: c for c in categorie["ChampsRisque"]}
    risque_propre = {}
    for cle, valeur in risque.items():
        texte = str(valeur or "").strip()[:2000]
        if texte and cle in champs:
            champ = champs[cle]
            if champ.get("Type") == "liste" and champ.get("Options") and texte not in champ["Options"]:
                raise ErreurDevisDommages(f"« {champ.get('Libelle') or cle} » : choix inconnu ({texte}).")
            if champ.get("Type") == "montant":
                texte = re.sub(r"[^0-9]", "", texte)
                if not texte:
                    continue
            risque_propre[cle] = texte
    for cle, champ in champs.items():
        if champ.get("Obligatoire") and not risque_propre.get(cle):
            raise ErreurDevisDommages(f"Description du risque : « {champ.get('Libelle') or cle} » est à renseigner.")

    for champ, libelle in (("IdClient", "Souscripteur"), ("IdAssure", "Assuré")):
        identifiant = _entier(donnees.get(champ) or donnees.get("IdClient"), libelle)
        if not _une_ligne(cursor, "SELECT 1 FROM stdclient WHERE idclient = %s", [identifiant]):
            raise ErreurDevisDommages(f"{libelle} introuvable (client n° {identifiant}).")
    return id_devis, id_avenant, risque_propre


def enregistrer_devis_dommages(donnees, id_utilisateur):
    with transaction.atomic(), connection.cursor() as cursor:
        p = _lire_parametres_calcul(donnees, cursor)
        id_devis, id_avenant, risque = _controler(cursor, donnees, p)
        calcul = _calculer(cursor, p["id_compagnie"], p["categorie"], p["garanties"], p["taux_reduction"],
                           p["date_effet"], p["date_expiration"], p["accessoire"])
        if calcul["Cumul"]["PrimeNette"] <= 0:
            raise ErreurDevisDommages(
                "La prime nette est nulle : saisissez un taux de prime et un capital, ou un montant de prime."
            )
        id_client = _entier(donnees.get("IdClient"), "Souscripteur")
        id_assure = _entier(donnees.get("IdAssure") or id_client, "Assuré")
        saisie = {
            "version": 1,
            "risque": risque,
            "garanties": p["garanties"],
            "accessoire_impose": p["accessoire"],
            "prorata": p["categorie"]["Prorata"],
        }
        cursor.execute(
            "CALL sp_creation_devis_dommages(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s);",
            [
                ID_INTERMEDIAIRE,
                p["id_compagnie"],
                id_avenant,
                id_client,
                id_assure,
                p["date_effet"],
                p["date_expiration"],
                date_emission_du_jour(),
                p["categorie"]["IdTarif"],
                p["taux_reduction"],
                _json(p["garanties"]),
                p["categorie"]["Prorata"],
                p["accessoire"],
                _entier(donnees.get("IdDuree"), "Durée", obligatoire=False),
                str(donnees.get("TelephoneAssure") or "").strip()[:30],
                str(donnees.get("NumeroPoliceCompagnie") or "").strip()[:60],
                _json(saisie),
                id_utilisateur,
                id_devis,
                "",
            ],
        )
        id_devis, message = cursor.fetchone()
        if not id_devis:
            raise ErreurDevisDommages(message or "Le devis n'a pas été enregistré.")
        enregistrer_terme_devis(id_devis, donnees.get("IdTerme"))
        # Compagnie ou catégorie changée : le déclencheur différé renumérote le devis (code catégorie) ;
        # contrôles immédiats pour renvoyer le numéro définitif
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        totaux = _une_ligne(
            cursor,
            "SELECT numerodevis, primeannuelle, primenette, accessoire, taxe, primettc FROM stddevis WHERE iddevis = %s",
            [id_devis],
        )
    return {
        "ObjectId": id_devis,
        "OutputMessage": message or "Devis enregistré avec succès.",
        "NumeroDevis": totaux[0],
        "PrimeAnnuelle": _nombre(totaux[1]),
        "PrimeNette": _nombre(totaux[2]),
        "Accessoire": _nombre(totaux[3]),
        "Taxe": _nombre(totaux[4]),
        "PrimeTtc": _nombre(totaux[5]),
    }


def _id_utilisateur(request):
    identifiant = getattr(request.user, "id", None) or getattr(request.user, "pk", None)
    if identifiant is None:
        return None
    try:
        return int(identifiant)
    except (TypeError, ValueError):
        return None


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def enregistrer_devis_dommages_vue(request):
    """POST /api/dommages/devis/ (IdDevis > 0 : modification)"""
    try:
        resultat = enregistrer_devis_dommages(request.data, _id_utilisateur(request))
    except ErreurDevisDommages as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as erreur:  # message de la base (RAISE EXCEPTION de la procédure)
        return Response({"error": str(erreur).split("\n")[0]}, status=status.HTTP_400_BAD_REQUEST)
    return Response(resultat, status=status.HTTP_201_CREATED)


# ------------------------------------------------------------------ relecture
def _personne(cursor, id_client):
    ligne = _une_ligne(
        cursor,
        """
        SELECT idclient, TRIM(COALESCE(nom, '') || ' ' || COALESCE(prenoms, '')), telephone, mobile, adresse1, adresse2,
               datenaissance, email, fax
        FROM stdclient WHERE idclient = %s
        """,
        [id_client],
    )
    if not ligne:
        return None
    return {
        "IdClient": ligne[0],
        "Nom": ligne[1],
        "Telephone": ligne[3] or ligne[2] or "",
        "Adresse": ligne[4] or "",
        "AdresseGeographique": ligne[5] or "",
        "DateNaissance": _iso(ligne[6]),
        "Email": (ligne[7] or "").strip(),
        "Fax": (ligne[8] or "").strip(),
    }


def lire_dommages(cursor, iddevis):
    """Devis Dommages tel qu'enregistré (None s'il n'existe pas ou n'est pas un devis Dommages)."""
    entete = _une_ligne(
        cursor,
        """
        SELECT d.iddevis, d.numerodevis, d.idproduit, d.confirme, COALESCE(d.archive, FALSE), d.idavenant,
               d.idcompagnie, c.raisonsociale, d.idclient, d.idassure, d.dateemission, d.dateeffet, d.dateexpiration,
               d.idterme, d.idduree, d.numeropolicecompagnie, d.primeannuelle, d.primenette, d.accessoire, d.taxe,
               d.primettc, d.commissionintermediaire
        FROM stddevis d LEFT JOIN stdcompagnie c ON c.idcompagnie = d.idcompagnie
        WHERE d.iddevis = %s
        """,
        [iddevis],
    )
    if not entete or entete[2] != ID_PRODUIT_DOMMAGES:
        return None
    detail = _une_ligne(
        cursor,
        """
        SELECT dd.iddevisdetail, dd.idtarif, t.libelle, t.codecategorie, dd.idoffre, o.libelleoffre, dd.tauxreduction,
               cd.tauxprime, cd.montantprime, cd.saisie
        FROM stddevisdetail dd
        LEFT JOIN stdtarif t ON t.idtarif = dd.idtarif
        LEFT JOIN stdoffre o ON o.idoffre = dd.idoffre
        LEFT JOIN stdcomplementdevisdetaildommage cd ON cd.iddevisdetail = dd.iddevisdetail
        WHERE dd.iddevis = %s
        ORDER BY dd.iddevisdetail, cd.idcomplement DESC
        LIMIT 1
        """,
        [iddevis],
    )
    garanties = []
    saisie = None
    if detail:
        cursor.execute(
            """
            SELECT g.idgarantie, sg.libellesousgarantie, g.capital, g.primeannuelle, g.primenette, g.taxe,
                   g.tauxfranchise, g.minfranchise, g.maxfranchise, g.textefranchise
            FROM stddevisdetgarantie g
            LEFT JOIN stdsousgarantie sg ON sg.idsousgarantie = g.idgarantie
            WHERE g.iddevisdet = %s AND g.acquise
            ORDER BY g.idgarantie
            """,
            [detail[0]],
        )
        garanties = [
            {
                "IdSousGarantie": g[0],
                "Libelle": g[1] or f"Garantie n° {g[0]}",
                "Capital": _nombre(g[2]),
                "PrimeAnnuelle": _nombre(g[3]),
                "PrimeNette": _nombre(g[4]),
                "Taxe": _nombre(g[5]),
                "TauxFranchise": _nombre(g[6]),
                "FranchiseMinimum": _nombre(g[7]),
                "FranchiseMaximum": _nombre(g[8]),
                "TexteFranchise": g[9] or "",
            }
            for g in cursor.fetchall()
        ]
        saisie = detail[9] if isinstance(detail[9], dict) else (json.loads(detail[9]) if detail[9] else None)

    if saisie:
        garanties_saisies = [
            {
                "IdSousGarantie": g.get("id_garantie"),
                "Acquise": bool(g.get("acquise")),
                "Capital": _nombre(Decimal(str(g.get("capital") or 0))),
                "Taux": _nombre(Decimal(str(g.get("taux") or 0))),
                "Prime": _nombre(Decimal(str(g.get("prime") or 0))),
                **({"TauxFranchise": _nombre(Decimal(str(g["taux_franchise"])))} if g.get("taux_franchise") is not None else {}),
                **({"FranchiseMinimum": _nombre(Decimal(str(g["franchise_minimum"])))} if g.get("franchise_minimum") is not None else {}),
                **({"FranchiseMaximum": _nombre(Decimal(str(g["franchise_maximum"])))} if g.get("franchise_maximum") is not None else {}),
            }
            for g in saisie.get("garanties") or []
        ]
        accessoire_impose = saisie.get("accessoire_impose")
    else:
        # Devis enregistré par URANUS : taux commun du complément, sinon prime saisie par garantie
        taux_commun = _nombre(detail[7]) if detail else 0
        garanties_saisies = [
            {
                "IdSousGarantie": g["IdSousGarantie"],
                "Acquise": True,
                "Capital": g["Capital"],
                "Taux": taux_commun if taux_commun > 0 and g["Capital"] > 0 else 0,
                "Prime": 0 if taux_commun > 0 and g["Capital"] > 0 else g["PrimeAnnuelle"],
                "TauxFranchise": g["TauxFranchise"],
                "FranchiseMinimum": g["FranchiseMinimum"],
                "FranchiseMaximum": g["FranchiseMaximum"],
            }
            for g in garanties
        ]
        # Accessoire enregistré gardé tel quel (repris d'URANUS, parfois saisi à la main)
        accessoire_impose = _nombre(entete[18]) if entete[18] else None

    client = _personne(cursor, entete[8])
    assure = client if entete[9] == entete[8] else _personne(cursor, entete[9])
    description = risque_dommages(cursor, iddevis) if detail else None
    return {
        "Risque": description["description"] if description else [],
        "Fiche": description["fiche"] if description else {},
        "IdDevis": entete[0],
        "NumeroDevis": entete[1],
        "Confirme": bool(entete[3]),
        "Archive": bool(entete[4]),
        "IdAvenant": entete[5],
        "IdCompagnie": entete[6],
        "Compagnie": entete[7] or "",
        "IdClient": entete[8],
        "IdAssure": entete[9],
        "DateEmission": _iso(entete[10]),
        "DateEffet": _iso(entete[11]),
        "DateExpiration": _iso(entete[12]),
        "IdTerme": entete[13],
        "IdDuree": entete[14],
        "NumeroPoliceCompagnie": entete[15] or "",
        "PrimeAnnuelle": _nombre(entete[16]),
        "PrimeNette": _nombre(entete[17]),
        "Accessoire": _nombre(entete[18]),
        "Taxe": _nombre(entete[19]),
        "PrimeTtc": _nombre(entete[20]),
        "Commission": _nombre(entete[21]),
        "Detail": {
            "IdDevisDetail": detail[0],
            "IdTarif": detail[1],
            "LibelleTarif": detail[2] or "",
            "CodeCategorie": detail[3] or "",
            "IdOffre": detail[4],
            "LibelleOffre": detail[5] or "",
            "TauxReduction": _nombre(detail[6]),
        } if detail else None,
        "Garanties": garanties,
        "Saisie": {
            "Origine": "LE PHARE" if saisie else "URANUS",
            "Risque": (saisie or {}).get("risque") or {},
            "Garanties": garanties_saisies,
            "AccessoireImpose": _nombre(Decimal(str(accessoire_impose))) if accessoire_impose is not None else None,
            "Prorata": bool((saisie or {}).get("prorata")),
        },
        "Client": client,
        "Assure": assure,
    }


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def lire_devis_dommages(request, iddevis):
    """GET /api/dommages/devis/<iddevis>/"""
    with connection.cursor() as cursor:
        devis = lire_dommages(cursor, iddevis)
    if not devis:
        return Response({"error": f"Devis Dommages {iddevis} introuvable."}, status=status.HTTP_404_NOT_FOUND)
    return Response(devis)


def risque_dommages(cursor, iddevis):
    """Catégorie et description du risque d'un devis Dommages, pour les documents imprimés."""
    ligne = _une_ligne(
        cursor,
        """
        SELECT dd.idtarif, t.libelle, cd.saisie
        FROM stddevisdetail dd
        LEFT JOIN stdtarif t ON t.idtarif = dd.idtarif
        LEFT JOIN stdcomplementdevisdetaildommage cd ON cd.iddevisdetail = dd.iddevisdetail
        WHERE dd.iddevis = %s
        ORDER BY dd.iddevisdetail, cd.idcomplement DESC
        LIMIT 1
        """,
        [iddevis],
    )
    if not ligne:
        return None
    saisie = ligne[2] if isinstance(ligne[2], dict) else (json.loads(ligne[2]) if ligne[2] else {})
    valeurs = (saisie or {}).get("risque") or {}
    reglage = DommageCategorie.objects.filter(IdTarif=ligne[0]).first()
    champs = [c for c in (reglage.ChampsRisque if reglage else []) if isinstance(c, dict) and c.get("Cle")]
    libelles = {c["Cle"]: c.get("Libelle") or c["Cle"] for c in champs}
    types = {c["Cle"]: c.get("Type") for c in champs}
    lignes = []
    for cle, valeur in valeurs.items():
        if not str(valeur or "").strip():
            continue
        if types.get(cle) == "date":
            try:
                valeur = datetime.strptime(str(valeur)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                pass
        elif types.get(cle) == "montant" and re.fullmatch(r"\d+", str(valeur).strip()):
            valeur = f"{int(valeur):,}".replace(",", " ")
        lignes.append({"libelle": libelles.get(cle, cle.replace("_", " ").capitalize()), "valeur": str(valeur)})
    ordre = list(libelles)
    lignes.sort(key=lambda l: next((i for i, c in enumerate(ordre) if libelles[c] == l["libelle"]), 99))
    # Textes de la fiche de cotation (Réglages Dommages), une ligne par élément pour les listes
    fiche = {
        "objet_garantie": (reglage.ObjetGarantie if reglage else "") or "",
        "contre_garanties": [l.strip() for l in ((reglage.ContreGaranties if reglage else "") or "").splitlines() if l.strip()],
        "exclusions": [l.strip() for l in ((reglage.Exclusions if reglage else "") or "").splitlines() if l.strip()],
    }
    return {"categorie": ligne[1] or "", "description": lignes, "fiche": fiche,
            "valeurs": {c: valeurs.get(c) for c in libelles if valeurs.get(c)}}
