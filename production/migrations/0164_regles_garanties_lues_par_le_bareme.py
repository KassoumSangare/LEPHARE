# Admin plus autonome (demande du 2026-10-16 : « éviter les interventions techniques sur le code source ») :
#   - fn_lephare_regle_auto v1 : règle des garanties Automobile appliquée par le barème (Administration > Réglages
#     Automobile > Règles des garanties, case « Appliquée aussi par le barème ») ;
#   - fn_garantie_offre_cat1_nsia, _cat2_nsia, _cat3_nsia v3 : bris de glace et recours anticipé offerts, défense-recours
#     4 200 F avec les dommages ou la collision lus dans ces règles au lieu d'être écrits dans le code ;
#   - fn_retenir_garantie_nsia_auto_plus v2 : âge minimum de NSIA Auto Plus lu dans « Dépréciation et âge des véhicules ».
# Résultats du moteur identiques avant / après (342 calculs, 38 offres NSIA).
# Retour : python manage.py migrate production 0163

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade, load_sql_version

RETRAIT = "DROP FUNCTION IF EXISTS public.fn_lephare_regle_auto(integer, integer, integer, integer, character varying);"


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0163_frais_gestion_minene_contrat"),
        ("configuration_api", "0091_regles_appliquees_bareme"),
    ]

    operations = [
        migrations.RunSQL(load_sql_version(__file__, "functions/fn_lephare_regle_auto", 1), RETRAIT),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_cat1_nsia", from_version=2, to_version=3)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_cat2_nsia", from_version=2, to_version=3)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_cat3_nsia", from_version=2, to_version=3)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_retenir_garantie_nsia_auto_plus", from_version=1, to_version=2)),
    ]
