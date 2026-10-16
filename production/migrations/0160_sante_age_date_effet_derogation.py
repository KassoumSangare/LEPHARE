# Santé : import du fichier « FAMILLE LEROLL 2025 » refusé (« Âge limite dépassé. Assuré rejeté. », constaté le
# 2026-10-15 sur le devis 26165) : la saisie mesurait l'âge au jour de la saisie, la tarification à la date d'effet.
#
# sp_saisie_adherent_sante v4, sp_saisie_affilie_sante v5 :
#   - âge apprécié à la date d'effet du devis saisie à l'écran (posée par LE PHARE : lephare.date_effet_age ; à
#     défaut, StdFiliale.date_effet), comme sp_creation_devis_sante, et non au jour de la saisie ;
#   - limites d'âge (adulte MINENE, enfant sans ou avec certificat) dépassables par dérogation : LE PHARE pose
#     lephare.derogation_age = 'on' sur sa connexion pour un utilisateur habilité (droit devis.derogation_age) ;
#   - message de refus avec l'âge, la date et la limite ; dérogation rappelée dans le message de réussite.
# fn_get_surprime_age_minene_sante v3 : au-delà de l'âge maximum (assuré admis par dérogation), taux de la dernière
# tranche (65 ans et plus) au lieu de 0.
# Retour : python manage.py migrate production 0159

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0159_arrondi_primes_ttc"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_saisie_adherent_sante", from_version=3, to_version=4)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_saisie_affilie_sante", from_version=4, to_version=5)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_get_surprime_age_minene_sante", from_version=2, to_version=3)),
    ]
