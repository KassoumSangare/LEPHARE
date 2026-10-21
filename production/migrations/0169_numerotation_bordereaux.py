# Numérotation des bordereaux calquée sur celle des polices (demande du 2026-10-20) :
#   code courtier + catégorie de la CP de la première prime + mois + exercice + « B » + n° séquentiel du mois
#   (ex. 11862011026B0001). Une seule suite par courtier et par mois pour les encaissements, les bordereaux de
#   reversement et de réclamation, les récapitulatifs de réclamation et les paiements de commissions.
# - fn_lephare_numero_bordereau + compteur lephare_numero_bordereau ;
# - sp_enregistrement_encaissement v5 : numéro de pièce par cette fonction (date d'encaissement) ;
# - lephare_bordereau_reversement.numero : texte (ancienne suite 2117, 2118… gardée telle quelle).
# Les numéros déjà attribués ne changent pas.
# Retour : python manage.py migrate production 0168

from django.db import migrations, models

from uranus.utils.migrations import load_sql_upgrade, load_sql_version

RETRAIT_FONCTION = """
DROP FUNCTION IF EXISTS public.fn_lephare_numero_bordereau(character varying, date);
DROP TABLE IF EXISTS public.lephare_numero_bordereau;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0168_encaissement_ordre_reglement_default"),
    ]

    operations = [
        migrations.RunSQL(load_sql_version(__file__, "functions/fn_lephare_numero_bordereau", 1), RETRAIT_FONCTION),
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_enregistrement_encaissement", from_version=4, to_version=5)),
        migrations.AlterField(
            model_name="bordereaureversement",
            name="numero",
            field=models.CharField(db_column="numero", max_length=20),
        ),
    ]
