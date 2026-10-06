# Prime TTC des grilles Voyage = colonne « Prime TTC » / « PTTC » des documents OREOLE.
#
# Les deux documents calculent taxe et TTC sur une prime nette non arrondie (classeur AMSA :
# E = (B + C) x 1,145 ; PDF NSIA : idem à 8 %). La 0069 avait recalculé taxe et TTC sur la
# prime nette arrondie : 1 F d'écart avec le document sur la taxe (3 lignes) ou la TTC
# (24 lignes AMSA, 23 NSIA). Chaque ligne reprend ici la TTC du document et la taxe vaut
# TTC - prime nette - accessoire (une quittance doit s'additionner) : prime nette, accessoire et
# TTC sont ceux du document ; la taxe ne s'écarte d'1 F de la colonne « taxe » du document que
# sur les lignes où le document lui-même ne s'additionne pas.
#
# Seules les lignes dont prime nette et accessoire sont encore ceux du document sont reprises
# (une ligne modifiée depuis dans l'admin est laissée telle quelle). Retour : taxe et TTC
# recalculées au taux sur la prime nette arrondie, comme la 0069.

import importlib
from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations

grilles_2026 = importlib.import_module("configuration_api.migrations.0069_grilles_voyage_oreole_2026")

# PTTC du PDF NSIA, dans l'ordre des durées de la 0069 (DUREES_NSIA, DUREES_ETUDIANT, DUREES_PELERINAGE)
PTTC_NSIA = {
    70: [19540, 22810, 28259, 29893, 35889, 39704, 42972, 60959, 68043, 79483, 138346],  # MONDIAL BASIC
    69: [7648, 8760, 9850, 12608, 13709, 17011, 19769, 27475, 31889, 45645, 86388],  # SCHENGEN
    68: [8401, 10471, 12019, 15649, 17197, 21338, 24445, 35323, 41012, 59651, 95347],  # EUROPE & SCHENGEN PLUS
    71: [7060, 8150, 9240, 11420, 12510, 15780, 17960, 25589, 29949, 44119, 84448],  # AFRIQUE
    74: [185245, 211404, 223394],  # ÉTUDIANT BASIC
    75: [168895, 189605, 212494],  # ÉTUDIANT PLUS
    76: [153636, 172165, 192875],  # ÉTUDIANT PREMIUM
    77: [9785, 19050, 24499],  # PÈLERINAGE BASIC
    78: [9240, 16870, 22319],  # PÈLERINAGE PLUS
    79: [7605, 13600, 19050],  # PÈLERINAGE DELUXE
}


def _franc(valeur):
    return Decimal(valeur).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _ttc_amsa():
    """(zone, âge min, durée min, prime nette, TTC) : TTC du classeur = (B x coefficient + 3 000) x 1,145."""
    lignes = []
    taux = 1 + grilles_2026.TAXE_AMSA / 100
    for zone, bases in grilles_2026.BASES_AMSA.items():
        for age_min, _, coefficient, zones in grilles_2026.AGES_AMSA:
            if zones and zone not in zones:
                continue
            for (d_min, _), base in zip(grilles_2026.DUREES_AMSA, bases):
                exacte = Decimal(base) * coefficient
                lignes.append((zone, age_min, d_min, _franc(exacte), _franc((exacte + grilles_2026.ACCESSOIRE_AMSA) * taux)))
    return lignes


def appliquer(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        for zone, age_min, d_min, prime_nette, ttc in _ttc_amsa():
            c.execute(
                """
                UPDATE stdzonevoyageprime SET prime_ttc = %s, taxe = %s - prime_nette - accessoire
                WHERE id_tarif = %s AND id_zone = %s AND age_minimum = %s AND duree_minimum = %s
                  AND prime_nette = %s AND accessoire = %s
                """,
                [ttc, ttc, grilles_2026.TARIF_AMSA, zone, age_min, d_min, prime_nette, grilles_2026.ACCESSOIRE_AMSA],
            )
        for id_offre, ttcs in PTTC_NSIA.items():
            _, frais, durees, primes = grilles_2026.GRILLE_NSIA[id_offre]
            for (d_min, d_max), prime_nette, ttc in zip(durees, primes, ttcs):
                c.execute(
                    """
                    UPDATE stdzonevoyageprimensia SET prime_ttc = %s, taxe = %s - prime_nette - accessoire
                    WHERE id_offre = %s AND id_zone IS NULL AND duree_minimum = %s AND duree_maximum = %s
                      AND prime_nette = %s AND accessoire = %s
                    """,
                    [ttc, ttc, id_offre, d_min, d_max, prime_nette, frais],
                )


def restaurer(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        for table in ("stdzonevoyageprime", "stdzonevoyageprimensia"):
            c.execute(
                f"""
                UPDATE {table} SET taxe = ROUND((prime_nette + accessoire) * taux_taxe / 100, 0),
                                   prime_ttc = prime_nette + accessoire + ROUND((prime_nette + accessoire) * taux_taxe / 100, 0)
                """
            )


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0070_statutjuridique"),
    ]

    operations = [
        migrations.RunPython(appliquer, restaurer),
    ]
