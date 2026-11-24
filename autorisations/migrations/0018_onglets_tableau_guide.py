# Onglets visibles selon le profil (demande du 2026-11-24) :
# 1. « le guide administratif doit être visible avec droit » : droit guide.view (Administration > Rôles, groupe « Guide de
#    l'administration »). Au départ, seuls les rôles techniques à accès complet l'ont, comme la restauration des archives
#    (0012) ; l'administrateur l'accorde ensuite profil par profil.
# 2. « quand un profil n'a pas le droit de voir le tableau de bord il ne doit pas voir l'onglet » : droit tableau.view, qui
#    remplace « Consulter les états » (reporting.view) pour ouvrir le tableau de bord. Chaque rôle qui avait
#    « Consulter les états » le reçoit, pour que l'affichage ne change pas à la mise à jour.

from django.db import migrations

from autorisations.catalogue import synchroniser_droits

GUIDE = "guide.view"
TABLEAU = "tableau.view"


def accorder(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Role = apps.get_model("autorisations", "Role")
    synchroniser_droits(Droit)
    guide = Droit.objects.get(code=GUIDE)
    tableau = Droit.objects.get(code=TABLEAU)
    for role in Role.objects.filter(code__in=["ADMIN_TECH", "DEVELOPPEUR"]):
        role.droits.add(guide)
    for role in Role.objects.filter(droits__code="reporting.view").distinct():
        role.droits.add(tableau)


def retirer(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Droit.objects.filter(code__in=[GUIDE, TABLEAU]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("autorisations", "0017_blocs_cockpit_tableau"),
    ]

    operations = [migrations.RunPython(accorder, retirer)]
