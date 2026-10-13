# RC chef de famille MINENE : franchise des dommages matériels (10 %, minimum 20 000, maximum 200 000)
# lue dans Administration > Réglages Santé MINENE au lieu d'être écrite dans fn_garantie_offre_risques_divers
# (v1 = définition d'URANUS en base, jusqu'ici absente du dépôt). Valeurs inchangées sans réglage.
# Retour : python manage.py migrate production 0154

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0154_minene_parametrage_admin"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_risques_divers", from_version=1, to_version=2)),
    ]
