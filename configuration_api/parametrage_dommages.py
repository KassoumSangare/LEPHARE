"""
Réglages Dommages (produit 9) dans l'admin : ce que l'écran de devis Dommages propose.

- Catégories (stdtarif 4xx) : proposée ou non à la saisie, ordre, description, prime au prorata,
  description du risque demandée (lephare_dommage_categorie).
- Imprimés : tableau des garanties en annexe de la cotation ou non, référence de la facture de prime,
  documents de production imprimés depuis le contrat (ex. « Garantie de soumission » d'une caution,
  lephare_dommage_document).
- Garanties de chaque catégorie, par compagnie : garanties de l'offre (stdoffregarantie, table URANUS
  lue par le calcul), franchise, taux de prime proposé et garantie obligatoire (lephare_dommage_garantie),
  taxe d'enregistrement du produit 9 créée si la garantie n'en a pas (stdtauxtaxegarantieproduit ;
  une taxe existante se modifie dans « Taxes », avec sa période de validité).

Lecture pour tout utilisateur connecté, modification réservée aux administrateurs, chaque modification
inscrite au journal d'audit.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import DommageCategorie, DommageDocument, DommageGarantie
from .parametrage import ErreurParametrage, _journal, _reponse_erreur, _texte
from .views_grilles_voyage import AUTHENTIFICATION, EstAdministrateur

ID_PRODUIT_DOMMAGES = 9
CHAMPS_MAXIMUM = 15
OPTIONS_MAXIMUM = 30
# Textes de la fiche de cotation imprimée, réglables par catégorie
TEXTES_FICHE = ("ObjetGarantie", "ContreGaranties", "Exclusions")
MOTIF_CLE = re.compile(r"^[a-z0-9_]{1,40}$")
DOCUMENTS_MAXIMUM = 10
TYPES_CHAMP = {code for code, _ in DommageCategorie.TYPES_CHAMP}


def _nombre(valeur):
    return float(valeur) if valeur is not None else None


def _decimal(valeur, champ, maximum=None, obligatoire=False):
    if valeur is None or str(valeur).strip() == "":
        if obligatoire:
            raise ErreurParametrage(f"{champ} : valeur à renseigner.")
        return None
    try:
        nombre = Decimal(str(valeur).replace(" ", "").replace(",", "."))
    except InvalidOperation as erreur:
        raise ErreurParametrage(f"{champ} : nombre attendu.") from erreur
    if nombre < 0 or (maximum is not None and nombre > maximum):
        raise ErreurParametrage(f"{champ} : entre 0 et {maximum}." if maximum is not None else f"{champ} : valeur positive attendue.")
    return nombre


def _offre_du_tarif(cursor, id_tarif):
    cursor.execute(
        """
        SELECT t.libelle, (SELECT o.idoffre FROM stdoffre o WHERE o.idtarif = t.idtarif ORDER BY o.actif DESC, o.idoffre LIMIT 1)
        FROM stdtarif t WHERE t.idtarif = %s AND t.codecategorie LIKE '4%%'
        """,
        [id_tarif],
    )
    ligne = cursor.fetchone()
    if not ligne:
        raise ErreurParametrage("Catégorie hors de la branche Dommages.")
    if not ligne[1]:
        raise ErreurParametrage(f"Aucune offre n'est rattachée à la catégorie « {ligne[0]} » (voir « Offres »).")
    return ligne[0], ligne[1]


def _garanties_par_offre(cursor):
    """{(idoffre, idcompagnie): [garanties]} pour toutes les offres Dommages."""
    cursor.execute(
        """
        SELECT DISTINCT ON (og.idoffre, og.idcompagnie, og.idsousgarantie)
               og.idoffre, og.idcompagnie, og.idsousgarantie, sg.libellesousgarantie, sg.idgarantie, g.libellegarantie,
               og.tauxfranchise, og.franchiseminimum, og.franchisemaximum, og.ordreaffichage
        FROM stdoffregarantie og
        JOIN stdoffre o ON o.idoffre = og.idoffre
        JOIN stdtarif t ON t.idtarif = o.idtarif AND t.codecategorie LIKE '4%%'
        JOIN stdsousgarantie sg ON sg.idsousgarantie = og.idsousgarantie
        LEFT JOIN stdgarantie g ON g.idgarantie = sg.idgarantie
        ORDER BY og.idoffre, og.idcompagnie, og.idsousgarantie, og.idoffregarantie
        """
    )
    lignes = cursor.fetchall()
    reglages = {(r.IdOffre, r.IdCompagnie, r.IdSousGarantie): r for r in DommageGarantie.objects.all()}
    taxes = _taxes(cursor)
    resultat = {}
    for id_offre, id_cie, id_sg, libelle, id_g, libelle_g, tf, fmin, fmax, ordre in lignes:
        r = reglages.get((id_offre, id_cie, id_sg))
        resultat.setdefault((id_offre, id_cie), []).append({
            "IdSousGarantie": id_sg,
            "Libelle": libelle,
            "IdGarantie": id_g,
            "LibelleGarantie": libelle_g or "",
            "TauxFranchise": _nombre(tf) or 0,
            "FranchiseMinimum": _nombre(fmin) or 0,
            "FranchiseMaximum": _nombre(fmax) or 0,
            "Ordre": ordre or 0,
            "TauxTaxe": taxes.get(id_sg),
            "TauxDefaut": _nombre(r.TauxDefaut) if r and r.TauxDefaut is not None else None,
            "Obligatoire": bool(r and r.Obligatoire),
        })
    for liste in resultat.values():
        liste.sort(key=lambda g: (g["Ordre"], g["Libelle"]))
    return resultat


def _taxes(cursor):
    """Taux de taxe du produit 9 en vigueur aujourd'hui, par sous-garantie."""
    cursor.execute(
        """
        SELECT DISTINCT ON (idgarantie) idgarantie, tauxtaxe FROM stdtauxtaxegarantieproduit
        WHERE idproduit = %s AND %s BETWEEN debutvalidite AND finvalidite
        ORDER BY idgarantie, debutvalidite DESC
        """,
        [ID_PRODUIT_DOMMAGES, date.today()],
    )
    return {i: float(t) for i, t in cursor.fetchall()}


def _document_json(d):
    return {
        "Id": d.id, "IdCompagnie": d.IdCompagnie, "Titre": d.Titre, "ConditionChamp": d.ConditionChamp,
        "ConditionValeur": d.ConditionValeur, "Corps": d.Corps, "Signataire": d.Signataire,
        "MentionSignature": d.MentionSignature, "Actif": d.Actif, "Ordre": d.Ordre,
    }


def _categorie_json(ligne, reglage, garanties, compagnies, nb_devis, documents=()):
    id_tarif, libelle, code, id_offre, libelle_offre = ligne
    return {
        "IdTarif": id_tarif,
        "Libelle": libelle,
        "CodeCategorie": code,
        "IdOffre": id_offre or 0,
        "LibelleOffre": libelle_offre or "",
        "SaisieOuverte": reglage.SaisieOuverte if reglage else True,
        "Ordre": reglage.Ordre if reglage else 999,
        "Description": reglage.Description if reglage else "",
        "Prorata": reglage.Prorata if reglage else False,
        "ChampsRisque": reglage.ChampsRisque if reglage else [],
        "ObjetGarantie": reglage.ObjetGarantie if reglage else "",
        "ContreGaranties": reglage.ContreGaranties if reglage else "",
        "Exclusions": reglage.Exclusions if reglage else "",
        "AnnexeCotation": reglage.AnnexeCotation if reglage else True,
        "ReferenceFacture": reglage.ReferenceFacture if reglage else "",
        "Documents": [_document_json(d) for d in documents],
        "NbDevis": nb_devis.get(id_tarif, 0),
        # Garanties par compagnie : seulement les compagnies qui en ont pour cette offre
        "Compagnies": {
            str(id_cie): garanties.get((id_offre, id_cie), [])
            for id_cie in compagnies if (id_offre, id_cie) in garanties
        },
    }


def _lire_tout(cursor):
    cursor.execute(
        """
        SELECT t.idtarif, t.libelle, t.codecategorie,
               (SELECT o.idoffre FROM stdoffre o WHERE o.idtarif = t.idtarif ORDER BY o.actif DESC, o.idoffre LIMIT 1),
               (SELECT o.libelleoffre FROM stdoffre o WHERE o.idtarif = t.idtarif ORDER BY o.actif DESC, o.idoffre LIMIT 1)
        FROM stdtarif t WHERE t.codecategorie LIKE '4%%' AND t.idtarif <> 0
        """
    )
    lignes = cursor.fetchall()
    cursor.execute("SELECT idcompagnie, raisonsociale FROM stdcompagnie WHERE idcompagnie <> 0 AND active ORDER BY raisonsociale")
    compagnies = cursor.fetchall()
    cursor.execute(
        """
        SELECT dd.idtarif, COUNT(DISTINCT d.iddevis) FROM stddevis d
        JOIN stddevisdetail dd ON dd.iddevis = d.iddevis
        WHERE d.idproduit = %s GROUP BY dd.idtarif
        """,
        [ID_PRODUIT_DOMMAGES],
    )
    nb_devis = dict(cursor.fetchall())
    garanties = _garanties_par_offre(cursor)
    reglages = {c.IdTarif: c for c in DommageCategorie.objects.all()}
    documents = {}
    for d in DommageDocument.objects.all():
        documents.setdefault(d.IdTarif, []).append(d)
    ids_compagnies = [c[0] for c in compagnies]
    categories = [_categorie_json(l, reglages.get(l[0]), garanties, ids_compagnies, nb_devis, documents.get(l[0], []))
                  for l in lignes]
    categories.sort(key=lambda c: (c["Ordre"], c["Libelle"]))
    return categories, compagnies


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def dommages(request):
    """GET /api/parametrage/dommages/ : catégories, garanties par compagnie et garanties disponibles."""
    with connection.cursor() as cursor:
        categories, compagnies = _lire_tout(cursor)
        taxes = _taxes(cursor)
        cursor.execute(
            """
            SELECT sg.idsousgarantie, sg.codesousgarantie, sg.libellesousgarantie, sg.idgarantie, g.libellegarantie, sg.saisierd
            FROM stdsousgarantie sg LEFT JOIN stdgarantie g ON g.idgarantie = sg.idgarantie
            WHERE sg.active AND sg.idsousgarantie <> 0
            ORDER BY sg.libellesousgarantie
            """
        )
        sous_garanties = [
            {"IdSousGarantie": i, "Code": code, "Libelle": lib, "IdGarantie": id_g, "LibelleGarantie": lib_g or "",
             "SaisieRd": bool(rd), "TauxTaxe": taxes.get(i)}
            for i, code, lib, id_g, lib_g, rd in cursor.fetchall()
        ]
    return Response({
        "Categories": categories,
        "Compagnies": [{"IdCompagnie": i, "RaisonSociale": n} for i, n in compagnies],
        "SousGaranties": sous_garanties,
        "TypesChamp": [{"Code": c, "Libelle": l} for c, l in DommageCategorie.TYPES_CHAMP],
    })


def _champs_risque(valeur):
    if not isinstance(valeur, list):
        raise ErreurParametrage("Description du risque : liste de champs attendue.")
    if len(valeur) > CHAMPS_MAXIMUM:
        raise ErreurParametrage(f"Description du risque : {CHAMPS_MAXIMUM} champs au plus.")
    champs, cles = [], set()
    for i, champ in enumerate(valeur, start=1):
        if not isinstance(champ, dict):
            raise ErreurParametrage(f"Champ {i} : fiche attendue.")
        libelle = _texte(champ.get("Libelle"), 80, f"Champ {i} : libellé", obligatoire=True)
        cle = str(champ.get("Cle") or "").strip()
        if not MOTIF_CLE.match(cle):
            raise ErreurParametrage(f"« {libelle} » : identifiant technique invalide (lettres minuscules, chiffres et _).")
        if cle in cles:
            raise ErreurParametrage(f"« {libelle} » : identifiant « {cle} » déjà utilisé par un autre champ.")
        cles.add(cle)
        type_ = champ.get("Type") or "texte"
        if type_ not in TYPES_CHAMP:
            raise ErreurParametrage(f"« {libelle} » : type de champ inconnu.")
        propre = {"Cle": cle, "Libelle": libelle, "Type": type_, "Obligatoire": bool(champ.get("Obligatoire"))}
        if type_ == "liste":
            options = champ.get("Options")
            if isinstance(options, str):
                options = options.splitlines()
            options = [str(o).strip()[:120] for o in (options or []) if str(o).strip()]
            options = list(dict.fromkeys(options))
            if not options:
                raise ErreurParametrage(f"« {libelle} » : indiquez les choix de la liste (un par ligne).")
            if len(options) > OPTIONS_MAXIMUM:
                raise ErreurParametrage(f"« {libelle} » : {OPTIONS_MAXIMUM} choix au plus.")
            propre["Options"] = options
        champs.append(propre)
    return champs


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def categorie(request, id_tarif):
    """PATCH /api/parametrage/dommages/categories/<idtarif>/ {SaisieOuverte, Ordre, Description, Prorata, ChampsRisque,
    ObjetGarantie, ContreGaranties, Exclusions, AnnexeCotation, ReferenceFacture}."""
    try:
        with connection.cursor() as cursor:
            libelle, _ = _offre_du_tarif(cursor, id_tarif)
        reglage = DommageCategorie.objects.filter(IdTarif=id_tarif).first() or DommageCategorie(IdTarif=id_tarif, Ordre=999)
        avant = {"SaisieOuverte": reglage.SaisieOuverte, "Ordre": reglage.Ordre, "Description": reglage.Description,
                 "Prorata": reglage.Prorata, "ChampsRisque": reglage.ChampsRisque,
                 "AnnexeCotation": reglage.AnnexeCotation, "ReferenceFacture": reglage.ReferenceFacture,
                 **{t: getattr(reglage, t) for t in TEXTES_FICHE}}
        donnees = request.data
        if "SaisieOuverte" in donnees:
            reglage.SaisieOuverte = bool(donnees["SaisieOuverte"])
        if "Prorata" in donnees:
            reglage.Prorata = bool(donnees["Prorata"])
        if "AnnexeCotation" in donnees:
            reglage.AnnexeCotation = bool(donnees["AnnexeCotation"])
        if "ReferenceFacture" in donnees:
            reglage.ReferenceFacture = _texte(donnees["ReferenceFacture"], 200, "Référence de la facture")
        if "Description" in donnees:
            reglage.Description = _texte(donnees["Description"], 400, "Description")
        if "Ordre" in donnees:
            try:
                reglage.Ordre = max(0, min(999, int(donnees["Ordre"])))
            except (TypeError, ValueError) as erreur:
                raise ErreurParametrage("Ordre : nombre entier attendu.") from erreur
        if "ChampsRisque" in donnees:
            reglage.ChampsRisque = _champs_risque(donnees["ChampsRisque"])
        for texte in TEXTES_FICHE:
            if texte in donnees:
                setattr(reglage, texte, _texte(donnees[texte], 2000, texte))
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    reglage.save()
    apres = {"SaisieOuverte": reglage.SaisieOuverte, "Ordre": reglage.Ordre, "Description": reglage.Description,
             "Prorata": reglage.Prorata, "ChampsRisque": reglage.ChampsRisque,
             "AnnexeCotation": reglage.AnnexeCotation, "ReferenceFacture": reglage.ReferenceFacture,
             **{t: getattr(reglage, t) for t in TEXTES_FICHE}}
    _journal(request, f"Dommages : catégorie « {libelle} » modifiée", {"idtarif": id_tarif, "avant": avant, "apres": apres})
    with connection.cursor() as cursor:
        categories, _ = _lire_tout(cursor)
    return Response(next(c for c in categories if c["IdTarif"] == id_tarif))


@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def documents(request, id_tarif):
    """PUT /api/parametrage/dommages/categories/<idtarif>/documents/ {Documents: [{Id?, IdCompagnie, Titre,
    ConditionChamp, ConditionValeur, Corps, Signataire, MentionSignature, Actif, Ordre}]} : remplace les documents
    de production de la catégorie (un document absent de la liste est supprimé)."""
    liste = request.data.get("Documents")
    try:
        if not isinstance(liste, list):
            raise ErreurParametrage("Documents : liste attendue.")
        if len(liste) > DOCUMENTS_MAXIMUM:
            raise ErreurParametrage(f"Documents : {DOCUMENTS_MAXIMUM} au plus par catégorie.")
        with connection.cursor() as cursor:
            libelle, _ = _offre_du_tarif(cursor, id_tarif)
            cursor.execute("SELECT idcompagnie FROM stdcompagnie WHERE idcompagnie <> 0")
            compagnies = {l[0] for l in cursor.fetchall()}
        reglage = DommageCategorie.objects.filter(IdTarif=id_tarif).first()
        cles = {c.get("Cle") for c in (reglage.ChampsRisque if reglage else []) if isinstance(c, dict)}
        existants = {d.id: d for d in DommageDocument.objects.filter(IdTarif=id_tarif)}
        propres = []
        for i, doc in enumerate(liste, start=1):
            if not isinstance(doc, dict):
                raise ErreurParametrage(f"Document {i} : fiche attendue.")
            titre = _texte(doc.get("Titre"), 120, f"Document {i} : titre", obligatoire=True)
            corps = _texte(doc.get("Corps"), 12000, f"« {titre} » : texte", obligatoire=True)
            try:
                id_compagnie = int(doc.get("IdCompagnie") or 0)
            except (TypeError, ValueError) as erreur:
                raise ErreurParametrage(f"« {titre} » : compagnie invalide.") from erreur
            if id_compagnie and id_compagnie not in compagnies:
                raise ErreurParametrage(f"« {titre} » : compagnie inconnue.")
            champ = str(doc.get("ConditionChamp") or "").strip()
            if champ and champ not in cles:
                raise ErreurParametrage(f"« {titre} » : la condition porte sur un champ du risque inconnu ({champ}).")
            try:
                id_doc = int(doc.get("Id") or 0)
                ordre = max(0, min(999, int(doc.get("Ordre") or i)))
            except (TypeError, ValueError) as erreur:
                raise ErreurParametrage(f"« {titre} » : nombre entier attendu.") from erreur
            if id_doc and id_doc not in existants:
                raise ErreurParametrage(f"« {titre} » : document introuvable (rechargez la page).")
            propres.append({
                "id": id_doc or None, "IdCompagnie": id_compagnie, "Titre": titre,
                "ConditionChamp": champ,
                "ConditionValeur": _texte(doc.get("ConditionValeur"), 120, f"« {titre} » : valeur de la condition") if champ else "",
                "Corps": corps,
                "Signataire": _texte(doc.get("Signataire"), 400, f"« {titre} » : signataire"),
                "MentionSignature": _texte(doc.get("MentionSignature"), 200, f"« {titre} » : mention sous la signature"),
                "Actif": bool(doc.get("Actif", True)), "Ordre": ordre,
            })
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    avant = [_document_json(d) for d in existants.values()]
    with transaction.atomic():
        gardes = set()
        for p in propres:
            document = existants.get(p.pop("id")) if p.get("id") else None
            if document is None:
                p.pop("id", None)
                document = DommageDocument(IdTarif=id_tarif)
            for cle, valeur in p.items():
                setattr(document, cle, valeur)
            document.save()
            gardes.add(document.id)
        DommageDocument.objects.filter(IdTarif=id_tarif).exclude(id__in=gardes).delete()
    apres = [_document_json(d) for d in DommageDocument.objects.filter(IdTarif=id_tarif)]
    _journal(request, f"Dommages : documents de production de « {libelle} » modifiés", {"idtarif": id_tarif, "avant": avant, "apres": apres})
    return Response({"Documents": apres})


@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def garanties_compagnie(request, id_tarif, id_compagnie):
    """PUT /api/parametrage/dommages/categories/<idtarif>/compagnies/<idcompagnie>/ {Garanties: [...]} :
    remplace les garanties de l'offre de la catégorie pour la compagnie."""
    liste = request.data.get("Garanties")
    try:
        if not isinstance(liste, list):
            raise ErreurParametrage("Garanties : liste attendue.")
        with connection.cursor() as cursor:
            libelle, id_offre = _offre_du_tarif(cursor, id_tarif)
            cursor.execute("SELECT raisonsociale FROM stdcompagnie WHERE idcompagnie = %s AND idcompagnie <> 0", [id_compagnie])
            ligne = cursor.fetchone()
            if not ligne:
                raise ErreurParametrage("Compagnie inconnue.")
            nom_compagnie = ligne[0]
            cursor.execute(
                "SELECT idsousgarantie, libellesousgarantie FROM stdsousgarantie WHERE idsousgarantie = ANY(%s)",
                [[int(g.get("IdSousGarantie") or 0) for g in liste if isinstance(g, dict)]],
            )
            libelles = dict(cursor.fetchall())
            taxes = _taxes(cursor)
        garanties, vues = [], set()
        for i, g in enumerate(liste, start=1):
            if not isinstance(g, dict):
                raise ErreurParametrage(f"Garantie {i} : fiche attendue.")
            try:
                id_sg = int(g.get("IdSousGarantie") or 0)
            except (TypeError, ValueError) as erreur:
                raise ErreurParametrage(f"Garantie {i} : identifiant invalide.") from erreur
            if id_sg not in libelles:
                raise ErreurParametrage(f"Garantie {i} : garantie inconnue.")
            if id_sg in vues:
                raise ErreurParametrage(f"« {libelles[id_sg]} » figure deux fois.")
            vues.add(id_sg)
            nom = libelles[id_sg]
            taxe = None
            if id_sg not in taxes:
                taxe = _decimal(g.get("TauxTaxe"), f"{nom} : taxe d'enregistrement (%)", maximum=Decimal("100"), obligatoire=True)
            try:
                ordre = max(0, min(999, int(g.get("Ordre") or 0)))
            except (TypeError, ValueError) as erreur:
                raise ErreurParametrage(f"{nom} : ordre invalide.") from erreur
            garanties.append({
                "id": id_sg,
                "nom": nom,
                "tf": _decimal(g.get("TauxFranchise"), f"{nom} : taux de franchise", maximum=Decimal("100")) or Decimal(0),
                "fmin": _decimal(g.get("FranchiseMinimum"), f"{nom} : franchise minimum") or Decimal(0),
                "fmax": _decimal(g.get("FranchiseMaximum"), f"{nom} : franchise maximum") or Decimal(0),
                "ordre": ordre,
                "taux": _decimal(g.get("TauxDefaut"), f"{nom} : taux de prime proposé", maximum=Decimal("100")),
                "obligatoire": bool(g.get("Obligatoire")),
                "taxe": taxe,
            })
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)

    with transaction.atomic(), connection.cursor() as cursor:
        avant = _garanties_par_offre(cursor).get((id_offre, id_compagnie), [])
        ids = [g["id"] for g in garanties]
        cursor.execute(
            "DELETE FROM stdoffregarantie WHERE idoffre = %s AND idcompagnie = %s AND NOT (idsousgarantie = ANY(%s))",
            [id_offre, id_compagnie, ids],
        )
        DommageGarantie.objects.filter(IdOffre=id_offre, IdCompagnie=id_compagnie).exclude(IdSousGarantie__in=ids).delete()
        for g in garanties:
            cursor.execute(
                """
                UPDATE stdoffregarantie SET tauxfranchise = %s, franchiseminimum = %s, franchisemaximum = %s, ordreaffichage = %s
                WHERE idoffre = %s AND idcompagnie = %s AND idsousgarantie = %s
                """,
                [g["tf"], g["fmin"], g["fmax"], g["ordre"], id_offre, id_compagnie, g["id"]],
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    """
                    INSERT INTO stdoffregarantie (idoffre, idsousgarantie, franchisemaximum, franchiseminimum, idcompagnie, tauxfranchise, ordreaffichage)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [id_offre, g["id"], g["fmax"], g["fmin"], id_compagnie, g["tf"], g["ordre"]],
                )
            DommageGarantie.objects.update_or_create(
                IdOffre=id_offre, IdCompagnie=id_compagnie, IdSousGarantie=g["id"],
                defaults={"TauxDefaut": g["taux"], "Obligatoire": g["obligatoire"]},
            )
            if g["taxe"] is not None:
                # Même période que les taxes Dommages d'origine ; une taxe existante se modifie dans « Taxes »
                cursor.execute(
                    """
                    INSERT INTO stdtauxtaxegarantieproduit (tauxtaxe, debutvalidite, finvalidite, idgarantie, idproduit, tauxtaxegroupe)
                    SELECT %s, DATE '2000-01-01', DATE '2050-12-31', %s, %s, 0
                    WHERE NOT EXISTS (SELECT 1 FROM stdtauxtaxegarantieproduit WHERE idgarantie = %s AND idproduit = %s)
                    """,
                    [g["taxe"], g["id"], ID_PRODUIT_DOMMAGES, g["id"], ID_PRODUIT_DOMMAGES],
                )
        apres = _garanties_par_offre(cursor).get((id_offre, id_compagnie), [])
    _journal(
        request,
        f"Dommages : garanties « {libelle} » chez {nom_compagnie} modifiées",
        {"idtarif": id_tarif, "idoffre": id_offre, "idcompagnie": id_compagnie, "avant": avant, "apres": apres},
    )
    return Response({"Garanties": apres})
