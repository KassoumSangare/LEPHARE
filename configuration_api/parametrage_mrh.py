"""
Réglages Multirisque Habitation dans l'admin (Réglages par branche > Multirisque Habitation) : tables du tarif MRH
lues par production/services/mrh_calcul_service.py, jusqu'ici modifiables seulement en base.

- Usages d'habitation (stdmrh_usage_habitation) et leurs paramètres de calcul (stdmrh_parametres_calcul) :
  prime de base = valeur du bâtiment × coefficient + valeur du contenu × coefficient + loyer mensuel × 12 × 15 ×
  coefficient + capital RVT × coefficient + forfait fixe, le tout × coefficient de réduction. Les coefficients sont
  échangés en ‰ (stockés en fraction : 1 ‰ = 0,001) ; la formule affichée est recomposée à chaque modification.
- Garanties de chaque usage (stdmrh_sous_garantie_usage) : comprises ou facultatives, part de la prime de base
  (les parts des garanties comprises font 100 %), ordre, active.
- Options (stdmrh_option) : ajustement en ‰ de la prime de base (TYPE1), en % de la prime de la garantie (TYPE2)
  ou forfait (FORFAIT), en plus ou en moins ; options proposées par usage (stdmrh_option_usage).
- Garanties facultatives à prime forfaitaire (stdmrh_sous_garantie_forfait).
Lecture pour tout utilisateur connecté, modification réservée aux administrateurs (droit tarifs.update), chaque
modification inscrite au journal d'audit.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import Option, OptionUsage, SousGarantieForfait, UsageHabitation
from .parametrage import ErreurParametrage, _journal, _reponse_erreur, _texte
from .views_grilles_voyage import AUTHENTIFICATION, EstAdministrateur

MILLE = Decimal("1000")
# (champ, libellé, champ « requis ») des capitaux de la prime de base
CAPITAUX = [
    ("coeff_valeur_batiment", "Valeur bâtiment", "param_valeur_batiment_requis"),
    ("coeff_valeur_contenu", "Valeur contenu", "param_valeur_contenu_requis"),
    ("coeff_loyer", "Loyer × 12 × 15", "param_loyer_requis"),
    ("coeff_capital_rvt", "Capital RVT", "param_capital_rvt_requis"),
]


def _nombre(valeur):
    return float(valeur) if valeur is not None else None


def _decimal(valeur, libelle, minimum=Decimal("0"), maximum=None, vide_permis=True):
    texte = str(valeur if valeur is not None else "").strip().replace(" ", "").replace(",", ".")
    if texte == "":
        if vide_permis:
            return None
        raise ErreurParametrage(f"{libelle} : valeur obligatoire.")
    try:
        nombre = Decimal(texte)
    except InvalidOperation as erreur:
        raise ErreurParametrage(f"{libelle} : nombre attendu.") from erreur
    if nombre < minimum or (maximum is not None and nombre > maximum):
        raise ErreurParametrage(f"{libelle} : entre {minimum} et {maximum}." if maximum is not None else f"{libelle} : {minimum} au moins.")
    return nombre


def _pour_mille(fraction):
    return _nombre(fraction * MILLE) if fraction is not None else None


def _lisible(nombre):
    texte = format(Decimal(nombre).normalize(), "f")
    return texte.replace(".", ",")


def formule_texte(p):
    """Formule affichée à la saisie, recomposée depuis les coefficients (« (Valeur bâtiment × 1‰ + …) × 0,95 »)."""
    termes = [f"{libelle} × {_lisible(getattr(p, champ) * MILLE)}‰" for champ, libelle, _ in CAPITAUX if getattr(p, champ)]
    if p.forfait_fixe:
        termes.append(f"{int(p.forfait_fixe):,}".replace(",", " "))
    texte = " + ".join(termes) or "0"
    if p.coeff_reduction and p.coeff_reduction != 1:
        texte = f"({texte}) × {_lisible(p.coeff_reduction)}" if len(termes) > 1 else f"{texte} × {_lisible(p.coeff_reduction)}"
    return texte


def _usage_json(u):
    p = getattr(u, "parametres", None)
    garanties = [{
        "Code": g.sous_garantie.code, "Libelle": g.sous_garantie.libelle, "Type": g.sous_garantie.type,
        "Obligatoire": g.obligatoire, "TauxRepartition": _nombre(g.taux_repartition), "Ordre": g.ordre_affichage, "Actif": g.actif,
        "PrimeForfait": _nombre(getattr(getattr(g.sous_garantie, "forfait", None), "prime_nette", None)),
    } for g in u.sous_garanties_liees.select_related("sous_garantie").order_by("ordre_affichage")]
    options = {o.option_id: o.actif for o in u.options_applicables.all()}
    return {
        "Code": u.code, "Libelle": u.libelle, "Description": u.description or "", "QualiteAssure": u.get_qualite_assure_display(),
        "Actif": u.actif, "IdOffre": u.offre_id, "Offre": u.offre.LibelleOffre if u.offre_id else "",
        "Parametres": {
            **{champ: _pour_mille(getattr(p, champ)) for champ, _, _ in CAPITAUX},
            **{requis: getattr(p, requis) for _, _, requis in CAPITAUX},
            "coeff_reduction": _nombre(p.coeff_reduction), "forfait_fixe": _nombre(p.forfait_fixe),
            "formule_texte": p.formule_texte or formule_texte(p),
        } if p else None,
        "Garanties": garanties,
        "Options": options,
    }


def _option_json(o):
    return {
        "Code": o.code, "Libelle": o.libelle, "Description": o.description or "", "TypeAjustement": o.type_ajustement,
        "TauxAjustement": _nombre(o.taux_ajustement), "MontantForfait": _nombre(o.montant_forfait),
        "Signe": o.signe_ajustement, "GarantieCible": o.sous_garantie_cible.libelle if o.sous_garantie_cible_id else "",
        "Actif": o.actif,
    }


def _usages():
    return UsageHabitation.objects.select_related("offre", "parametres").order_by("qualite_assure", "libelle")


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def mrh(request):
    """GET /api/parametrage/mrh/ : usages (paramètres de calcul, garanties, options) et options."""
    return Response({
        "Usages": [_usage_json(u) for u in _usages()],
        "Options": [_option_json(o) for o in Option.objects.select_related("sous_garantie_cible").order_by("libelle")],
        "Forfaits": [{"Code": f.sous_garantie.code, "Libelle": f.sous_garantie.libelle, "PrimeNette": _nombre(f.prime_nette), "Actif": f.actif}
                     for f in SousGarantieForfait.objects.select_related("sous_garantie").order_by("sous_garantie__libelle")],
    })


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def usage(request, code):
    """PATCH /api/parametrage/mrh/usages/<code>/ {Libelle, Description, Actif, Parametres: {coeff_* en ‰,
    coeff_reduction, forfait_fixe, param_*_requis}, Garanties: [{Code, Obligatoire, TauxRepartition, Ordre, Actif}],
    Options: {code: actif}}."""
    u = UsageHabitation.objects.select_related("parametres", "offre").filter(code=code).first()
    if not u:
        return Response({"error": f"Usage {code} inconnu."}, status=status.HTTP_404_NOT_FOUND)
    avant = _usage_json(u)
    d = request.data
    try:
        with transaction.atomic():
            if "Libelle" in d:
                u.libelle = _texte(d["Libelle"], 200, "Libellé de l'usage", obligatoire=True)
            if "Description" in d:
                u.description = _texte(d["Description"], 600, "Description")
            if "Actif" in d:
                u.actif = bool(d["Actif"])
            u.save()
            if isinstance(d.get("Parametres"), dict):
                p = u.parametres
                v = d["Parametres"]
                for champ, libelle, requis in CAPITAUX:
                    if champ in v:
                        pour_mille = _decimal(v[champ], f"Coefficient {libelle.lower()}", maximum=MILLE)
                        setattr(p, champ, (pour_mille / MILLE) if pour_mille else None)
                    if requis in v:
                        setattr(p, requis, bool(v[requis]))
                if "coeff_reduction" in v:
                    p.coeff_reduction = _decimal(v["coeff_reduction"], "Coefficient de réduction", maximum=Decimal("5")) or Decimal("1")
                if "forfait_fixe" in v:
                    p.forfait_fixe = _decimal(v["forfait_fixe"], "Forfait fixe") or Decimal("0")
                if not any(getattr(p, champ) for champ, _, _ in CAPITAUX) and not p.forfait_fixe:
                    raise ErreurParametrage("Prime de base : au moins un coefficient ou un forfait fixe.")
                for champ, libelle, requis in CAPITAUX:
                    if getattr(p, champ) and not getattr(p, requis):
                        raise ErreurParametrage(f"{libelle} : à demander à la saisie dès qu'un coefficient lui est appliqué.")
                p.formule_texte = formule_texte(p)
                p.save()
            if isinstance(d.get("Garanties"), list):
                liens = {g.sous_garantie_id: g for g in u.sous_garanties_liees.all()}
                for ligne in d["Garanties"]:
                    g = liens.get(str(ligne.get("Code") or ""))
                    if not g:
                        raise ErreurParametrage(f"Garantie {ligne.get('Code')} absente de cet usage.")
                    g.obligatoire = bool(ligne.get("Obligatoire"))
                    g.taux_repartition = _decimal(ligne.get("TauxRepartition"), f"{g.sous_garantie.libelle} : part", maximum=Decimal("100"))
                    g.ordre_affichage = int(ligne.get("Ordre") or g.ordre_affichage or 0)
                    g.actif = bool(ligne.get("Actif", True))
                    if g.obligatoire and g.taux_repartition is None:
                        raise ErreurParametrage(f"{g.sous_garantie.libelle} : part de la prime de base à renseigner (garantie comprise).")
                    g.save()
                total = sum((g.taux_repartition or 0) for g in u.sous_garanties_liees.filter(obligatoire=True, actif=True))
                if abs(total - 100) > Decimal("0.01"):
                    raise ErreurParametrage(f"Les parts des garanties comprises font {_lisible(total)} % : elles doivent faire 100 %.")
            if isinstance(d.get("Options"), dict):
                liens = {o.option_id: o for o in OptionUsage.objects.filter(usage=u)}
                for code_option, actif in d["Options"].items():
                    if code_option in liens:
                        liens[code_option].actif = bool(actif)
                        liens[code_option].save()
                    elif actif and Option.objects.filter(code=code_option).exists():
                        OptionUsage.objects.create(usage=u, option_id=code_option, actif=True)
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    except (TypeError, ValueError):
        return _reponse_erreur(ErreurParametrage("Ordre d'affichage : nombre entier attendu."))
    u = _usages().get(code=code)
    apres = _usage_json(u)
    _journal(request, f"Usage MRH « {u.libelle} » modifié", {"avant": avant, "apres": apres})
    return Response(apres)


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def option(request, code):
    """PATCH /api/parametrage/mrh/options/<code>/ {Libelle, TauxAjustement, MontantForfait, Signe, Actif}."""
    o = Option.objects.select_related("sous_garantie_cible").filter(code=code).first()
    if not o:
        return Response({"error": f"Option {code} inconnue."}, status=status.HTTP_404_NOT_FOUND)
    avant = _option_json(o)
    d = request.data
    try:
        if "Libelle" in d:
            o.libelle = _texte(d["Libelle"], 200, "Libellé de l'option", obligatoire=True)
        if "TauxAjustement" in d and o.type_ajustement != "FORFAIT":
            maximum = MILLE if o.type_ajustement == "TYPE1" else Decimal("100")
            o.taux_ajustement = _decimal(d["TauxAjustement"], "Taux d'ajustement", maximum=maximum, vide_permis=False)
        if "MontantForfait" in d and o.type_ajustement == "FORFAIT":
            o.montant_forfait = _decimal(d["MontantForfait"], "Montant forfaitaire", vide_permis=False)
        if "Signe" in d:
            if d["Signe"] not in ("+", "-"):
                raise ErreurParametrage("Signe : majoration (+) ou réduction (-).")
            o.signe_ajustement = d["Signe"]
        if "Actif" in d:
            o.actif = bool(d["Actif"])
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    o.save()
    apres = _option_json(o)
    _journal(request, f"Option MRH « {o.libelle} » modifiée", {"avant": avant, "apres": apres})
    return Response(apres)


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def forfait(request, code):
    """PATCH /api/parametrage/mrh/forfaits/<code>/ {PrimeNette, Actif} : garantie facultative à prime forfaitaire."""
    f = SousGarantieForfait.objects.select_related("sous_garantie").filter(sous_garantie_id=code).first()
    if not f:
        return Response({"error": f"Forfait {code} inconnu."}, status=status.HTTP_404_NOT_FOUND)
    avant = {"PrimeNette": _nombre(f.prime_nette), "Actif": f.actif}
    try:
        if "PrimeNette" in request.data:
            f.prime_nette = _decimal(request.data["PrimeNette"], "Prime nette forfaitaire", vide_permis=False)
        if "Actif" in request.data:
            f.actif = bool(request.data["Actif"])
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    f.save()
    apres = {"Code": code, "Libelle": f.sous_garantie.libelle, "PrimeNette": _nombre(f.prime_nette), "Actif": f.actif}
    _journal(request, f"Forfait MRH « {f.sous_garantie.libelle} » modifié", {"avant": avant, "apres": apres})
    return Response(apres)
