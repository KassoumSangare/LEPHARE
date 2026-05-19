# Fix : sp_avenant_retrait appelait sp_avenant_creation_devis_initial avec 7 params
# mais la procédure en attend 9 depuis la migration 0075 (date_expiration + motif_annulation).

from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0136_merge_20260518_2207"),
    ]

    operations = [
        migrations.RunSQL(
            *load_sql_upgrade(
                __file__,
                "procedures/sp_avenant_retrait",
                from_version=1,
                to_version=2,
            )
        )
    ]
