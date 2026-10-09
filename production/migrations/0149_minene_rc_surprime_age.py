# MINENE (compte rendu OREOLE du 2026-10-08, CP et barème 70 %-80 %) :
#   - RC chef de famille rattachée (offre 67) : sp_creation_devis_risques_divers cherchait la police
#     Santé MINENE via le devis RC, qui n'existe pas encore à la création ; le nombre d'adhérents valait
#     0 et toutes les primes du devis aussi. La police est désormais lue sur le numéro saisi (au moins
#     1 adhérent) : 14 524 + 6 000 + 2 976 + 1 500 = 25 000 F TTC par adhérent, comme le barème.
#     Procédure jusqu'ici absente du dépôt : la version en base avant correction sert de retour.
#   - Surprime d'âge Santé MINENE : 30 % de 61 à 64 ans (barème « de 61 à 65 ans »), 50 % de 65 à
#     69 ans ; elle commençait à 60 ans.
# Retour : python manage.py migrate production 0148

from django.db import migrations

from uranus.utils.migrations import load_sql_pair


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0148_dommages_parametrage"),
    ]

    operations = [
        migrations.RunSQL(
            *load_sql_pair(
                __file__,
                "procedures/sp_creation_devis_risques_divers.sql",
                "procedures/sp_creation_devis_risques_divers_reverse.sql",
            )
        ),
        migrations.RunSQL(
            *load_sql_pair(
                __file__,
                "functions/fn_get_surprime_age_minene_sante.sql",
                "functions/fn_get_surprime_age_minene_sante_reverse.sql",
            )
        ),
    ]
