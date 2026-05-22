# Fix arrondi taxe IA INC : pour N > 1 assurés incorporés, la sommation de taxes
# arrondies par garantie et par assuré donnait 761 au lieu de 760.
# Solution : utiliser une formule unique ROUND((prime_total + accessoire) * taux / 100, 0)
# pour toutes les offres IA avec prime imposée (comme déjà fait pour les offres 173/174).

from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0137_sp_avenant_retrait"),
    ]

    operations = [
        migrations.RunSQL(
            *load_sql_upgrade(
                __file__,
                "procedures/sp_finalisation_devis",
                from_version=2,
                to_version=3,
            )
        ),
    ]
