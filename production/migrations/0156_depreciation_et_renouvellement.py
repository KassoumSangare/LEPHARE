# Compte rendu de la séance LE PHARE du 12-10-2026 (Automobile) : valeur vénale mise à jour selon l'âge au
# renouvellement, liste des véhicules (et des assurés) tenant compte des incorporations et retraits.
#
#   - fn_lephare_depreciation (nouvelle) : valeur vénale d'après le tableau de la CIEAMI réglé dans
#     l'administration (configuration_api 0084).
#   - fn_get_valeur_venale_vehicule v2 : passe par ce tableau (la table URANUS stddepreciationvehicule,
#     vide, rendait la valeur neuve au renouvellement).
#   - fn_liste_objets_assures v2 : une ligne par matricule (v1 : une par date d'effet, une flotte de
#     5 véhicules se renouvelait avec 1 véhicule, une IA de 15 assurés avec 2) ; retrait écarté seulement
#     s'il est postérieur à la ligne.
#   - sp_avenant_creation_devis_initial v4 : au renouvellement, valeur vénale de chaque véhicule d'après
#     son genre, son type, sa carrosserie, sa catégorie et sa charge utile ; conservée si le tableau ne
#     s'applique pas. v3 = définition en base (différente des v1 / v2 du dépôt).
# Retour : python manage.py migrate production 0155

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade, load_sql_version


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0155_minene_franchise_rc_reglee"),
        ("configuration_api", "0084_depreciation_vehicules"),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_lephare_depreciation", 1),
            "DROP FUNCTION IF EXISTS public.fn_lephare_depreciation(integer, integer, integer, character varying, numeric, numeric, date, date);"
            " DROP FUNCTION IF EXISTS public.fn_lephare_nombre_texte(numeric);",
        ),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_get_valeur_venale_vehicule", from_version=1, to_version=2)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_liste_objets_assures", from_version=1, to_version=2)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_avenant_creation_devis_initial", from_version=3, to_version=4)),
    ]
