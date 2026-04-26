from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):
    """
    Renouvellement Santé MINENE : sp_avenant_creation_devis_initial v2
    - Ajoute primeimposee dans les INSERTs stddevisdetail
    - Corrige IdContratDetail → IdDevisDetail pour StdComplementDevisDetailSante
    - Copie StdAdherent et StdAffilie lors du renouvellement Santé
    """

    dependencies = [
        ("production", "0129_sp_creation_devis_sante_v3"),
    ]

    operations = [
        migrations.RunSQL(
            *load_sql_upgrade(
                __file__,
                "procedures/sp_avenant_creation_devis_initial",
                from_version=1,
                to_version=2,
            )
        )
    ]
