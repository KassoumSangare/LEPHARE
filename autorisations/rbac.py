"""
Droits effectifs d'un utilisateur : Utilisateur -> Rôles actifs -> Droits.

- Compte inactif ou expiré : aucun droit.
- Administrateur (is_admin, repris d'URANUS) : tous les droits (accès de secours ; ses actions
  sont journalisées comme celles de tout le monde).
- Sinon : réunion des droits de ses rôles actifs ; un droit ajouté au catalogue après coup (catalogue.REMPLACES) et pas
  encore créé en base par sa migration est tenu par le droit qui en tenait lieu.
Le calcul est gardé sur l'objet utilisateur, rechargé à chaque requête par l'authentification.
"""

from django.utils import timezone

from .catalogue import REMPLACES, TOUS

# Droits de REMPLACES déjà créés en base : la recherche s'arrête une fois qu'ils y sont tous
_remplacants_en_base = set()


def _remplacants_absents():
    from .models import Droit

    if len(_remplacants_en_base) < len(REMPLACES):
        _remplacants_en_base.update(Droit.objects.filter(code__in=list(REMPLACES)).values_list("code", flat=True))
    return [code for code in REMPLACES if code not in _remplacants_en_base]


def compte_expire(utilisateur):
    expiration = getattr(utilisateur, "expiry_date", None)
    return bool(expiration and expiration < timezone.now())


def droits_utilisateur(utilisateur):
    if not utilisateur or not getattr(utilisateur, "is_authenticated", False):
        return frozenset()
    deja = getattr(utilisateur, "_droits_lephare", None)
    if deja is not None:
        return deja
    from .models import Droit

    if not utilisateur.is_active or compte_expire(utilisateur):
        codes = frozenset()
    elif getattr(utilisateur, "is_admin", False):
        codes = frozenset(set(TOUS) | set(Droit.objects.values_list("code", flat=True)))
    else:
        codes = set(
            Droit.objects.filter(roles__actif=True, roles__attributions__utilisateur=utilisateur)
            .values_list("code", flat=True).distinct()
        )
        codes |= {code for code in _remplacants_absents() if REMPLACES[code] in codes}
        codes = frozenset(codes)
    utilisateur._droits_lephare = codes
    return codes


def a_le_droit(utilisateur, code):
    return code in droits_utilisateur(utilisateur)


def roles_utilisateur(utilisateur):
    from .models import Role

    return list(Role.objects.filter(attributions__utilisateur=utilisateur).order_by("ordre", "libelle"))
