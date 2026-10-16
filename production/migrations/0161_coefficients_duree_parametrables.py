# Tarifs automobiles NSIA « à lecture directe » (documents reçus d'OREOLE le 2026-10-16) : les coefficients de prime des
# contrats de moins d'un an (6 mois = 53 %, 3 mois = 28 %…) étaient écrits dans fn_calcul_taux_prime_fractionnee ; ils
# deviennent réglables dans l'admin (réglage auto.coefficients_duree, créé par la migration configuration_api 0089).
# Valeurs d'origine inchangées : le calcul ne change pas tant que le réglage n'est pas modifié.
# Retour : python manage.py migrate production 0160

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0160_sante_age_date_effet_derogation"),
        ("configuration_api", "0089_tarifs_auto_lecture_directe"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_calcul_taux_prime_fractionnee", from_version=1, to_version=2)),
    ]
