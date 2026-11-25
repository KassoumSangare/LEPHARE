# Demande du 2026-11-25 : « l'accès à l'onglet correction doit requérir des droits ». Droit dédié corrections.view (« Accéder aux
# corrections ») pour la section Corrections de l'administration ; elle s'ouvrait jusque-là à qui avait le droit d'un seul des
# outils de son catalogue (modifier un client, un devis, encaisser…), donc à presque tous les gestionnaires.
# Accordé à l'Administrateur technique, au Développeur et aux rôles qui corrigeaient déjà les contrats depuis l'administration
# (contrats.admin_update : l'écran est désormais rangé dans cette section), pour que personne ne perde cet écran à la mise à
# jour ; l'administrateur l'accorde ensuite profil par profil (Administration > Rôles).

from django.db import migrations

from autorisations.catalogue import synchroniser_droits

ACCES = "corrections.view"


def accorder(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Role = apps.get_model("autorisations", "Role")
    synchroniser_droits(Droit)
    acces = Droit.objects.get(code=ACCES)
    for role in Role.objects.filter(code__in=("ADMIN_TECH", "DEVELOPPEUR")):
        role.droits.add(acces)
    for role in Role.objects.filter(droits__code="contrats.admin_update").distinct():
        role.droits.add(acces)


def retirer(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Droit.objects.filter(code=ACCES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("autorisations", "0019_annulation_reversement"),
    ]

    operations = [migrations.RunPython(accorder, retirer)]
