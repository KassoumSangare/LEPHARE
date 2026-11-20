# Règlement des ristournes en caisse (2026-11-20) : remboursement au client ou imputation sur une autre prime
# (production/ristournes.py). sp_enregistrement_encaissement v7 : une quittance négative (avenant de retrait ou de
# résiliation) se règle par un montant négatif, partiel compris ; solde du client, plafond et reliquat lus dans l'autre
# sens. Quittances positives : calculs inchangés. Retour : python manage.py migrate production 0224

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0224_ia_partage_accessoires_reglable"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_enregistrement_encaissement", from_version=6, to_version=7)),
    ]
