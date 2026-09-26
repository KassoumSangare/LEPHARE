# Aligne le barème automobile NSIA sur les montants des documents NSIA reçus d'OREOLE.
#
# Sécurité routière, FORMULE I NSIA : le prix dépend du nombre de places, alors que
# le barème appliquait 6 000 F partout.
#   - 3 places (le moteur ramène 1 à 3 places sur cette ligne) : 5 400 F
#     (CP NSIA EBENE PREMIUM TPC, 2 places ; devis émis à 2 et 3 places)
#   - 5 places : 7 650 F (CP NSIA AXES MARKETING validée par OREOLE, CP AFRICOGE et
#     TRAORE ; 58 des 87 devis émis à 5 places)
#   - 7 places : 10 345 F (20 devis émis à 7 places)
#   4, 6, 8 et 9 places restent à 6 000 F : aucune source (NSIA, OREOLE, URANUS) ne
#   donne leur montant.
#
# Incendie, grilles TPC boisées (202 : BAOBAB, EBENE, EBENE PRISME) : NSIA applique
# 2,5 ‰ au-delà de 10 M de valeur vénale (CP EBENE PREMIUM TPC, 23 453 555 F ->
# 58 634 F), et non 3,5 ‰ comme la tranche ajoutée sur ces trois grilles.

from django.db import migrations

SECURITE_ROUTIERE = [
    # (idformule, nombreplace, ancien montant, nouveau montant)
    (1, 3, 6000, 5400),
    (14, 5, 6000, 7650),
    (4, 7, 6000, 10345),
]

INCENDIE_TPC_BOISEES = [1059, 1060, 1061]  # stdtarifdetail.iddetail, tarifs 121/122/123


def _sql_securite_routiere(sens):
    return [
        f"UPDATE stdformulesecuriteroutiere SET primenette = {nouveau if sens == 'avant' else ancien} "
        f"WHERE idformule = {idformule} AND idcompagnie = 1 AND libelleformule = 'FORMULE I' "
        f"AND nombreplace = {places};"
        for idformule, places, ancien, nouveau in SECURITE_ROUTIERE
    ]


def _sql_incendie(taux):
    ids = ", ".join(str(i) for i in INCENDIE_TPC_BOISEES)
    return [
        f"UPDATE stdtarifdetail SET taux = {taux} WHERE iddetail IN ({ids}) "
        f"AND idtarif IN (121, 122, 123) AND idgarantie = 10 AND capitalmin = 10000001;"
    ]


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0067_seed_repartitionprimesante"),
    ]

    operations = [
        migrations.RunSQL(
            sql=_sql_securite_routiere("avant") + _sql_incendie(2.5),
            reverse_sql=_sql_securite_routiere("arriere") + _sql_incendie(3.5),
        ),
    ]
