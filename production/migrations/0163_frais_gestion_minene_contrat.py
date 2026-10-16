# Frais de gestion MINENE (fichier « TARIFICATION MINENE SANTE » : FRAIS DE GESTION ADEC 1 500 F par assuré principal
# et par contrat, en IA et en RC chef de famille) : comptés dans la prime TTC du devis (stddevis.accessoiregestionnaire),
# ils n'étaient pas repris par le contrat (stdcontrat.accessoiregestionnaire à 0), dont la prime TTC (25 000 F)
# dépassait alors prime nette + accessoire + taxe (23 500 F).
#
#   - sp_confirmation_devis v3 : le contrat reprend les frais de gestion du devis ;
#   - contrats déjà émis : frais de gestion recopiés de leur devis (5 contrats IA/RC MINENE au 2026-10-16).
# Retour : python manage.py migrate production 0162 (la procédure revient à la v2 ; les montants recopiés restent).

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade

RECOPIE = """
UPDATE stdcontrat AS c
SET accessoiregestionnaire = d.accessoiregestionnaire
FROM stddevis AS d
WHERE d.iddevis = c.iddevis
  AND COALESCE(c.accessoiregestionnaire, 0) = 0
  AND COALESCE(d.accessoiregestionnaire, 0) > 0;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0162_nsia_recours_anticipe_offert"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_confirmation_devis", from_version=2, to_version=3)),
        migrations.RunSQL(RECOPIE, migrations.RunSQL.noop),
    ]
