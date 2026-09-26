# Aligne le BNS sur NSIA pour la sous-garantie 172 (Bris de glace avec prise en compte
# des toits ouvrants) : NSIA applique le bonus (mais pas la réduction commerciale) sur
# cette garantie, alors que fn_calcul_prime_prorata l'excluait du BNS.
# Référence : conditions particulières NSIA EBENE PREMIUM TPC (202), 90 210 x 0,70 = 63 147.

from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0140_fix_typos_default_maxlength_boolean"),
    ]

    operations = [
        migrations.RunSQL(
            *load_sql_upgrade(
                __file__,
                "functions/fn_calcul_prime_prorata",
                from_version=1,
                to_version=2,
            )
        ),
    ]
