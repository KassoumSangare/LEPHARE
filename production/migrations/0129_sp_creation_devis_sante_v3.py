from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):
    """
    Corrige l'application du taux de réduction/majoration pour les offres MINENE.
    Avant : le taux n'était appliqué que lorsque prime_famille=0 ET prime_affilie=0 ET prime_globale=0.
    Si le frontend envoyait prime_famille>0 (ex: 543556 saisi manuellement), le taux était ignoré.
    Après : le taux est appliqué à la prime de base quelle que soit sa source (table ou saisie manuelle).
    """

    dependencies = [
        ("production", "0128_sp_finalisation_devis"),
    ]

    operations = [
        migrations.RunSQL(
            *load_sql_upgrade(
                __file__,
                "procedures/sp_creation_devis_sante",
                from_version=2,
                to_version=3,
            )
        )
    ]
