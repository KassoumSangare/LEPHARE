"""
Réglages Automobile dans l'admin : dépréciation des véhicules (tableau de la CIEAMI), et calcul de la valeur
vénale demandé par les écrans (saisie d'un véhicule, import du formulaire, renouvellement).

- Tableau (lephare_depreciation_classe) : une ligne par genre de véhicule, taux par âge en mois ; une case
  peut porter deux taux (« 30/35 »).
- Règles de classement (lephare_depreciation_regle) : ligne du tableau retenue pour un véhicule.
- Paramètres auto.depreciation.* : taux retenu entre deux, valeur au-delà de 10 ans, valeur minimum.
Le calcul lui-même est fait par la base (fn_lephare_depreciation), comme au renouvellement.

Lecture pour tout utilisateur connecté, modification réservée aux administrateurs (droit tarifs.update),
chaque modification inscrite au journal d'audit.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import AutoRegleGarantie, DepreciationClasse, DepreciationRegle, ParametreGeneral, PoolTpvTranche
from .parametrage import ErreurParametrage, _auteur, _cache, _journal, _parametre_json, _reponse_erreur, _texte, _valider_parametre
from .views_grilles_voyage import AUTHENTIFICATION, EstAdministrateur

PREFIXE = "auto.depreciation."
CHOIX_TAUX = {"plus_faible": "Le plus faible", "plus_eleve": "Le plus élevé", "moyenne": "La moyenne"}
VEHICULES_MAX = 500


def _lignes(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        colonnes = [c[0] for c in cursor.description]
        return [dict(zip(colonnes, ligne)) for ligne in cursor.fetchall()]


def _classe_json(c):
    return {
        "Code": c.Code, "Libelle": c.Libelle, "Kilometrage": c.Kilometrage, "Ordre": c.Ordre,
        "Taux": {k: [float(x) for x in v] for k, v in sorted((c.Taux or {}).items(), key=lambda kv: int(kv[0]))},
        "ModifiePar": c.ModifiePar,
        "DateModification": c.DateModification.isoformat() if c.DateModification else None,
    }


def _regle_json(r):
    return {
        "Id": r.id, "Ordre": r.Ordre, "Classe": r.Classe_id, "IdGenre": r.IdGenre, "IdTypeVehicule": r.IdTypeVehicule,
        "IdCarrosserie": r.IdCarrosserie, "CodeCategorie": r.CodeCategorie or "", "ChargeUtileSuperieureA": r.ChargeUtileSuperieureA,
    }


def regles_garanties_json():
    """Garanties admises selon l'âge du véhicule (lues aussi au démarrage de l'application)."""
    try:
        return [{
            "Id": r.id, "IdCompagnie": r.IdCompagnie, "IdSousGarantie": r.IdSousGarantie, "AgeMinimum": r.AgeMinimum,
            "AgeMaximum": r.AgeMaximum, "Categories": r.Categories or "", "Commentaire": r.Commentaire or "",
        } for r in AutoRegleGarantie.objects.all()]
    except Exception:  # noqa: BLE001 — base sans la migration configuration_api 0085
        return []


def _referentiels():
    return {
        "Compagnies": _lignes("SELECT idcompagnie AS id, raisonsociale AS libelle FROM stdcompagnie WHERE idcompagnie <> 0 AND COALESCE(active, TRUE) ORDER BY raisonsociale"),
        "SousGaranties": _lignes(
            "SELECT DISTINCT sg.idsousgarantie AS id, sg.libellesousgarantie AS libelle FROM stdsousgarantie sg "
            "JOIN stdoffregarantie og ON og.idsousgarantie = sg.idsousgarantie JOIN stdoffre o ON o.idoffre = og.idoffre "
            "JOIN stdtarif t ON t.idtarif = o.idtarif WHERE t.codecategorie LIKE '2%%' ORDER BY sg.libellesousgarantie"
        ),
        "Genres": _lignes("SELECT idgenre AS id, libellegenre AS libelle FROM stdgenrevehicule WHERE idgenre <> 0 ORDER BY libellegenre"),
        "Types": _lignes("SELECT id, libelletype AS libelle FROM stdtypevehicule WHERE id <> 0 ORDER BY libelletype"),
        "Carrosseries": _lignes("SELECT idcarrosserie AS id, libellecarrosserie AS libelle FROM stdcarrosserie ORDER BY libellecarrosserie"),
        "Categories": _lignes(
            "SELECT DISTINCT ON (codecategorie) codecategorie AS code, libelle FROM stdtarif "
            "WHERE codecategorie LIKE '2%%' ORDER BY codecategorie, idtarif"
        ),
    }


# ------------------------------------------------------------------ lecture
@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def depreciation(request):
    """GET /api/parametrage/auto/depreciation/ : tableau, règles, paramètres et listes de référence."""
    return Response({
        "Classes": [_classe_json(c) for c in DepreciationClasse.objects.all()],
        "Regles": [_regle_json(r) for r in DepreciationRegle.objects.all()],
        "Parametres": [_parametre_json(p) for p in ParametreGeneral.objects.filter(Cle__startswith=PREFIXE)],
        "ChoixTaux": [{"Code": k, "Libelle": v} for k, v in CHOIX_TAUX.items()],
        "ReglesGaranties": regles_garanties_json(),
        **_referentiels(),
    })


# ------------------------------------------------------------------ modifications
def _taux(valeur):
    """{mois: [taux] ou [min, max]} contrôlé ; accepte aussi « 30/35 » en texte par case."""
    if not isinstance(valeur, dict):
        raise ErreurParametrage("Taux : tableau attendu (âge en mois → taux).")
    propre = {}
    for cle, case in valeur.items():
        try:
            mois = int(str(cle).strip())
        except ValueError as erreur:
            raise ErreurParametrage(f"Âge « {cle} » : nombre de mois attendu.") from erreur
        if not 0 < mois <= 600:
            raise ErreurParametrage(f"Âge {mois} mois : entre 1 et 600 mois.")
        if case in (None, "", []):
            continue
        morceaux = case if isinstance(case, list) else str(case).replace(",", ".").split("/")
        try:
            nombres = [Decimal(str(x).strip().replace(",", ".")) for x in morceaux if str(x).strip() != ""]
        except InvalidOperation as erreur:
            raise ErreurParametrage(f"{mois} mois : taux illisible « {case} » (ex. 30 ou 30/35).") from erreur
        if not 1 <= len(nombres) <= 2 or any(not 0 <= n <= 100 for n in nombres):
            raise ErreurParametrage(f"{mois} mois : un ou deux taux entre 0 et 100 % (ex. 30 ou 30/35).")
        propre[str(mois)] = [float(n) for n in sorted(nombres)]
    if not propre:
        raise ErreurParametrage("Renseignez au moins un taux.")
    return propre


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def classe(request, code):
    """PATCH /api/parametrage/auto/depreciation/classes/<code>/ {Libelle, Kilometrage, Taux}."""
    try:
        ligne = DepreciationClasse.objects.get(Code=code)
    except DepreciationClasse.DoesNotExist:
        return Response({"error": f"Ligne {code} introuvable."}, status=status.HTTP_404_NOT_FOUND)
    avant = _classe_json(ligne)
    try:
        if "Libelle" in request.data:
            ligne.Libelle = _texte(request.data["Libelle"], 100, "Libellé", obligatoire=True)
        if "Kilometrage" in request.data:
            ligne.Kilometrage = _texte(request.data["Kilometrage"], 100, "Kilométrage")
        if "Taux" in request.data:
            ligne.Taux = _taux(request.data["Taux"])
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    ligne.ModifiePar = _auteur(request)
    ligne.save()
    apres = _classe_json(ligne)
    _journal(request, f"Dépréciation : ligne « {ligne.Libelle} » modifiée", {"avant": avant, "apres": apres})
    return Response(apres)


def _entier_ou_vide(valeur, libelle):
    if valeur in (None, ""):
        return None
    try:
        return int(valeur)
    except (TypeError, ValueError) as erreur:
        raise ErreurParametrage(f"{libelle} : nombre entier attendu.") from erreur


@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def regles(request):
    """PUT /api/parametrage/auto/depreciation/regles/ {Regles: [...]} : liste complète, dans l'ordre."""
    liste = request.data.get("Regles")
    if not isinstance(liste, list):
        return _reponse_erreur(ErreurParametrage("Règles : liste attendue."))
    codes = set(DepreciationClasse.objects.values_list("Code", flat=True))
    avant = [_regle_json(r) for r in DepreciationRegle.objects.all()]
    nouvelles = []
    try:
        for i, r in enumerate(liste, start=1):
            if r.get("Classe") not in codes:
                raise ErreurParametrage(f"Règle {i} : ligne du tableau inconnue.")
            regle = DepreciationRegle(
                Ordre=i, Classe_id=r["Classe"],
                IdGenre=_entier_ou_vide(r.get("IdGenre"), f"Règle {i}, genre"),
                IdTypeVehicule=_entier_ou_vide(r.get("IdTypeVehicule"), f"Règle {i}, type"),
                IdCarrosserie=_entier_ou_vide(r.get("IdCarrosserie"), f"Règle {i}, carrosserie"),
                CodeCategorie=_texte(r.get("CodeCategorie"), 3, f"Règle {i}, catégorie"),
                ChargeUtileSuperieureA=_entier_ou_vide(r.get("ChargeUtileSuperieureA"), f"Règle {i}, charge utile"),
            )
            if regle.IdGenre is None and regle.IdTypeVehicule is None and regle.IdCarrosserie is None and not regle.CodeCategorie:
                raise ErreurParametrage(f"Règle {i} : indiquez au moins un genre, un type, une carrosserie ou une catégorie.")
            nouvelles.append(regle)
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    with transaction.atomic():
        DepreciationRegle.objects.all().delete()
        DepreciationRegle.objects.bulk_create(nouvelles)
    apres = [_regle_json(r) for r in DepreciationRegle.objects.all()]
    _journal(request, "Dépréciation : règles de classement modifiées", {"avant": avant, "apres": apres})
    return Response(apres)


@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def regles_garanties(request):
    """PUT /api/parametrage/auto/regles-garanties/ {Regles: [...]} : liste complète des garanties admises selon l'âge."""
    liste = request.data.get("Regles")
    if not isinstance(liste, list):
        return _reponse_erreur(ErreurParametrage("Règles : liste attendue."))
    avant = regles_garanties_json()
    nouvelles = []
    try:
        for i, r in enumerate(liste, start=1):
            compagnie = _entier_ou_vide(r.get("IdCompagnie"), f"Règle {i}, compagnie")
            garantie = _entier_ou_vide(r.get("IdSousGarantie"), f"Règle {i}, garantie")
            minimum = _entier_ou_vide(r.get("AgeMinimum"), f"Règle {i}, âge minimum")
            maximum = _entier_ou_vide(r.get("AgeMaximum"), f"Règle {i}, âge maximum")
            if not compagnie or not garantie:
                raise ErreurParametrage(f"Règle {i} : choisissez la compagnie et la garantie.")
            if minimum is None and maximum is None:
                raise ErreurParametrage(f"Règle {i} : indiquez un âge minimum ou maximum.")
            if minimum is not None and maximum is not None and minimum >= maximum:
                raise ErreurParametrage(f"Règle {i} : l'âge minimum doit être inférieur à l'âge maximum.")
            categories = ",".join(c for c in re.split(r"[\s,;]+", str(r.get("Categories") or "")) if c)
            if categories and not re.fullmatch(r"\d{3}(,\d{3})*", categories):
                raise ErreurParametrage(f"Règle {i} : catégories attendues sous la forme 201, 202.")
            nouvelles.append(AutoRegleGarantie(
                IdCompagnie=compagnie, IdSousGarantie=garantie, AgeMinimum=minimum, AgeMaximum=maximum,
                Categories=categories, Commentaire=_texte(r.get("Commentaire"), 200, f"Règle {i}, commentaire"),
            ))
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    with transaction.atomic():
        AutoRegleGarantie.objects.all().delete()
        AutoRegleGarantie.objects.bulk_create(nouvelles)
    apres = regles_garanties_json()
    _journal(request, "Automobile : garanties admises selon l'âge modifiées", {"avant": avant, "apres": apres})
    return Response(apres)


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def parametre(request, cle):
    """PATCH /api/parametrage/auto/depreciation/parametres/<cle>/ {Valeur} ou {Retablir: true}."""
    parametre_ = ParametreGeneral.objects.filter(Cle=cle, Cle__startswith=PREFIXE).first()
    if not parametre_:
        return Response({"error": f"Réglage {cle} inconnu."}, status=status.HTTP_404_NOT_FOUND)
    avant = parametre_.Valeur
    try:
        if request.data.get("Retablir"):
            parametre_.Valeur = parametre_.ValeurOrigine
        elif cle == "auto.depreciation.taux_retenu":
            valeur = str(request.data.get("Valeur") or "").strip()
            if valeur not in CHOIX_TAUX:
                raise ErreurParametrage(f"Taux retenu : {', '.join(CHOIX_TAUX)} attendu.")
            parametre_.Valeur = valeur
        else:
            parametre_.Valeur = _valider_parametre(parametre_, request.data.get("Valeur"))
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    parametre_.ModifiePar = _auteur(request)
    parametre_.save()
    _cache.pop(cle, None)
    _journal(request, f"Dépréciation : « {parametre_.Libelle} » modifié", {"cle": cle, "avant": avant, "apres": parametre_.Valeur})
    return Response(_parametre_json(parametre_))


# ------------------------------------------------------------------ Pool TPV (catégorie 204)
PREFIXE_POOL = "auto.pool_tpv."


def _tranche_json(t):
    return {
        "Id": t.id, "PlacesMin": t.PlacesMin, "PlacesMax": t.PlacesMax, "PrimeRcAnnuelle": float(t.PrimeRcAnnuelle),
        "Accessoires": [float(x) for x in (t.Accessoires or [])], "Ordre": t.Ordre,
    }


def _suivi_pool(du=None, au=None):
    """Contrats émis en offre « POOL TPV » : RC + Recours dus au Pool, par police."""
    filtres, params = [], []
    if du:
        filtres.append("c.dateemission::date >= %s")
        params.append(du)
    if au:
        filtres.append("c.dateemission::date <= %s")
        params.append(au)
    return _lignes(
        f"""
        SELECT c.idcontrat AS "IdContrat", c.numeropolice AS "NumeroPolice", c.dateemission::date AS "DateEmission",
               c.dateeffet::date AS "DateEffet", c.dateexpiration::date AS "DateExpiration",
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS "Client", co.raisonsociale AS "Compagnie",
               COUNT(DISTINCT cd.idcontratdetail) AS "Vehicules",
               COALESCE(SUM(g.primenette) FILTER (WHERE g.idgarantie = 1), 0) AS "PrimeRc",
               COALESCE(SUM(g.primenette) FILTER (WHERE g.idgarantie = 4), 0) AS "PrimeRecours"
        FROM stdcontrat AS c
        JOIN stdcontratdetail AS cd ON cd.idcontrat = c.idcontrat
        JOIN stddevisdetail AS dd ON dd.iddevis = c.iddevis AND fn_est_offre_pool_tpv(dd.idoffre)
        LEFT JOIN stddevisdetgarantie AS g ON g.iddevisdet = dd.iddevisdetail
        LEFT JOIN stdclient AS cl ON cl.idclient = c.idclient
        LEFT JOIN stdcompagnie AS co ON co.idcompagnie = c.idcompagnie
        WHERE COALESCE(c.idcontratannulation, 0) = 0 {''.join(' AND ' + f for f in filtres)}
        GROUP BY c.idcontrat, cl.nom, cl.prenoms, co.raisonsociale
        ORDER BY c.dateemission DESC, c.idcontrat DESC
        """,
        params,
    )


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def pool_tpv(request):
    """GET /api/parametrage/auto/pool-tpv/?du=&au= : tranches, paramètres et primes dues au Pool."""
    suivi = _suivi_pool(request.query_params.get("du") or None, request.query_params.get("au") or None)
    for ligne in suivi:
        ligne["PrimeRc"], ligne["PrimeRecours"] = float(ligne["PrimeRc"]), float(ligne["PrimeRecours"])
        ligne["TotalPool"] = ligne["PrimeRc"] + ligne["PrimeRecours"]
    return Response({
        "Tranches": [_tranche_json(t) for t in PoolTpvTranche.objects.all()],
        "Parametres": [_parametre_json(p) for p in ParametreGeneral.objects.filter(Cle__startswith=PREFIXE_POOL)],
        "Suivi": suivi,
    })


@api_view(["PUT"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def pool_tpv_tranches(request):
    """PUT /api/parametrage/auto/pool-tpv/tranches/ {Tranches: [...]} : grille complète, dans l'ordre des places."""
    liste = request.data.get("Tranches")
    if not isinstance(liste, list) or not liste:
        return _reponse_erreur(ErreurParametrage("Tranches : liste attendue."))
    avant = [_tranche_json(t) for t in PoolTpvTranche.objects.all()]
    nouvelles = []
    try:
        for i, t in enumerate(sorted(liste, key=lambda x: int(x.get("PlacesMin") or 0)), start=1):
            mini = _entier_ou_vide(t.get("PlacesMin"), f"Tranche {i}, places minimum")
            maxi = _entier_ou_vide(t.get("PlacesMax"), f"Tranche {i}, places maximum")
            if mini is None or mini < 0:
                raise ErreurParametrage(f"Tranche {i} : nombre de places minimum attendu.")
            if maxi is not None and maxi < mini:
                raise ErreurParametrage(f"Tranche {i} : le maximum de places doit être au moins égal au minimum.")
            try:
                prime = Decimal(str(t.get("PrimeRcAnnuelle")).replace(" ", "").replace(",", "."))
            except InvalidOperation as erreur:
                raise ErreurParametrage(f"Tranche {i} : prime RC annuelle attendue.") from erreur
            if prime <= 0:
                raise ErreurParametrage(f"Tranche {i} : prime RC annuelle positive attendue.")
            accessoires = t.get("Accessoires") or []
            if not isinstance(accessoires, list) or len(accessoires) != 12:
                raise ErreurParametrage(f"Tranche {i} : douze accessoires attendus (1 à 12 mois).")
            try:
                accessoires = [float(Decimal(str(a).replace(" ", "").replace(",", ".") or 0)) for a in accessoires]
            except InvalidOperation as erreur:
                raise ErreurParametrage(f"Tranche {i} : accessoire illisible.") from erreur
            if any(a < 0 for a in accessoires):
                raise ErreurParametrage(f"Tranche {i} : accessoires positifs attendus.")
            if nouvelles and nouvelles[-1].PlacesMax is not None and mini <= nouvelles[-1].PlacesMax:
                raise ErreurParametrage(f"Tranche {i} : chevauche la tranche précédente.")
            if nouvelles and nouvelles[-1].PlacesMax is None:
                raise ErreurParametrage("Seule la dernière tranche peut être sans maximum de places.")
            nouvelles.append(PoolTpvTranche(PlacesMin=mini, PlacesMax=maxi, PrimeRcAnnuelle=prime, Accessoires=accessoires,
                                            Ordre=i, ModifiePar=_auteur(request)))
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    with transaction.atomic():
        PoolTpvTranche.objects.all().delete()
        PoolTpvTranche.objects.bulk_create(nouvelles)
    apres = [_tranche_json(t) for t in PoolTpvTranche.objects.all()]
    _journal(request, "Pool TPV : tarif modifié", {"avant": avant, "apres": apres})
    return Response(apres)


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated, EstAdministrateur])
def pool_tpv_parametre(request, cle):
    """PATCH /api/parametrage/auto/pool-tpv/parametres/<cle>/ {Valeur} ou {Retablir: true}."""
    parametre_ = ParametreGeneral.objects.filter(Cle=cle, Cle__startswith=PREFIXE_POOL).first()
    if not parametre_ or cle == "auto.pool_tpv.offre":
        return Response({"error": f"Réglage {cle} inconnu ou non modifiable."}, status=status.HTTP_404_NOT_FOUND)
    avant = parametre_.Valeur
    try:
        if request.data.get("Retablir"):
            parametre_.Valeur = parametre_.ValeurOrigine
        elif cle == "auto.pool_tpv.fractions":
            morceaux = [m.strip().replace(",", ".") for m in str(request.data.get("Valeur") or "").split("/")]
            try:
                nombres = [Decimal(m) for m in morceaux]
            except InvalidOperation as erreur:
                raise ErreurParametrage("Fractions : douze pourcentages séparés par « / » attendus.") from erreur
            if len(nombres) != 12 or any(not 0 < n <= 100 for n in nombres) or nombres != sorted(nombres):
                raise ErreurParametrage("Fractions : douze pourcentages croissants entre 0 et 100, séparés par « / ».")
            parametre_.Valeur = "/".join(f"{n:f}".rstrip("0").rstrip(".") for n in nombres)
        else:
            parametre_.Valeur = _valider_parametre(parametre_, request.data.get("Valeur"))
    except ErreurParametrage as erreur:
        return _reponse_erreur(erreur)
    parametre_.ModifiePar = _auteur(request)
    parametre_.save()
    _cache.pop(cle, None)
    _journal(request, f"Pool TPV : « {parametre_.Libelle} » modifié", {"cle": cle, "avant": avant, "apres": parametre_.Valeur})
    return Response(_parametre_json(parametre_))


# ------------------------------------------------------------------ calcul pour les écrans
def _date(valeur):
    if not valeur:
        return None
    if isinstance(valeur, (date, datetime)):
        return valeur if isinstance(valeur, date) else valeur.date()
    texte = str(valeur).strip()[:10]
    for format_ in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texte, format_).date()
        except ValueError:
            continue
    return None


def _nombre(valeur):
    try:
        return Decimal(str(valeur).replace(" ", "").replace(",", ".")) if valeur not in (None, "") else None
    except InvalidOperation:
        return None


def calculer_valeurs_venales(vehicules, date_effet_defaut=None):
    """[{Cle?, IdGenre, IdTypeVehicule, IdCarrosserie, CodeCategorie | IdTarif, ChargeUtile, ValeurNeuve, DateMec,
    DateEffet?}] → mêmes clés + Classe, Libelle, AgeMois, TauxMinimum, TauxMaximum, Taux, ValeurVenale, Explication."""
    resultats = []
    with connection.cursor() as cursor:
        for v in vehicules[:VEHICULES_MAX]:
            categorie = str(v.get("CodeCategorie") or "").strip()
            if not categorie and v.get("IdTarif"):
                cursor.execute("SELECT codecategorie FROM stdtarif WHERE idtarif = %s", [int(v["IdTarif"])])
                ligne = cursor.fetchone()
                categorie = (ligne[0] or "").strip() if ligne else ""
            entier = lambda x: int(x) if str(x or "").strip().lstrip("-").isdigit() else None  # noqa: E731
            cursor.execute(
                "SELECT classe, libelle, age_mois, taux_minimum, taux_maximum, taux, valeur_venale, explication "
                "FROM fn_lephare_depreciation(%s, %s, %s, %s, %s, %s, %s, %s)",
                [entier(v.get("IdGenre")), entier(v.get("IdTypeVehicule")), entier(v.get("IdCarrosserie")), categorie,
                 _nombre(v.get("ChargeUtile")) or 0, _nombre(v.get("ValeurNeuve")) or 0, _date(v.get("DateMec")),
                 _date(v.get("DateEffet")) or _date(date_effet_defaut) or date.today()],
            )
            r = cursor.fetchone()
            resultats.append({
                "Cle": v.get("Cle"), "Classe": r[0], "Libelle": r[1], "AgeMois": r[2],
                "TauxMinimum": None if r[3] is None else float(r[3]), "TauxMaximum": None if r[4] is None else float(r[4]),
                "Taux": None if r[5] is None else float(r[5]),
                "ValeurVenale": None if r[6] is None else int(r[6]), "Explication": r[7],
            })
    return resultats


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def valeur_venale(request):
    """POST /api/auto/valeur-venale/ {Vehicules: [...], DateEffet} : valeurs vénales du tableau (n'écrit rien)."""
    vehicules = request.data.get("Vehicules")
    if not isinstance(vehicules, list):
        return Response({"error": "Vehicules : liste attendue."}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"Vehicules": calculer_valeurs_venales(vehicules, request.data.get("DateEffet"))})
