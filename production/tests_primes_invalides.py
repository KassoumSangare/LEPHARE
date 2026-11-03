from decimal import Decimal

from django.test import SimpleTestCase

from .import_assures import ValidationError, valider_monetaire
from .views_cockpit import _franc


class CelluleVideTests(SimpleTestCase):
    """Une cellule vide d'un fichier Excel arrive en « nan » (pandas) : elle ne doit jamais devenir un montant."""

    def test_cellule_vide_vaut_zero(self):
        for valeur in (float("nan"), "nan", "NaN", "", "  ", None):
            with self.subTest(valeur=valeur):
                self.assertEqual(valider_monetaire(valeur, "PRIME HT"), Decimal("0"))

    def test_montant_conserve(self):
        self.assertEqual(valider_monetaire("1500,50", "PRIME HT"), Decimal("1500.50"))
        self.assertEqual(valider_monetaire(4240, "PRIME HT"), Decimal("4240"))

    def test_valeur_non_numerique_refusee(self):
        for valeur in ("inf", "abc"):
            with self.subTest(valeur=valeur), self.assertRaises(ValidationError):
                valider_monetaire(valeur, "PRIME HT")


class TotauxTests(SimpleTestCase):
    def test_prime_invalide_comptee_pour_zero(self):
        self.assertEqual(_franc(Decimal("NaN")), 0)
        self.assertEqual(_franc(None), 0)
        self.assertEqual(_franc(Decimal("1500.4")), 1500)
