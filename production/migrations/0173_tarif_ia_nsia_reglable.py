# Tarif Individuelle Accidents NSIA réglable dans l'admin (Réglages par branche > Individuelle Accidents) :
# fn_calcul_prime_ia_nsia v2 et fn_get_accessoire_ia_nsia v2 lisent les taux par classe et les tranches
# d'accessoires (tables créées et remplies à l'identique par configuration_api 0101) au lieu de les porter en dur.
# Retour : python manage.py migrate production 0172

from django.db import migrations

from uranus.utils.migrations import load_sql_version


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0172_transport_hors_guce"),
        ("configuration_api", "0101_reglages_transport_ia"),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_calcul_prime_ia_nsia", 2),
            load_sql_version(__file__, "functions/fn_calcul_prime_ia_nsia", 1),
        ),
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_get_accessoire_ia_nsia", 2),
            load_sql_version(__file__, "functions/fn_get_accessoire_ia_nsia", 1),
        ),
    ]
