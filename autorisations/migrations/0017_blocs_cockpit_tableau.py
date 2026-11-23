# Un droit par bloc du cockpit et du tableau de bord (demande du 2026-11-23 : « je veux que chaque bloc du cockpit et du tableau
# de bord soit visible par un utilisateur qu'avec des droits »). Cases dans Administration > Rôles, groupes « Cockpit
# opérationnel » et « Tableau de bord ».
#
# Chaque rôle reçoit les blocs qu'il voyait jusqu'ici, pour que l'affichage ne change pas à la mise à jour : au cockpit, bloc
# visible = droit de lecture de son module (et famille d'information « tableaux.* » de la migration 0016 là où elle a été
# appliquée) ; au tableau de bord, tous les blocs. La direction retire ensuite les blocs profil par profil. Les 8 droits
# « tableaux.* » sont supprimés.

from django.db import migrations

from autorisations.catalogue import BLOCS_ECRANS, synchroniser_droits

ANCIENNES_FAMILLES = ["chiffre_affaires", "primes", "portefeuille", "devis", "caisse", "reversements", "commissions", "alertes"]


def blocs_du_role(codes, familles_en_base):
    """Blocs que le rôle voyait avant cette migration (codes : ses droits)."""
    def famille(nom):
        code = f"tableaux.{nom}"
        return code in codes if code in familles_en_base else True

    a = codes.__contains__
    ca = famille("chiffre_affaires") and (a("commissions.view") or a("reporting.view"))
    primes = famille("primes") and a("contrats.view")
    portefeuille = famille("portefeuille") and a("contrats.view")
    devis = famille("devis") and a("devis.view")
    caisse = famille("caisse") and a("encaissements.view")
    regles = {
        "cockpit.chiffre_affaires": ca, "cockpit.percu": ca, "cockpit.reste_a_percevoir": ca, "cockpit.commissions_listes": ca,
        "cockpit.primes": primes,
        "cockpit.polices": portefeuille, "cockpit.echeances": portefeuille, "cockpit.derniers_contrats": portefeuille,
        "cockpit.branches": a("contrats.view") and (primes or ca),
        "cockpit.devis": devis, "cockpit.transformation": devis, "cockpit.derniers_devis": devis,
        "cockpit.encaisse": caisse, "cockpit.reste_a_encaisser": caisse,
        "cockpit.a_reverser": famille("reversements") and a("reversements.view"),
        # Tuile affichée jusqu'ici seulement sans le chiffre d'affaires (le reste à percevoir la reprenait)
        "cockpit.commissions": famille("commissions") and a("commissions.view") and not ca,
        "cockpit.a_traiter": True,
        "tableau.chiffre_affaires": famille("chiffre_affaires"), "tableau.percu": famille("chiffre_affaires"),
        "tableau.reste_a_percevoir": famille("chiffre_affaires"), "tableau.ca_par_mois": famille("chiffre_affaires"),
        "tableau.ca_listes": famille("chiffre_affaires"),
        "tableau.primes": famille("primes"),
        "tableau.encaisse": famille("caisse"), "tableau.recouvrement": famille("caisse"),
        "tableau.primes_par_mois": famille("primes") or famille("caisse"),
        "tableau.compagnies": famille("chiffre_affaires") or famille("primes"),
        "tableau.branches": famille("chiffre_affaires") or famille("primes") or famille("caisse"),
        "tableau.alertes": famille("alertes"),
    }
    return [code for code, accorde in regles.items() if accorde]


def accorder(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Role = apps.get_model("autorisations", "Role")
    synchroniser_droits(Droit)
    anciennes = [f"tableaux.{nom}" for nom in ANCIENNES_FAMILLES]
    familles_en_base = set(Droit.objects.filter(code__in=anciennes).values_list("code", flat=True))
    blocs = {d.code: d for d in Droit.objects.filter(code__in=BLOCS_ECRANS)}
    for role in Role.objects.all():
        codes = set(role.droits.values_list("code", flat=True))
        role.droits.add(*[blocs[code] for code in blocs_du_role(codes, familles_en_base) if code in blocs])
    Droit.objects.filter(code__in=anciennes).delete()


def retirer(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Droit.objects.filter(code__in=BLOCS_ECRANS).exclude(code="cockpit.view").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("autorisations", "0016_infos_tableaux"),
    ]

    operations = [migrations.RunPython(accorder, retirer)]
