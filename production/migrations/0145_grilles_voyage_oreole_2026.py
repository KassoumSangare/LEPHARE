# Calcul Voyage sur les grilles OREOLE 2026 (configuration_api 0069) :
#   - fn_grille_voyage : ligne de grille (prime nette, accessoire, taux de taxe), par offre (NSIA)
#     ou par formule et zone (AMSA), l'offre devant être proposée dans la zone ;
#   - fn_garantie_offre_voyage : prime sur les frais médicaux (29, comme l'enregistrement), arrondie
#     au franc après réduction, accessoire de la grille, taxe au taux de la grille sur prime nette +
#     accessoire, durée en jours de couverture (effet et expiration compris) ;
#   - sp_creation_devis_voyage : reprend ces montants tels quels (devis = écran) ;
#   - fn_liste_offre_voyage / fn_liste_tarif_voyage : offres et formules proposées par zone.
# Retour au calcul d'URANUS : python manage.py migrate production 0144

from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade, load_sql_version


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0144_tarif_ia_nsia"),
        ("configuration_api", "0069_grilles_voyage_oreole_2026"),
    ]

    operations = [
        migrations.RunSQL(
            sql=load_sql_version(__file__, "functions/fn_grille_voyage", 1),
            reverse_sql="DROP FUNCTION IF EXISTS public.fn_grille_voyage(integer, integer, integer, integer, integer);",
        ),
        migrations.RunSQL(
            *load_sql_upgrade(__file__, "functions/fn_calcul_prime_voyage_by_age", from_version=1, to_version=2)
        ),
        migrations.RunSQL(
            *load_sql_upgrade(__file__, "functions/fn_garantie_offre_voyage", from_version=1, to_version=2)
        ),
        migrations.RunSQL(
            *load_sql_upgrade(__file__, "procedures/sp_creation_devis_voyage", from_version=1, to_version=2)
        ),
        migrations.RunSQL(
            *load_sql_upgrade(__file__, "functions/fn_liste_offre_voyage", from_version=1, to_version=2)
        ),
        migrations.RunSQL(
            *load_sql_upgrade(__file__, "functions/fn_liste_tarif_voyage", from_version=1, to_version=2)
        ),
    ]
