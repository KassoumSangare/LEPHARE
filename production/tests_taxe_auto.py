"""Taxe d'enregistrement Automobile : (prime nette hors FGA et CEDEAO + accessoire) x 14,5 / 100 (production/taxe_auto.py).

python manage.py test production.tests_taxe_auto (sans base de données)
"""
from decimal import Decimal

from django.test import SimpleTestCase

from .taxe_auto import taxe_auto, taxe_et_ttc_auto


class TaxeAuto(SimpleTestCase):
    def test_formule_en_une_fois(self):
        # Devis 26644 : (45 378 + 6 000) x 14,5 % = 7 449,81 -> 7 450, la taxe enregistrée par la base
        self.assertEqual(taxe_auto(45378, 6000), Decimal("7450"))
        # Devis 25225 : (152 008 + 9 000) x 14,5 % = 23 346,16 -> 23 346
        self.assertEqual(taxe_auto(Decimal("152008"), Decimal("9000")), Decimal("23346"))

    def test_demi_franc_arrondi_au_superieur(self):
        # 100 x 14,5 % = 14,5 -> 15, comme ROUND de PostgreSQL
        self.assertEqual(taxe_auto(100, 0), Decimal("15"))

    def test_valeurs_absentes(self):
        self.assertEqual(taxe_auto(None, None), Decimal("0"))

    def test_taxe_et_ttc_depuis_prime_nette_cedeao_comprise(self):
        # Écran « Imposer les primes » : prime nette 178 984 CEDEAO (1 000) comprise, accessoire 12 000, FGA 1 468
        taxe, ttc = taxe_et_ttc_auto(178984, 1000, 12000, 1468)
        self.assertEqual(taxe, Decimal("27548"))  # (177 984 + 12 000) x 14,5 % = 27 547,68
        self.assertEqual(ttc, Decimal("220000"))

    def test_taux_de_la_base(self):
        self.assertEqual(taxe_auto(10000, 0, Decimal("8")), Decimal("800"))

    def test_ligne_de_grille_a_lecture_directe(self):
        # Administration > Tarifs à lecture directe : taxe et TTC jamais saisies, TTC = somme exacte (sans arrondi)
        from configuration_api.parametrage_auto import _taxe_et_ttc

        montants = {"PrimeNette": Decimal("117265"), "Accessoire": Decimal("9000"), "Fga": Decimal("1468"), "Cedeao": Decimal("1000")}
        self.assertEqual(_taxe_et_ttc(montants), {"Taxe": Decimal("18308"), "PrimeTtc": Decimal("147041")})
