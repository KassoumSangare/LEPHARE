# Transport (bordereaux GUCE) : part AFS-CI déduite par certificat quand le fichier ne la donne pas (500 F, valeur
# écrite jusqu'ici dans production/views_transport_guce.py), réglable dans Administration > Le cabinet & règles de
# gestion. Retour : python manage.py migrate configuration_api 0092

from decimal import Decimal

from django.db import migrations

CLE = "transport.part_afs_ci"


def creer(apps, schema_editor):
    Parametre = apps.get_model("configuration_api", "ParametreGeneral")
    Parametre.objects.get_or_create(Cle=CLE, defaults={
        "Groupe": "transport", "Libelle": "Part AFS-CI par certificat",
        "Aide": "Déduite de l'accessoire et de la prime TTC de chaque certificat dont l'accessoire l'atteint, quand le "
                "fichier GUCE importé ne donne pas la colonne « Accessoires AFS-CI ».",
        "Type": "montant", "Valeur": "500", "ValeurOrigine": "500", "Unite": "F",
        "Minimum": Decimal("0"), "Maximum": None, "Ordre": 1,
    })


def retirer(apps, schema_editor):
    apps.get_model("configuration_api", "ParametreGeneral").objects.filter(Cle=CLE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0092_reglages_branches"),
    ]

    operations = [
        migrations.RunPython(creer, retirer),
    ]
