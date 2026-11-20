# AMSA ne partage pas ses accessoires (correction de l'utilisateur du 2026-11-20 ; réglage mis à 0 % par configuration_api 0111).
# Les calculs IA qui partageaient encore l'accessoire par moitié écrite dans le code lisent la part du cabinet réglée sur la
# fiche de la compagnie (fn_lephare_part_accessoires_cabinet), comme fn_get_accessoire depuis 0174 :
#   - sp_creation_devis_ia v5 : prime imposée (NSIA, SUNU et AMSA à 50/50 écrits ici, autres refusées) ;
#   - sp_finalisation_devis v9 : IA de groupe à prime imposée (50/50 pour toutes ; moitié gardée sans réglage) ;
#   - fn_garantie_offre_ia v4 : offres IA personnalisées 173 et 174 (idem).
# Mêmes montants qu'avant pour NSIA et SUNU (50 %). Les contrats reprennent déjà la part réglée à leur enregistrement
# (déclencheur trg_lephare_commission_courtier). Retour : python manage.py migrate production 0223

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0223_sante_prestation_detail_minene"),
        ("configuration_api", "0111_amsa_sans_partage_accessoires"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_creation_devis_ia", from_version=4, to_version=5)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_finalisation_devis", from_version=8, to_version=9)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_ia", from_version=3, to_version=4)),
    ]
