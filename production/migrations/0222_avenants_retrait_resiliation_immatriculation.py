# Avenants de retrait, de résiliation et de changement d'immatriculation (demande du 2026-11-19, production/avenants.py).
# - fn_liste_objets_assures v3 : une ligne d'avenant CHI (changement d'immatriculation) entre dans les objets en vigueur de
#   la police, et l'immatriculation qu'elle remplace (stdcontratdetail.oldmatricule) en sort ; sans elle, le renouvellement,
#   l'incorporation et le retrait garderaient l'ancienne plaque.
# Les retraits (RET) et résiliations (RES) en sortaient déjà les objets concernés (v2).
# Retour : python manage.py migrate production 0221

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0221_taxe_auto_prime_nette_accessoire"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_liste_objets_assures", from_version=2, to_version=3)),
    ]
