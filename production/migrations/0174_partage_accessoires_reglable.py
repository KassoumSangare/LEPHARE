# Partage des accessoires compagnie / cabinet lu sur la fiche de la compagnie (Administration > Compagnies >
# Reversements, « Part du cabinet dans les accessoires » ; NSIA, SUNU et AMSA : 50 %) au lieu de ces trois compagnies
# écrites dans le code ; accessoires des offres IA CGA et CI-ÉNERGIES lus dans les Réglages IA (configuration_api 0102).
#   - fn_lephare_part_accessoires_cabinet (nouvelle) ;
#   - fn_get_accessoire v4, fn_garantie_offre_dommages v3, sp_creation_devis_voyage v3.
# Mêmes montants qu'avant avec les réglages d'origine. Retour : python manage.py migrate production 0173

from django.db import migrations

from uranus.utils.migrations import load_sql_version


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0173_tarif_ia_nsia_reglable"),
        ("configuration_api", "0102_accessoires_offres_ia_part_amsa"),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_lephare_part_accessoires_cabinet", 1),
            "DROP FUNCTION IF EXISTS public.fn_lephare_part_accessoires_cabinet(integer);",
        ),
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_get_accessoire", 4),
            load_sql_version(__file__, "functions/fn_get_accessoire", 3),
        ),
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_garantie_offre_dommages", 3),
            load_sql_version(__file__, "functions/fn_garantie_offre_dommages", 2),
        ),
        migrations.RunSQL(
            load_sql_version(__file__, "procedures/sp_creation_devis_voyage", 3),
            load_sql_version(__file__, "procedures/sp_creation_devis_voyage", 2),
        ),
    ]
