# Dommages : tarification identique à URANUS (comparaison du 2026-10-11 sur dix saisies identiques,
# fn_garantie_offre_tousrisquesinfo d'URANUS contre fn_garantie_offre_dommages de LE PHARE) :
#   - prime saisie (taux 0) + réduction : URANUS ignore la réduction, LE PHARE l'appliquait
#     (Caution 12 000 F, réduction 10 % : 18 091 F TTC au lieu de 19 465 F) ;
#   - capitaux et taux impairs : LE PHARE arrondissait la prime de chaque garantie avant la taxe
#     (TRI à 0,333 % : 40 889 F au lieu de 40 887 F).
# fn_garantie_offre_dommages v2 reprend ces deux règles d'URANUS. Un seul devis Dommages saisi dans
# LE PHARE (26061, prime saisie sans réduction) : aucun devis enregistré n'est modifié.
# Retour : python manage.py migrate production 0152

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0152_commission_minene_oreole"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_dommages", from_version=1, to_version=2)),
    ]
