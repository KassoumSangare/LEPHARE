# Demandes du 2026-10-19 :
#   - « quand on impose une prime, faire apparaître cette prime sur les fiches » : sp_maj_manuelle_primes (fin de toute
#     imposition : correction d'un devis Auto, récapitulatif d'une flotte, « Modifier » du registre) n'écrivait que
#     l'en-tête du devis / contrat / quittance ; ses garanties gardaient les primes du barème, que les conditions
#     particulières et la liste des véhicules impriment. sp_lephare_ventiler_prime_imposee les ramène à la prime
#     imposée (prorata des primes calculées, taxe recalculée à son taux), sur le devis et sur le contrat qui en est issu ;
#     sp_maj_manuelle_primes v2 l'appelle. Les devis et contrats déjà enregistrés ne sont pas touchés ici.
#   - « quand le bouton NSIA Auto Plus est coché, faire apparaître NSIA Auto+ dans les garanties » :
#     fn_retenir_garantie_nsia_auto_plus v3, case cochée = garantie retenue quels que soient l'âge et l'offre.
# Retour : python manage.py migrate production 0166 (procédure d'URANUS et règle v2 rétablies)

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade, load_sql_version


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0166_bordereaux_reversement_commission_ht"),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_version(__file__, "procedures/sp_lephare_ventiler_prime_imposee", 1),
            "DROP PROCEDURE IF EXISTS public.sp_lephare_ventiler_prime_imposee(integer);",
        ),
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_maj_manuelle_primes", from_version=1, to_version=2)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_retenir_garantie_nsia_auto_plus", from_version=2, to_version=3)),
    ]
