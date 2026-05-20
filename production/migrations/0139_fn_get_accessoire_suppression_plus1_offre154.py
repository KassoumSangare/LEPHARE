# Suppression du +1 hardcodé dans fn_get_accessoire pour l'offre 154 (CGA P/C Capital 2K).
# Ce +1 était un ancien correctif compensant l'arrondi à 0 décimales par garantie
# (sp_enregistrement_assure_ia utilisait ROUND(..., 0) → taxe G17=307 + G19=307 = 614).
# Depuis que la procédure utilise ROUND(..., 4), la somme devient 614.8 → ROUND = 615,
# et le +1 provoque 615 + 146 = 761 au lieu de 760.

from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0138_sp_finalisation_devis_ia_taxe_arrondi"),
    ]

    operations = [
        migrations.RunSQL(
            *load_sql_upgrade(
                __file__,
                "functions/fn_get_accessoire",
                from_version=1,
                to_version=2,
            )
        ),
    ]
