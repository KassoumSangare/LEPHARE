from django.db import migrations


def ajouter(apps, schema_editor):
    ParametreGeneral = apps.get_model("configuration_api", "ParametreGeneral")
    # Mention imprimée jusqu'ici en dur dans l'en-tête des états (exportUtils.js) : à vérifier
    valeur = "Agrément N° 0021 / MEF / DAPS"
    ParametreGeneral.objects.get_or_create(Cle="documents.mention_agrement", defaults=dict(
        Groupe="documents",
        Libelle="Agrément du cabinet",
        Aide="Imprimé sous le nom du cabinet dans l'en-tête des états réglementaires et de gestion. Vide : rien n'est imprimé.",
        Type="texte",
        Valeur=valeur,
        ValeurOrigine=valeur,
        Ordre=4,
    ))


def retirer(apps, schema_editor):
    apps.get_model("configuration_api", "ParametreGeneral").objects.filter(Cle="documents.mention_agrement").delete()


class Migration(migrations.Migration):

    dependencies = [("configuration_api", "0073_parametrage_lephare")]

    operations = [migrations.RunPython(ajouter, retirer)]
