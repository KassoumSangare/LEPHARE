# Tarif annoté NSIA (« COMMENTAIRE ANNOTE TARIF AUTOMOBILE NSIA CI », catégories 1 à 12) relu feuille par feuille le
# 2026-10-17 ; règles de la base alignées sur le texte (configuration_api 0094) :
#   - fn_lephare_regle_auto v2 : règle « prime minimum » (PRIME_MINIMUM) lue par le barème, garanties liées facultatives ;
#   - fn_garantie_offre_cat1_nsia, _cat2_nsia, _cat3_nsia v4 : prime minimum appliquée à la prime annuelle tarifée ;
#     catégorie 2 : le transport d'hydrocarbures ne majore plus que l'incendie et l'explosion (le vol et le vol des
#     accessoires étaient doublés) ; catégorie 3 : vol des accessoires et vandalisme tarifés (0 F auparavant),
#     franchise des dommages et du bris de glace lue dans l'offre (50 000 F étaient écrits dans le code) ;
#   - fn_garantie_offre_tpv v2 (Pool TPV, catégorie 204) : l'offre « assureur » ne plante plus (« l'enregistrement
#     v_pool n'est pas encore affecté » : tout devis TPV hors Pool était impossible à calculer).
# Retour : python manage.py migrate production 0164

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0164_regles_garanties_lues_par_le_bareme"),
        ("configuration_api", "0094_regles_tarif_annote_relues"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_lephare_regle_auto", from_version=1, to_version=2)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_cat1_nsia", from_version=3, to_version=4)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_cat2_nsia", from_version=3, to_version=4)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_cat3_nsia", from_version=3, to_version=4)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_tpv", from_version=1, to_version=2)),
    ]
