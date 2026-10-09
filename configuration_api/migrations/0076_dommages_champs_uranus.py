# Saisie Dommages alignée sur l'écran d'URANUS : plus de « description du risque » demandée par défaut
# (URANUS n'en avait pas ; les champs livrés par 0075 avaient été rédigés sans document d'OREOLE).
# Seules les catégories dont les champs n'ont pas été retouchés dans Réglages Dommages sont vidées ;
# l'administration peut toujours en ajouter. Retour : python manage.py migrate configuration_api 0075

import importlib

from django.db import migrations

CHAMPS_0075 = {
    id_tarif: champs
    for id_tarif, _ordre, _description, champs in importlib.import_module(
        "configuration_api.migrations.0075_dommages_parametrage"
    ).CATEGORIES
}


def vider(apps, schema_editor):
    DommageCategorie = apps.get_model("configuration_api", "DommageCategorie")
    for categorie in DommageCategorie.objects.all():
        if categorie.ChampsRisque and categorie.ChampsRisque == CHAMPS_0075.get(categorie.IdTarif):
            categorie.ChampsRisque = []
            categorie.save(update_fields=["ChampsRisque"])


def retablir(apps, schema_editor):
    DommageCategorie = apps.get_model("configuration_api", "DommageCategorie")
    for categorie in DommageCategorie.objects.all():
        if not categorie.ChampsRisque and CHAMPS_0075.get(categorie.IdTarif):
            categorie.ChampsRisque = CHAMPS_0075[categorie.IdTarif]
            categorie.save(update_fields=["ChampsRisque"])


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0075_dommages_parametrage"),
    ]

    operations = [migrations.RunPython(vider, retablir)]
