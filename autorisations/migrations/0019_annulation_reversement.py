# Demande du 2026-11-24 : « permettre l'annulation d'un reversement mais l'annulation se fait avec droit ».
# Droit dédié reversements.cancel (« Annuler un reversement », motif obligatoire) pour l'annulation d'un bordereau de
# reversement ; elle relevait jusque-là de « Valider un reversement ». Les rôles qui l'avaient le reçoivent, pour que
# personne ne perde l'annulation à la mise à jour ; l'administrateur le retire ensuite profil par profil
# (Administration > Rôles).

from django.db import migrations

from autorisations.catalogue import synchroniser_droits

ANNULATION = "reversements.cancel"


def accorder(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Role = apps.get_model("autorisations", "Role")
    synchroniser_droits(Droit)
    annulation = Droit.objects.get(code=ANNULATION)
    for role in Role.objects.filter(droits__code="reversements.validate").distinct():
        role.droits.add(annulation)


def retirer(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Droit.objects.filter(code=ANNULATION).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("autorisations", "0018_onglets_tableau_guide"),
    ]

    operations = [migrations.RunPython(accorder, retirer)]
