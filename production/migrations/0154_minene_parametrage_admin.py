# MINENE SANTÉ : la base lit les réglages de l'administration (Réglages Santé MINENE, configuration_api
# 0083) au lieu de valeurs écrites dans les fonctions. Valeurs d'origine conservées à défaut de réglage :
# les devis calculés avant et après la migration sont identiques.
#
#   - fn_lephare_parametre_nombre (nouvelle) : valeur numérique d'un paramètre lephare_parametre.
#   - fn_minene_personnes_max (nouvelle) : taille maximale d'une famille par formule (lephare_sante_formule).
#   - fn_get_prime_base_minene_sante v2 : prime de la formule (lephare_sante_formule).
#   - fn_get_surprime_affection_minene_sante v2, fn_get_surprime_age_minene_sante v2 : taux et âges réglés.
#   - fn_get_capitaux_minene_ia / _rc v2, fn_get_prime_base_minene_ia / _rcc v2 : capitaux et primes IA / RC.
#   - fn_get_frais_gestion_minene(produit) (nouvelle) et fn_get_frais_gestion_minene() v2 : forfaits ADEC IA
#     et RC de la répartition de la prime Santé MINENE (stdrepartitionprimesante).
#   - fn_get_accessoire_sante_minene v2 : taxe sur l'accessoire au taux Santé de la table des taxes (8 %).
#   - sp_saisie_adherent_sante v3, sp_saisie_affilie_sante v4 : âges, affections et taille de famille réglés.
#   - sp_creation_devis_sante v6 : taille de famille par formule réglée.
#   - sp_creation_devis_risques_divers v3 (RC MINENE) et sp_finalisation_devis v5 (IA MINENE) : taxe d'un
#     adhérent calculée sur sa prime et son accessoire (2 976 F écrits jusqu'ici, valeur inchangée avec la
#     prime de 14 524 F) ; frais de gestion ADEC du produit.
# Retour : python manage.py migrate production 0153

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade, load_sql_version

FONCTIONS_MODIFIEES = [
    "fn_get_prime_base_minene_sante",
    "fn_get_surprime_affection_minene_sante",
    "fn_get_surprime_age_minene_sante",
    "fn_get_capitaux_minene_ia",
    "fn_get_capitaux_minene_rc",
    "fn_get_prime_base_minene_ia",
    "fn_get_prime_base_minene_rcc",
    "fn_get_accessoire_sante_minene",
]

PROCEDURES = [
    ("sp_saisie_adherent_sante", 2, 3),
    ("sp_saisie_affilie_sante", 3, 4),
    ("sp_creation_devis_sante", 5, 6),
    ("sp_creation_devis_risques_divers", 2, 3),
    ("sp_finalisation_devis", 4, 5),
]


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0153_dommages_calcul_identique_uranus"),
        ("configuration_api", "0083_sante_minene_parametrage"),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_lephare_parametre_nombre", 1),
            "DROP FUNCTION IF EXISTS public.fn_lephare_parametre_nombre(character varying, numeric);",
        ),
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_minene_personnes_max", 1),
            "DROP FUNCTION IF EXISTS public.fn_minene_personnes_max(integer);",
        ),
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_get_frais_gestion_minene_produit", 1),
            "DROP FUNCTION IF EXISTS public.fn_get_frais_gestion_minene(integer);",
        ),
        # Après la fonction à un paramètre qu'elle appelle ; retour à la v1 avant la suppression de celle-ci
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_get_frais_gestion_minene", from_version=1, to_version=2)),
        *[
            migrations.RunSQL(*load_sql_upgrade(__file__, f"functions/{nom}", from_version=1, to_version=2))
            for nom in FONCTIONS_MODIFIEES
        ],
        *[
            migrations.RunSQL(*load_sql_upgrade(__file__, f"procedures/{nom}", from_version=avant, to_version=apres))
            for nom, avant, apres in PROCEDURES
        ],
    ]
