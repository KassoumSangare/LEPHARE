"""
Réglages Individuelle Accidents dans l'admin (Réglages par branche > Individuelle Accidents) : tarif NSIA ASSURANCES.

- Taux par classe d'activité (lephare_ia_taux_classe) : décès et invalidité permanente en ‰ du capital, frais
  médicaux en % du capital ; la classe vient de la profession de l'assuré (stdprofessionia.codeclasseassure).
  Lus par fn_calcul_prime_ia_nsia (v2).
- Accessoires selon la prime nette (lephare_ia_accessoire_tranche) : plafond de prime et montant ; ligne sans
  plafond = au-delà, pourcentage de la prime nette + montant. Lus par fn_get_accessoire_ia_nsia (v2), montant
  partagé à moitié entre la compagnie et le cabinet par fn_get_accessoire.
- Accessoires forfaitaires des offres (lephare_ia_accessoire_offre : CGA, CI-ÉNERGIES…), montant total partagé
  selon la part du cabinet de la compagnie (fiche compagnie > Reversements), lus par fn_get_accessoire.
- Clauses NSIA (âge, indemnité maximale) et réduction maximale : paramètres ia.* et devis.reduction_max_ia,
  route générale des paramètres (parametrage.py).
Lecture pour tout utilisateur connecté, modification réservée aux administrateurs (droit tarifs.update), chaque
modification inscrite au journal d'audit.
"""

from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import CompagnieDocument, IaAccessoireOffre, IaAccessoireTranche, IaTauxClasse
from .parametrage import ErreurParametrage, _auteur, _journal, _reponse_erreur, _texte
from .views_grilles_voyage import AUTHENTIFICATION, EstAdministrateur

ID_COMPAGNIE_NSIA = 1


def _nombre(valeur):
    return float(valeur) if valeur is not None else None


def _decimal(valeur, libelle, minimum=Decimal("0"), maximum=None, vide_permis=False):
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


def _professions():
    """{classe: (nombre de professions, exemples)} d'après les professions IA."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT TRIM(codeclasseassure), COUNT(*),
                   STRING_AGG(libelleprofession, ', ' ORDER BY libelleprofession) FILTER (WHERE libelleprofession IS NOT NULL)
            FROM stdprofessionia GROUP BY 1
            """
        )
        return {c: (n, (exemples or "")[:160]) for c, n, exemples in cursor.fetchall()}


def _classe_json(c, professions=None):
    nombre, exemples = (professions or {}).get(c.Classe, (0, ""))
    return {
        "Classe": c.Classe, "Libelle": c.Libelle, "TauxDeces": _nombre(c.TauxDeces), "TauxInvalidite": _nombre(c.TauxInvalidite),
        "TauxFraisMedicaux": _nombre(c.TauxFraisMedicaux), "Professions": nombre, "Exemples": exemples,
        "ModifiePar": c.ModifiePar, "DateModification": c.DateModification.isoformat() if c.DateModification else None,
    }


def _tranche_json(t):
    return {"Id": t.id, "PrimeMax": _nombre(t.PrimeMax), "Montant": _nombre(t.Montant), "TauxAuDela": _nombre(t.TauxAuDela)}


def _offres():
    lignes = list(IaAccessoireOffre.objects.all())
    with connection.cursor() as cursor:
        cursor.execute("SELECT idoffre, libelleoffre FROM stdoffre WHERE idoffre = ANY(%s)", [[o.IdOffre for o in lignes]])
        libelles = dict(cursor.fetchall())
    return [{"IdOffre": o.IdOffre, "Libelle": libelles.get(o.IdOffre, f"Offre {o.IdOffre}"), "Montant": _nombre(o.Montant), "Actif": o.Actif}
            for o in lignes]


def _parts():
    """Part du cabinet dans les accessoires, par compagnie qui l'a réglée (fiche compagnie > Reversements)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT idcompagnie, raisonsociale FROM stdcompagnie")
        noms = dict(cursor.fetchall())
    parts = []
    for d in CompagnieDocument.objects.all():
        part = (d.Reversement or {}).get("PartAccessoiresCourtier")
        if part not in (None, ""):
            parts.append({"IdCompagnie": d.IdCompagnie, "RaisonSociale": noms.get(d.IdCompagnie, ""), "Part": float(part)})
    return sorted(parts, key=lambda p: p["RaisonSociale"])


def _tranches():
    lignes = list(IaAccessoireTranche.objects.filter(IdCompagnie=ID_COMPAGNIE_NSIA))
    return sorted(lignes, key=lambda t: (t.PrimeMax is None, t.PrimeMax or 0))


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def ia(request):
    """GET /api/parametrage/ia/ : taux par classe et accessoires du tarif NSIA."""
    try:
        professions = _professions()
    except Exception:  # noqa: BLE001 - colonne absente dans une base ancienne : pas de décompte
        professions = {}
    return Response({
        "Compagnie": "NSIA ASSURANCES",
        "Classes": [_classe_json(c, professions) for c in IaTauxClasse.objects.filter(IdCompagnie=ID_COMPAGNIE_NSIA)],
        "Tranches": [_tranche_json(t) for t in _tranches()],
        "Offres": _offres(),
        "Parts": _parts(),
    })


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def classe(request, classe):
    """PATCH /api/parametrage/ia/classes/<classe>/ {Libelle, TauxDeces, TauxInvalidite, TauxFraisMedicaux}."""
    ligne = IaTauxClasse.objects.filter(IdCompagnie=ID_COMPAGNIE_NSIA, Classe=classe).first()
    if not ligne:
        return Response({"error": f"Classe {classe} inconnue."}, status=status.HTTP_404_NOT_FOUND)
    avant = _classe_json(ligne)
    try:
        if "Libelle" in request.data:
            ligne.Libelle = _texte(request.data["Libelle"], 120, "Libellé de la classe")
        for champ, libelle, maximum in (("TauxDeces", "Taux décès", Decimal("1000")),
                                        ("TauxInvalidite", "Taux invalidité permanente", Decimal("1000")),
                                        ("TauxFraisMedicaux", "Taux frais médicaux", Decimal("100"))):
            if champ in request.data:
                setattr(ligne, champ, _decimal(request.data[champ], libelle, maximum=maximum))
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    ligne.ModifiePar = _auteur(request)
    ligne.save()
    apres = _classe_json(ligne)
    _journal(request, f"Tarif IA NSIA, classe {classe} modifiée", {"avant": avant, "apres": apres})
    return Response(apres)


@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def tranches(request):
    """PUT /api/parametrage/ia/tranches/ {Tranches: [{PrimeMax, Montant, TauxAuDela}]} : grille complète."""
    lignes = request.data.get("Tranches")
    if not isinstance(lignes, list) or not lignes:
        return _reponse_erreur(ErreurParametrage("Tranches : liste attendue."))
    avant = [_tranche_json(t) for t in _tranches()]
    try:
        nouvelles, plafonds, au_dela = [], set(), 0
        for i, ligne in enumerate(lignes, start=1):
            plafond = _decimal(ligne.get("PrimeMax"), f"Tranche {i} : prime nette jusqu'à", minimum=Decimal("1"), vide_permis=True)
            montant = _decimal(ligne.get("Montant"), f"Tranche {i} : accessoires")
            taux = None
            if plafond is None:
                au_dela += 1
                taux = _decimal(ligne.get("TauxAuDela"), "Au-delà : pourcentage de la prime nette", maximum=Decimal("100"),
                                vide_permis=True) or Decimal("0")
            elif plafond in plafonds:
                raise ErreurParametrage(f"Deux tranches s'arrêtent à {plafond:,.0f} F.".replace(",", " "))
            plafonds.add(plafond)
            nouvelles.append(IaAccessoireTranche(IdCompagnie=ID_COMPAGNIE_NSIA, PrimeMax=plafond, Montant=montant,
                                                 TauxAuDela=taux, ModifiePar=_auteur(request)))
        if au_dela != 1:
            raise ErreurParametrage("Gardez une seule ligne « au-delà » (sans plafond) pour les primes les plus fortes.")
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    with transaction.atomic():
        IaAccessoireTranche.objects.filter(IdCompagnie=ID_COMPAGNIE_NSIA).delete()
        IaAccessoireTranche.objects.bulk_create(nouvelles)
    apres = [_tranche_json(t) for t in _tranches()]
    _journal(request, "Accessoires IA NSIA modifiés", {"avant": avant, "apres": apres})
    return Response({"Tranches": apres})


@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def offres(request):
    """PUT /api/parametrage/ia/offres/ {Offres: [{IdOffre, Montant, Actif}]} : accessoires forfaitaires des offres."""
    lignes = request.data.get("Offres")
    if not isinstance(lignes, list):
        return _reponse_erreur(ErreurParametrage("Offres : liste attendue."))
    existantes = {o.IdOffre: o for o in IaAccessoireOffre.objects.all()}
    avant = _offres()
    try:
        modifiees = []
        for ligne in lignes:
            o = existantes.get(int(ligne.get("IdOffre") or 0))
            if not o:
                raise ErreurParametrage(f"Offre {ligne.get('IdOffre')} inconnue.")
            o.Montant = _decimal(ligne.get("Montant"), f"Offre {o.IdOffre} : accessoire")
            o.Actif = bool(ligne.get("Actif", True))
            o.ModifiePar = _auteur(request)
            modifiees.append(o)
    except (ErreurParametrage, ValueError) as erreur:
        return _reponse_erreur(erreur if isinstance(erreur, ErreurParametrage) else ErreurParametrage("Offre : identifiant attendu."))
    with transaction.atomic():
        for o in modifiees:
            o.save()
    apres = _offres()
    _journal(request, "Accessoires forfaitaires des offres IA modifiés", {"avant": avant, "apres": apres})
    return Response({"Offres": apres})
