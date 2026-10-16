# Vérification du barème Automobile NSIA (2026-10-16) :
#   - devis URANUS 118620126D4478V (Tous risques, 10 CV essence et diesel, 31 jours) : le barème de la base retrouve
#     chaque garantie au franc près (sécurité routière 5 places : 7 650 F, valeur corrigée le 2026-09-25 d'après une CP
#     NSIA ; URANUS est resté à 6 000 F) ;
#   - conditions particulières NSIA du véhicule 35493WWCI01 (EBENE PREMIUM TPC, devis 24777) : chaque garantie au franc
#     près, sauf le recours anticipé, facturé 6 825 F au barème et 0 F par NSIA (« attribué sans prime » avec les dommages
#     ou la collision, tarif annoté NSIA, toutes catégories).
#
# fn_garantie_offre_cat1_nsia, _cat2_nsia, _cat3_nsia v2 : recours anticipé sans prime avec les dommages ou la collision.
# Défense-recours inchangée (4 200 F sur la prime nette, comme URANUS) ; la règle d'écran « 4 240 F » passe à 4 200 F.
# Retour : python manage.py migrate production 0161

from decimal import Decimal

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


def regle_recours_4200(apps, schema_editor):
    Regle = apps.get_model("configuration_api", "AutoRegleInteraction")
    Regle.objects.filter(IdCompagnie=1, IdSousGarantie=4, Type="PRIME_SI", PrimeAnnuelle=Decimal("4240")).update(
        PrimeAnnuelle=Decimal("4200"),
        Commentaire="Défense-recours : forfait de 4 200 F (au lieu de 7 950 F) avec les dommages au véhicule ou la collision "
                    "(prime nette d'URANUS ; le tarif annoté indique 4 240 F).",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0161_coefficients_duree_parametrables"),
        ("configuration_api", "0090_auto_regles_interactions"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_cat1_nsia", from_version=1, to_version=2)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_cat2_nsia", from_version=1, to_version=2)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre_cat3_nsia", from_version=1, to_version=2)),
        migrations.RunPython(regle_recours_4200, migrations.RunPython.noop),
    ]
