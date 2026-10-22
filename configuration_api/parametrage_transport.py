"""
Réglages Transport hors GUCE dans l'admin (Réglages par branche > Transport) : ce qui fixe la cotation.

- Garanties (lephare_transport_garantie) : libellé, description, garantie de base ou extension, sous-garantie du
  référentiel, taux proposé par mode de transport (vide : saisi à la cotation), taux minimum, ordre, active.
- Modes de transport (lephare_transport_mode) : libellé, document et moyen de transport demandés, modes de
  chargement proposés, actif. La catégorie (stdtarif 6xx) est fixe.
- Primes minimums, coûts de police et taxe (paramètres transport.*, groupe transport_tarif) et listes de saisie
  (groupe transport_listes) : route générale des paramètres (parametrage.py).
Lus par production/views_transport_hors_guce.py. Lecture pour tout utilisateur connecté, modification réservée aux
administrateurs (droit tarifs.update), chaque modification inscrite au journal d'audit.
"""

import re
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import ParametreGeneral, TransportGarantie, TransportMode
from .parametrage import ErreurParametrage, _auteur, _journal, _parametre_json, _reponse_erreur, _texte
from .views_grilles_voyage import AUTHENTIFICATION, EstAdministrateur

GROUPES_PARAMETRES = ("transport", "transport_tarif", "transport_listes")


def _taux(valeur, libelle):
    """Taux en % (texte enregistré) ou None si vide."""
    texte = str(valeur if valeur is not None else "").strip().replace(",", ".")
    if texte == "":
        return None
    try:
        nombre = Decimal(texte)
    except InvalidOperation as erreur:
        raise ErreurParametrage(f"{libelle} : taux attendu.") from erreur
    if nombre <= 0 or nombre > 100:
        raise ErreurParametrage(f"{libelle} : taux compris entre 0 et 100 %.")
    return format(nombre.normalize(), "f")


def _garantie_json(g, sous_garanties=None):
    return {
        "Code": g.Code, "Groupe": g.Groupe, "Libelle": g.Libelle, "Description": g.Description,
        "CodeSousGarantie": g.CodeSousGarantie,
        "LibelleSousGarantie": (sous_garanties or {}).get(g.CodeSousGarantie, ""),
        "Taux": g.Taux or {}, "TauxMinimum": g.TauxMinimum, "Ordre": g.Ordre, "Active": g.Active,
        "ModifiePar": g.ModifiePar, "DateModification": g.DateModification.isoformat() if g.DateModification else None,
    }


def _mode_json(m):
    return {
        "Code": m.Code, "Libelle": m.Libelle, "CodeCategorie": m.CodeCategorie, "Document": m.Document,
        "Moyen": m.Moyen, "Chargements": m.Chargements or [], "Ordre": m.Ordre, "Actif": m.Actif,
    }


def _sous_garanties():
    """Sous-garanties du référentiel proposées pour une garantie Transport : {code: libellé}."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT codesousgarantie, libellesousgarantie FROM stdsousgarantie "
            "WHERE active AND (saisietransport OR codesousgarantie = ANY(%s)) ORDER BY libellesousgarantie",
            [list(TransportGarantie.objects.values_list("CodeSousGarantie", flat=True))],
        )
        return dict(cursor.fetchall())


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def transport(request):
    """GET /api/parametrage/transport/ : garanties, modes, paramètres et sous-garanties disponibles."""
    sous_garanties = _sous_garanties()
    return Response({
        "Garanties": [_garantie_json(g, sous_garanties) for g in TransportGarantie.objects.all()],
        "Modes": [_mode_json(m) for m in TransportMode.objects.all()],
        "Parametres": [_parametre_json(p) for p in ParametreGeneral.objects.filter(Groupe__in=GROUPES_PARAMETRES)],
        "SousGaranties": [{"Code": c, "Libelle": l} for c, l in sous_garanties.items()],
    })


@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def garanties(request):
    """PUT /api/parametrage/transport/garanties/ {Garanties: [...]} : liste complète (ajouts, modifications ; une
    garantie déjà utilisée par des devis se désactive, elle ne se supprime pas)."""
    lignes = request.data.get("Garanties")
    if not isinstance(lignes, list) or not lignes:
        return _reponse_erreur(ErreurParametrage("Garanties : liste attendue."))
    modes = set(TransportMode.objects.values_list("Code", flat=True))
    sous_garanties = _sous_garanties()
    existantes = {g.Code: g for g in TransportGarantie.objects.all()}
    avant = [_garantie_json(g) for g in existantes.values()]
    vues = set()
    try:
        nouvelles = []
        for ordre, ligne in enumerate(lignes, start=1):
            if not isinstance(ligne, dict):
                raise ErreurParametrage("Garanties : ligne invalide.")
            libelle = _texte(ligne.get("Libelle"), 80, "Libellé de la garantie", obligatoire=True)
            code = str(ligne.get("Code") or "").strip().upper()
            if not code:
                code = re.sub(r"[^A-Z0-9]+", "_", libelle.upper().encode("ascii", "ignore").decode()).strip("_")[:30] or f"GARANTIE_{ordre}"
            if code in vues:
                raise ErreurParametrage(f"Garantie « {libelle} » : en double.")
            vues.add(code)
            groupe = str(ligne.get("Groupe") or "")
            if groupe not in ("BASE", "EXTENSION"):
                raise ErreurParametrage(f"{libelle} : garantie de base ou extension ?")
            code_sg = str(ligne.get("CodeSousGarantie") or "").strip()
            if code_sg not in sous_garanties:
                raise ErreurParametrage(f"{libelle} : choisissez la garantie du référentiel à laquelle elle se rattache.")
            taux = {}
            for mode, valeur in (ligne.get("Taux") or {}).items():
                if mode in modes:
                    taux[mode] = _taux(valeur, f"{libelle} ({mode.lower()})")
            minimum = bool(ligne.get("TauxMinimum"))
            if minimum and not any(taux.values()):
                raise ErreurParametrage(f"{libelle} : un taux minimum demande au moins un taux.")
            nouvelles.append(TransportGarantie(
                Code=code, Groupe=groupe, Libelle=libelle, Description=_texte(ligne.get("Description"), 600, f"{libelle} : description"),
                CodeSousGarantie=code_sg, Taux=taux, TauxMinimum=minimum, Ordre=ordre, Active=bool(ligne.get("Active", True)),
                ModifiePar=_auteur(request),
            ))
        if not any(g.Groupe == "BASE" and g.Active for g in nouvelles):
            raise ErreurParametrage("Gardez au moins une garantie de base active.")
        retirees = [c for c in existantes if c not in vues]
        if retirees:
            raise ErreurParametrage("Une garantie ne se supprime pas : désactivez-la (les devis existants la gardent).")
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    with transaction.atomic():
        for g in nouvelles:
            g.save()
    apres = [_garantie_json(g, sous_garanties) for g in TransportGarantie.objects.all()]
    _journal(request, "Garanties Transport modifiées", {"avant": avant, "apres": apres})
    return Response({"Garanties": apres})


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def mode(request, code):
    """PATCH /api/parametrage/transport/modes/<code>/ {Libelle, Document, Moyen, Chargements, Actif, Ordre}."""
    ligne = TransportMode.objects.filter(Code=code).first()
    if not ligne:
        return Response({"error": f"Mode {code} inconnu."}, status=status.HTTP_404_NOT_FOUND)
    avant = _mode_json(ligne)
    try:
        if "Libelle" in request.data:
            ligne.Libelle = _texte(request.data["Libelle"], 60, "Libellé", obligatoire=True)
        if "Document" in request.data:
            ligne.Document = _texte(request.data["Document"], 80, "Document de transport")
        if "Moyen" in request.data:
            ligne.Moyen = _texte(request.data["Moyen"], 80, "Moyen de transport")
        if "Chargements" in request.data:
            valeurs = request.data["Chargements"]
            if isinstance(valeurs, str):
                valeurs = valeurs.splitlines()
            chargements = [_texte(v, 80, "Mode de chargement") for v in (valeurs or []) if str(v).strip()]
            if not chargements:
                raise ErreurParametrage("Gardez au moins un mode de chargement.")
            ligne.Chargements = list(dict.fromkeys(chargements))
        if "Actif" in request.data:
            ligne.Actif = bool(request.data["Actif"])
            if not ligne.Actif and not TransportMode.objects.exclude(Code=code).filter(Actif=True).exists():
                raise ErreurParametrage("Gardez au moins un mode de transport actif.")
        if "Ordre" in request.data:
            ligne.Ordre = max(0, min(99, int(request.data["Ordre"] or 0)))
    except (ErreurParametrage, ValueError) as erreur:
        return _reponse_erreur(erreur if isinstance(erreur, ErreurParametrage) else ErreurParametrage("Ordre : nombre entier attendu."))
    ligne.ModifiePar = _auteur(request)
    ligne.save()
    apres = _mode_json(ligne)
    _journal(request, f"Mode de transport « {ligne.Libelle} » modifié", {"avant": avant, "apres": apres})
    return Response(apres)
