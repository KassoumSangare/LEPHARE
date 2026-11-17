# Taxe des devis Automobile (demande du 2026-11-17) : « la taxe est égale à (prime nette + accessoire) x 14,5 / 100 ».
# - sp_finalisation_devis v8 : pour l'Automobile, taxe calculée en une fois sur (prime nette hors FGA et CEDEAO
#   + accessoire), au lieu de la somme des taxes arrondies garantie par garantie (1 à 3 F d'écart pour un devis sur deux).
# Les devis et contrats déjà enregistrés ne sont pas touchés.
# Retour : python manage.py migrate production 0220

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0220_minene_package_choix"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_finalisation_devis", from_version=7, to_version=8)),
    ]
