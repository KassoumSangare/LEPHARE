# Conditions Particulières Auto (fn_liste_garanties_souscrites) : colonnes « BNS » et « Autres » (réduction commerciale)
# des garanties (demande du 2026-11-23 : faire apparaître le BNS sur la CP).
#  - Le BNS n'était lu que si le véhicule avait une option d'assistance : 0 % imprimé sur presque toutes les CP
#    (2 572 devis et 1 791 contrats avec un BNS en base locale, un seul avec une option d'assistance).
#  - Les taux de chaque garantie suivent désormais le moteur de la compagnie (fn_lephare_auto_taux_reduction_cp) :
#    NSIA (BNS sur le bris de glace toits ouvrants depuis 0141, réduction commerciale sur le recours), AMSA et SUNU
#    (taux imprimés, auparavant toujours 0), Pool TPV sans réduction.
# Les montants ne changent pas : seuls les taux imprimés sont corrigés.

from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade, load_sql_version


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0226_rafas_mouvements"),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_lephare_auto_taux_reduction_cp", 1),
            "DROP FUNCTION IF EXISTS public.fn_lephare_auto_taux_reduction_cp(integer, character varying, integer, character varying, numeric);",
        ),
        migrations.RunSQL(
            *load_sql_upgrade(
                __file__,
                "functions/fn_liste_garanties_souscrites",
                from_version=1,
                to_version=2,
            )
        ),
    ]
