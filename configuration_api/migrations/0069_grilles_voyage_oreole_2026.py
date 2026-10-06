# Grilles Voyage reçues d'OREOLE (Desktop\_OREOLE ASSURANCE\VOYAGE) appliquées à la base :
#
# NSIA ASSURANCES (1) — « TARIF VOYAGE NSIA ASSURANCES.pdf » : prime nette par plan et par
# durée, sans âge (lignes valables de 0 à 120 ans, à confirmer avec NSIA), frais 8 000 (Mondial),
# 5 000 (Étudiant), 2 500 (autres), taxe 8 % de (prime nette + frais). La colonne « prime
# nette » du document fait foi (la colonne en devise est fausse ou vide sur certaines lignes).
#   Formule standard (105) : 70 MONDIAL BASIC, 69 SCHENGEN, 68 EUROPE & SCHENGEN PLUS, 71 AFRIQUE
#   Formule étudiant (106) : 74 BASIC, 75 PLUS, 76 PREMIUM (6 mois, 9 mois, 1 an seulement)
#   Formule pèlerinage (107) : 77 BASIC, 78 PLUS, 79 DELUXE (15, 30, 45 jours)
#   Offres 68 à 79 renommées (aucun devis enregistré dessus, hors un essai sur 68) ;
#   72 FAMILLE et 73 ECONOMIE désactivées (absentes du tarif).
#
# AMSA ASSURANCES (21) — « TARIFS Assurances voyages COVEREDGE - AMSACI - 03112025.xlsx » :
# base 18-65 ans par zone (Schengen, Afrique et Moyen-Orient, Monde entier) et par durée
# (7, 15, 32, 62, 93 jours, 6 mois, 12 mois) ; 0-17 ans : moitié ; 66-75 : x 2,5 ; 76-80 : x 3 ;
# 81-89 : x 4, Schengen seulement ; accessoire 3 000, taxe 14,5 %. Primes arrondies au franc
# depuis la valeur exacte du classeur. Appliquée au tarif « sans COVID » (108) ; le tarif
# « avec COVID » (109) n'a pas de grille dans le document : il n'est plus proposé.
#
# Durées en jours, date d'effet et date d'expiration comprises (« du … au … à minuit ») :
# 6 mois = 184 jours au plus, 9 mois = 276, 1 an = 366.
#
# Pays par zone : la destination donne la zone ; l'offre doit être proposée dans la zone
# (stdoffrevoyagezone). Schengen = 29 États membres (Bulgarie et Roumanie depuis 2025), Crète
# et « Schengen ». NSIA : Europe hors Schengen (Royaume-Uni, Irlande, Chypre, micro-États…),
# Afrique (continent africain), Monde entier (le reste) ; Mondial, Étudiant et Pèlerinage
# partout. AMSA : Europe hors Schengen en Monde entier (la zone « Europe-Afrique-Moyen-Orient »
# devient « Afrique et Moyen-Orient » dans le nouveau tarif) ; Émirats Arabes Unis rangés
# avec Dubaï. Tout se modifie dans l'admin (Paramétrage > Grilles Voyage).
#
# Les anciennes grilles, zones, pays et offres sont copiés dans des tables
# *_avant_grilles_2026_10 et restaurés par : python manage.py migrate configuration_api 0068

from decimal import ROUND_HALF_UP, Decimal

import django.db.models.deletion
from django.db import migrations, models

NSIA, AMSA = 1, 21
SAUVEGARDE = "avant_grilles_2026_10"
TABLES_SAUVEGARDEES = ["stdzonevoyageprime", "stdzonevoyageprimensia", "stdzonevoyagepays", "stdzonevoyage"]

SCHENGEN = [
    8, 17, 23, 34, 53, 55, 63, 64, 68, 69, 74, 83, 89, 91, 102, 106, 107, 108, 115, 134, 145, 148,
    149, 153, 154, 173, 174, 179, 180,  # 29 États membres
    52, 167,  # Crète, « Schengen »
]
EUROPE_HORS_SCHENGEN = [6, 9, 10, 27, 30, 43, 44, 88, 109, 122, 123, 126, 155, 156, 160, 169, 197, 200]
MOYEN_ORIENT_AMSA = [4, 13, 20, 58, 60, 86, 87, 94, 99, 103, 137, 150, 183, 195, 203]
ANGLETERRE = 10  # rangée par erreur dans le continent Afrique de stdpays

# ------------------------------------------------------------------ NSIA
TAXE_NSIA = Decimal("8")
DUREES_NSIA = [(1, 7), (8, 10), (11, 15), (16, 21), (22, 30), (31, 45), (46, 60), (61, 92), (93, 184), (185, 276), (277, 366)]
DUREES_ETUDIANT = [(93, 184), (185, 276), (277, 366)]
DUREES_PELERINAGE = [(1, 15), (16, 30), (31, 45)]
# offre : (libellé, frais, durées, primes nettes)
GRILLE_NSIA = {
    70: ("MONDIAL BASIC", 8000, DUREES_NSIA, [10092, 13120, 18166, 19679, 25231, 28763, 31789, 48443, 55003, 65596, 120098]),
    69: ("SCHENGEN", 2500, DUREES_NSIA, [4582, 5611, 6621, 9174, 10193, 13251, 15805, 22940, 27027, 39764, 77489]),
    68: ("EUROPE & SCHENGEN PLUS", 2500, DUREES_NSIA, [5278, 7196, 8629, 11990, 13423, 17258, 20134, 30206, 35474, 52732, 85785]),
    71: ("AFRIQUE", 2500, DUREES_NSIA, [4037, 5046, 6055, 8074, 9083, 12111, 14129, 21194, 25231, 38351, 75692]),
    74: ("BASIC", 5000, DUREES_ETUDIANT, [166523, 190745, 201846]),
    75: ("PLUS", 5000, DUREES_ETUDIANT, [151385, 170560, 191754]),
    76: ("PREMIUM", 5000, DUREES_ETUDIANT, [137255, 154412, 173588]),
    77: ("BASIC", 2500, DUREES_PELERINAGE, [6560, 15138, 20185]),
    78: ("PLUS", 2500, DUREES_PELERINAGE, [6055, 13120, 18166]),
    79: ("DELUXE", 2500, DUREES_PELERINAGE, [4542, 10092, 15138]),
}
OFFRES_NSIA_RETIREES = [72, 73]  # FAMILLE, ECONOMIE

# ------------------------------------------------------------------ AMSA
TAXE_AMSA = Decimal("14.5")
ACCESSOIRE_AMSA = 3000
TARIF_AMSA, TARIF_AMSA_COVID = 108, 109
OFFRES_AMSA = [80, 82]  # particulier, groupe (même grille)
ZONE_AMSA_SCHENGEN, ZONE_AMSA_MONDE, ZONE_AMSA_AFRIQUE_MO = 3, 4, 5
DUREES_AMSA = [(1, 7), (8, 15), (16, 32), (33, 62), (63, 93), (94, 184), (185, 366)]
BASES_AMSA = {  # 18-65 ans, valeurs exactes du classeur
    ZONE_AMSA_SCHENGEN: ["6002.81038", "10049.39622", "16531.05521", "23958.76496", "31530.1164", "39515.389599999995", "45503.60816"],
    ZONE_AMSA_AFRIQUE_MO: ["6002.81038", "10502.00655", "16904.9507", "24785.27078", "33399.593850000005", "40394.371979999996", "48737.47617"],
    ZONE_AMSA_MONDE: ["8543.5055", "12687.012209999999", "19384.468159999997", "29645.91215", "39795.1746", "48691.55918", "74063.97594"],
}
AGES_AMSA = [  # (âge min, âge max, coefficient, zones)
    (0, 17, Decimal("0.5"), None),
    (18, 65, Decimal("1"), None),
    (66, 75, Decimal("2.5"), None),
    (76, 80, Decimal("3"), None),
    (81, 89, Decimal("4"), [ZONE_AMSA_SCHENGEN]),
]


def _franc(valeur):
    return Decimal(valeur).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _ligne(prime_nette, accessoire, taux):
    prime_nette, accessoire = _franc(prime_nette), Decimal(accessoire)
    taxe = _franc((prime_nette + accessoire) * taux / 100)
    return prime_nette, accessoire, taxe, prime_nette + accessoire + taxe


def appliquer(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        # Contrôles des clés étrangères immédiats : pas d'événements de trigger en attente
        # avant les ALTER TABLE de la même transaction (retour arrière)
        c.execute("SET CONSTRAINTS ALL IMMEDIATE")
        for table in TABLES_SAUVEGARDEES:
            c.execute(f"CREATE TABLE {table}_{SAUVEGARDE} AS TABLE {table}")
        c.execute(
            f"CREATE TABLE stdoffre_voyage_{SAUVEGARDE} AS "
            "SELECT idoffre, libelleoffre, actif FROM stdoffre WHERE ppr = 'V'"
        )

        # Zones
        c.execute("UPDATE stdzonevoyage SET libelle_zone = 'EUROPE HORS SCHENGEN' WHERE id_zone = 6")
        c.execute("UPDATE stdzonevoyage SET libelle_zone = 'ZONE 3: AFRIQUE ET MOYEN-ORIENT' WHERE id_zone = %s", [ZONE_AMSA_AFRIQUE_MO])
        c.execute("INSERT INTO stdzonevoyage (libelle_zone, id_compagnie) VALUES ('SCHENGEN', %s) RETURNING id_zone", [NSIA])
        zone_nsia_schengen = c.fetchone()[0]
        c.execute("INSERT INTO stdzonevoyage (libelle_zone, id_compagnie) VALUES ('AFRIQUE', %s) RETURNING id_zone", [NSIA])
        zone_nsia_afrique = c.fetchone()[0]
        zone_nsia_europe, zone_nsia_monde = 6, 7

        # Pays par zone (une zone par pays et par compagnie)
        c.execute("SELECT id_pays, continent_id FROM stdpays")
        pays = dict(c.fetchall())
        afrique = {p for p, continent in pays.items() if continent == 1 and p != ANGLETERRE}

        def zone_nsia(p):
            if p in SCHENGEN:
                return zone_nsia_schengen
            if p in EUROPE_HORS_SCHENGEN:
                return zone_nsia_europe
            return zone_nsia_afrique if p in afrique else zone_nsia_monde

        def zone_amsa(p):
            if p in SCHENGEN:
                return ZONE_AMSA_SCHENGEN
            return ZONE_AMSA_AFRIQUE_MO if p in afrique or p in MOYEN_ORIENT_AMSA else ZONE_AMSA_MONDE

        c.execute(
            "DELETE FROM stdzonevoyagepays WHERE id_zone IN (SELECT id_zone FROM stdzonevoyage WHERE id_compagnie IN (%s, %s))",
            [NSIA, AMSA],
        )
        for p in sorted(pays):
            c.execute("INSERT INTO stdzonevoyagepays (id_pays, id_zone) VALUES (%s, %s), (%s, %s)", [p, zone_nsia(p), p, zone_amsa(p)])

        # Offres
        for id_offre, (libelle, *_) in GRILLE_NSIA.items():
            c.execute("UPDATE stdoffre SET libelleoffre = %s, actif = TRUE WHERE idoffre = %s", [libelle, id_offre])
        c.execute("UPDATE stdoffre SET actif = FALSE WHERE idoffre = ANY(%s)", [OFFRES_NSIA_RETIREES])

        toutes_nsia = [zone_nsia_schengen, zone_nsia_europe, zone_nsia_afrique, zone_nsia_monde]
        offres_zones = {
            69: [zone_nsia_schengen],
            68: [zone_nsia_schengen, zone_nsia_europe],
            71: [zone_nsia_afrique],
            70: toutes_nsia,
            **{o: toutes_nsia for o in (74, 75, 76, 77, 78, 79)},
            **{o: [ZONE_AMSA_SCHENGEN, ZONE_AMSA_AFRIQUE_MO, ZONE_AMSA_MONDE] for o in OFFRES_AMSA},
        }
        for id_offre, zones in offres_zones.items():
            for zone in zones:
                c.execute("INSERT INTO stdoffrevoyagezone (id_offre, id_zone) VALUES (%s, %s)", [id_offre, zone])

        # Grille NSIA par offre, valable dans toutes les zones de l'offre
        c.execute("DELETE FROM stdzonevoyageprimensia")
        for id_offre, (_, frais, durees, primes) in GRILLE_NSIA.items():
            for (d_min, d_max), prime in zip(durees, primes):
                pn, acc, taxe, ttc = _ligne(prime, frais, TAXE_NSIA)
                c.execute(
                    """
                    INSERT INTO stdzonevoyageprimensia (id_offre, id_zone, duree_minimum, duree_maximum, age_minimum,
                        age_maximum, prime_nette, accessoire, taxe, prime_ttc, taux_taxe, prime_nette_ristourne,
                        taxe_ristourne, prime_ttc_ristourne)
                    VALUES (%s, NULL, %s, %s, 0, 120, %s, %s, %s, %s, %s, 0, 0, 0)
                    """,
                    [id_offre, d_min, d_max, pn, acc, taxe, ttc, TAXE_NSIA],
                )

        # Grille AMSA par formule et par zone
        c.execute("DELETE FROM stdzonevoyageprime WHERE id_tarif IN (%s, %s)", [TARIF_AMSA, TARIF_AMSA_COVID])
        for zone, bases in BASES_AMSA.items():
            for age_min, age_max, coefficient, zones in AGES_AMSA:
                if zones and zone not in zones:
                    continue
                for (d_min, d_max), base in zip(DUREES_AMSA, bases):
                    pn, acc, taxe, ttc = _ligne(Decimal(base) * coefficient, ACCESSOIRE_AMSA, TAXE_AMSA)
                    c.execute(
                        """
                        INSERT INTO stdzonevoyageprime (id_tarif, id_zone, duree_minimum, duree_maximum, age_minimum,
                            age_maximum, prime_nette, accessoire, taxe, prime_ttc, taux_taxe, prime_nette_ristourne,
                            taxe_ristourne, prime_ttc_ristourne)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0)
                        """,
                        [TARIF_AMSA, zone, d_min, d_max, age_min, age_max, pn, acc, taxe, ttc, TAXE_AMSA],
                    )


def restaurer(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        c.execute("SET CONSTRAINTS ALL IMMEDIATE")
        c.execute("DELETE FROM stdoffrevoyagezone")
        for table in ["stdzonevoyageprimensia", "stdzonevoyageprime", "stdzonevoyagepays"]:
            c.execute(f"DELETE FROM {table}")
        c.execute(f"DELETE FROM stdzonevoyage WHERE id_zone NOT IN (SELECT id_zone FROM stdzonevoyage_{SAUVEGARDE})")
        c.execute(
            f"UPDATE stdzonevoyage z SET libelle_zone = s.libelle_zone FROM stdzonevoyage_{SAUVEGARDE} s WHERE s.id_zone = z.id_zone"
        )
        for table in ["stdzonevoyagepays", "stdzonevoyageprime", "stdzonevoyageprimensia"]:
            c.execute(f"INSERT INTO {table} SELECT * FROM {table}_{SAUVEGARDE}")
        c.execute(
            f"UPDATE stdoffre o SET libelleoffre = s.libelleoffre, actif = s.actif "
            f"FROM stdoffre_voyage_{SAUVEGARDE} s WHERE s.idoffre = o.idoffre"
        )
        for table in TABLES_SAUVEGARDEES + ["stdoffre_voyage"]:
            c.execute(f"DROP TABLE {table}_{SAUVEGARDE}")


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0068_bareme_nsia_securite_routiere_incendie"),
    ]

    operations = [
        migrations.AddField(
            model_name="zonevoyageprime",
            name="taux_taxe",
            field=models.DecimalField(db_column="taux_taxe", decimal_places=4, default=14.5, max_digits=7, verbose_name="Taux de taxe (%)"),
        ),
        migrations.AddField(
            model_name="zonevoyageprimensia",
            name="taux_taxe",
            field=models.DecimalField(db_column="taux_taxe", decimal_places=4, default=14.5, max_digits=7, verbose_name="Taux de taxe (%)"),
        ),
        migrations.AlterField(
            model_name="zonevoyageprimensia",
            name="zone_voyage",
            field=models.ForeignKey(
                blank=True,
                db_column="id_zone",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="primesvoyagensia",
                to="configuration_api.zonevoyage",
                verbose_name="Zone de voyage",
            ),
        ),
        migrations.CreateModel(
            name="OffreVoyageZone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "offre",
                    models.ForeignKey(
                        db_column="id_offre",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="zonesvoyage",
                        to="configuration_api.offre",
                        verbose_name="Offre",
                    ),
                ),
                (
                    "zone_voyage",
                    models.ForeignKey(
                        db_column="id_zone",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offresvoyage",
                        to="configuration_api.zonevoyage",
                        verbose_name="Zone de voyage",
                    ),
                ),
            ],
            options={
                "verbose_name": "Offre Voyage par zone",
                "verbose_name_plural": "Offres Voyage par zone",
                "db_table": "stdoffrevoyagezone",
                "constraints": [models.UniqueConstraint(fields=("offre", "zone_voyage"), name="offre_voyage_zone_unique")],
            },
        ),
        migrations.RunPython(appliquer, restaurer),
    ]
