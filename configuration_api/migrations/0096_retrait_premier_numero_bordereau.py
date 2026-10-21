# Le réglage « Numéro du prochain bordereau » (finance.premier_numero_bordereau, migration 0095) ne sert plus :
# depuis la migration production 0169 (2026-10-20), les bordereaux sont numérotés comme les polices (code courtier +
# catégorie + mois + exercice + « B » + n° du mois). Retour : le réglage est recréé avec sa valeur d'origine.

from django.db import migrations

CLE = "finance.premier_numero_bordereau"


def retirer(apps, schema_editor):
    apps.get_model("configuration_api", "ParametreGeneral").objects.filter(Cle=CLE).delete()


def recreer(apps, schema_editor):
    apps.get_model("configuration_api", "ParametreGeneral").objects.get_or_create(Cle=CLE, defaults=dict(
        Groupe="finance", Libelle="Numéro du prochain bordereau",
        Aide="Les bordereaux de reversement et de réclamation suivent la numérotation d'OREOLE (dernier connu : 2117 du "
             "19/06/2026). Le numéro proposé est le plus grand de ce réglage et du dernier bordereau émis + 1 ; il reste "
             "modifiable à l'émission.",
        Type="entier", Valeur="2118", ValeurOrigine="2118", Unite="", Minimum=1, Maximum=999999, Ordre=4,
    ))


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0095_reversements_courriers"),
        ("production", "0169_numerotation_bordereaux"),
    ]

    operations = [migrations.RunPython(retirer, recreer)]
