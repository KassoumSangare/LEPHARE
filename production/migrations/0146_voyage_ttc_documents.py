# Calcul Voyage aligné sur les documents OREOLE (voir configuration_api 0071) :
#   - fn_grille_voyage v2 : renvoie aussi la prime TTC du document et les bornes (durée, âge) de
#     la ligne retenue (type de retour modifié : suppression puis création) ;
#   - fn_garantie_offre_voyage v3 : sans réduction, taxe totale = TTC du document - prime nette -
#     accessoire (à 1 F près du calcul au taux), sinon taxe recalculée au taux.
# Retour : python manage.py migrate production 0145

from django.db import migrations
from uranus.utils.migrations import load_sql_upgrade, load_sql_version

SUPPRIMER_GRILLE = "DROP FUNCTION IF EXISTS public.fn_grille_voyage(integer, integer, integer, integer, integer);"


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0145_grilles_voyage_oreole_2026"),
        ("configuration_api", "0071_voyage_ttc_documents"),
    ]

    operations = [
        migrations.RunSQL(
            sql=load_sql_version(__file__, "functions/fn_grille_voyage", 2),
            reverse_sql=SUPPRIMER_GRILLE + "\n" + load_sql_version(__file__, "functions/fn_grille_voyage", 1),
        ),
        migrations.RunSQL(
            *load_sql_upgrade(__file__, "functions/fn_garantie_offre_voyage", from_version=2, to_version=3)
        ),
    ]
