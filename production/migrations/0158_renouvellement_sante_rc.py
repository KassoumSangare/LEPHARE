# Renouvellement d'un contrat Santé ou RC refusé : « la colonne « idcontratdetail » de la relation
# « stdcomplementdevisdetailsante » n'existe pas » (constaté le 2026-10-13 sur le contrat Santé 21809).
#
# sp_avenant_creation_devis_initial v5 (v4 = définition en base) :
#   - les compléments Santé et RC du devis de renouvellement sont écrits sur IdDevisDetail (la v3 d'URANUS, reprise
#     en v4, écrivait dans une colonne IdContratDetail absente des tables de devis, avec une variable non déclarée) ;
#   - Santé : couvertures (filiales), adhérents et affiliés du contrat de base reconduits sur le devis, au nom de
#     l'opérateur, saisie Santé ouverte (bloc de la v2 chargée par la migration 0130, disparu de la base depuis ;
#     filiales recopiées en plus pour que chaque famille garde sa formule MINENE).
# Retour : python manage.py migrate production 0157

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0157_pool_tpv"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_avenant_creation_devis_initial", from_version=4, to_version=5)),
    ]
