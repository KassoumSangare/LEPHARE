# Numérotation des polices et devis selon les documents OREOLE « Codes catégorie - Numérotation »
# (AUTO, IA, TRANSPORT, VOYAGE) :
#   - Facultés terrestres : code catégorie 614 (le référentiel portait 618) ;
#   - un devis modifié vers une autre compagnie ou une autre catégorie de tarif reçoit un numéro
#     conforme (code courtier + code catégorie + année + D + n° + clé) : sp_aligner_numero_devis,
#     appelée par des déclencheurs différés sur stddevis et stddevisdetail.
# Retour : python manage.py migrate production 0146

from django.db import migrations
from uranus.utils.migrations import load_sql_pair


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0146_voyage_ttc_documents"),
    ]

    operations = [
        migrations.RunSQL(
            *load_sql_pair(
                __file__,
                "raw/categorie_facultes_terrestres_614.sql",
                "raw/categorie_facultes_terrestres_614_reverse.sql",
            )
        ),
        migrations.RunSQL(
            *load_sql_pair(
                __file__,
                "procedures/sp_aligner_numero_devis.sql",
                "procedures/sp_aligner_numero_devis_reverse.sql",
            )
        ),
        migrations.RunSQL(
            *load_sql_pair(
                __file__,
                "triggers/trg_aligner_numero_devis.sql",
                "triggers/trg_aligner_numero_devis_reverse.sql",
            )
        ),
    ]
