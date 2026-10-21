# Numérotation des bordereaux sans la catégorie (demande du 2026-10-21) : code courtier + mois + exercice + « B » +
# n° séquentiel du mois (ex. 11861026B0018). Même compteur (lephare_numero_bordereau) : les numéros déjà attribués,
# avec catégorie, ne changent pas et la suite du mois continue. Retour : python manage.py migrate production 0170

from django.db import migrations

from uranus.utils.migrations import load_sql_version


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0170_encaissement_date_reception_cheque"),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_lephare_numero_bordereau", 2),
            load_sql_version(__file__, "functions/fn_lephare_numero_bordereau", 1),
        ),
    ]
