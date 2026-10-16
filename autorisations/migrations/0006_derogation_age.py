# Droit « Déroger à la limite d'âge » (devis.derogation_age, demandé le 2026-10-15 : « quand l'âge dépasse les
# conditions, l'import doit s'effectuer par habilité ») : inscrit au catalogue et accordé aux rôles qui ont déjà tous
# les droits (Administrateur technique, Développeur) ; les autres rôles se règlent dans Administration > Rôles.

from django.db import migrations

from autorisations.catalogue import synchroniser_droits

CODE = "devis.derogation_age"


def accorder(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Role = apps.get_model("autorisations", "Role")
    synchroniser_droits(Droit)
    droit = Droit.objects.get(code=CODE)
    autres = Droit.objects.exclude(code=CODE).count()
    for role in Role.objects.all():
        if role.droits.exclude(code=CODE).count() >= autres:
            role.droits.add(droit)


def retirer(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    for droit in Droit.objects.filter(code=CODE):
        droit.roles.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("autorisations", "0005_roles_initiaux"),
    ]

    operations = [migrations.RunPython(accorder, retirer)]
