"""
Blocs du cockpit et du tableau de bord visibles par l'utilisateur (demande du 2026-11-23 : « chaque bloc du cockpit et du
tableau de bord visible par un utilisateur qu'avec des droits ») : un droit par bloc dans le catalogue
(autorisations/catalogue.py, BLOCS_COCKPIT et BLOCS_TABLEAU), coché rôle par rôle dans Administration > Rôles. Le serveur ne
calcule ni n'envoie les chiffres d'un bloc non accordé.

Jamais d'accès par défaut : tant que la migration autorisations 0017 n'est pas appliquée (droit du bloc absent du catalogue
en base, code déployé avant la migration), la règle d'avant s'applique, c'est-à-dire le droit de lecture du module.
"""
from autorisations.catalogue import BLOCS_COCKPIT, BLOCS_TABLEAU
from autorisations.rbac import droits_utilisateur

# Champs du chiffre d'affaires (production/chiffre_affaires.calculer) propres à chacun des trois blocs qui le montrent
CHAMPS_CHIFFRE_AFFAIRES = {
    "chiffre_affaires": ("Total", "Commissions", "Accessoires", "Rafas", "Nombre", "RafasFactures", "RafasBase", "PrimeNette",
                         "TauxMoyen", "Precedent", "AuPrecedent", "Mensuel", "Apporteurs", "Net", "PartDesPrimes"),
    "percu": ("Percu", "PercuPrecedent"),
    "reste_a_percevoir": ("EnAttente", "ResteAPercevoir"),
}

_LECTURE_CA = ("commissions.view", "reporting.view")
# Règle d'avant la migration 0017, quand le droit du bloc n'existe pas encore en base : l'un de ces droits suffit ; ()
# = jamais (tuile « Commissions en attente » : masquée dès que le chiffre d'affaires était visible, c'est-à-dire toujours)
DROITS_AVANT_MIGRATION = {
    "cockpit.chiffre_affaires": _LECTURE_CA, "cockpit.percu": _LECTURE_CA, "cockpit.reste_a_percevoir": _LECTURE_CA,
    "cockpit.commissions_listes": _LECTURE_CA,
    "cockpit.primes": ("contrats.view",), "cockpit.polices": ("contrats.view",), "cockpit.branches": ("contrats.view",),
    "cockpit.echeances": ("contrats.view",), "cockpit.derniers_contrats": ("contrats.view",),
    "cockpit.devis": ("devis.view",), "cockpit.transformation": ("devis.view",), "cockpit.derniers_devis": ("devis.view",),
    "cockpit.encaisse": ("encaissements.view",), "cockpit.reste_a_encaisser": ("encaissements.view",),
    "cockpit.a_reverser": ("reversements.view",), "cockpit.commissions": (), "cockpit.a_traiter": ("cockpit.view",),
    # Tableau de bord : tous ses blocs étaient visibles avec l'accès à l'écran
    **{code: ("reporting.view",) for code in BLOCS_TABLEAU},
}
# Blocs qui listent des clients (polices, contrats, devis) : le droit de consulter le module est exigé en plus du bloc
MODULE_EXIGE = {"cockpit.echeances": "contrats.view", "cockpit.derniers_contrats": "contrats.view",
                "cockpit.derniers_devis": "devis.view"}


def _blocs_visibles(utilisateur, codes):
    """Noms courts (sans le préfixe « cockpit. » ou « tableau. ») des blocs que les droits de l'utilisateur laissent voir."""
    from autorisations.models import Droit

    au_catalogue = set(Droit.objects.filter(code__in=codes).values_list("code", flat=True))
    droits = droits_utilisateur(utilisateur)

    def accorde(code):
        if code in au_catalogue:
            permis = code in droits
        else:
            permis = any(droit in droits for droit in DROITS_AVANT_MIGRATION.get(code, ()))
        module = MODULE_EXIGE.get(code)
        return permis and (module is None or module in droits)

    return frozenset(code.split(".", 1)[1] for code in codes if accorde(code))


def blocs_cockpit(utilisateur):
    return _blocs_visibles(utilisateur, BLOCS_COCKPIT)


def blocs_tableau(utilisateur):
    return _blocs_visibles(utilisateur, BLOCS_TABLEAU)


def chiffre_affaires_selon_blocs(ca, blocs):
    """Chiffre d'affaires réduit aux champs des blocs « Chiffre d'affaires », « Perçu », « Reste à percevoir » accordés ;
    None si aucun ne l'est."""
    garder = {champ for bloc, champs in CHAMPS_CHIFFRE_AFFAIRES.items() if bloc in blocs for champ in champs}
    if not garder:
        return None
    resultat = {cle: valeur for cle, valeur in ca.items() if cle in garder}
    if "Mois" in ca:
        mois = {}
        if "chiffre_affaires" in blocs:
            mois["Total"] = ca["Mois"].get("Total")
        if "percu" in blocs:
            mois["Percu"] = ca["Mois"].get("Percu")
        resultat["Mois"] = mois
    return resultat
