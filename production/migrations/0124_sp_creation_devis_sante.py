from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):
    """
    Applique la réduction/majoration commerciale sur la prime MINENE pour tous
    les types de contrats (particulier et société), et gère aussi la majoration
    (taux négatif). Avant : seulement type_contrat=2 et taux > 0.
    """

    dependencies = [
        ("production", "0123_contratdetgarantie_tauxfranchise_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            *load_sql_upgrade(
                __file__,
                "procedures/sp_creation_devis_sante",
                from_version=1,
                to_version=2,
            )
        )
    ]
