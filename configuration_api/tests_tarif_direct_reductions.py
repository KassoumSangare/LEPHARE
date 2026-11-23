"""Tarif Auto à lecture directe : réduction commerciale et BNS déduits comme au barème (2026-11-23). Tests sans base."""
from decimal import Decimal
from unittest import mock

from django.test import SimpleTestCase

from configuration_api import parametrage_auto as pa


def ligne(id_sous_garantie, prime_nette, acquise=True):
    return {"idsousgarantie": id_sous_garantie, "primenette": Decimal(prime_nette), "acquise": acquise}


# Barème d'un véhicule NSIA (RC, CEDEAO, recours, incendie) et ligne cumul (idsousgarantie 0)
SANS_TAUX = [ligne(0, 99999), ligne(1, 60000), ligne(3, 1000), ligne(4, 4000), ligne(10, 6000)]
# BNS 25 % sur tout sauf la CEDEAO, réduction commerciale 35 % hors RC
AVEC_TAUX = [ligne(0, 99999), ligne(1, 45000), ligne(3, 1000), ligne(4, 1950), ligne(10, 2925)]


class PrimesNettesDuBareme(SimpleTestCase):
    def test_hors_cedeao_fga_et_cumul(self):
        self.assertEqual(pa._primes_nettes_bareme(SANS_TAUX + [ligne(2, 1200)]), (Decimal(70000), Decimal(60000)))

    def test_garanties_non_acquises_ecartees(self):
        self.assertEqual(pa._primes_nettes_bareme([ligne(1, 60000), ligne(10, 6000, acquise=False)]), (Decimal(60000), Decimal(60000)))


class CoefficientsDesReductions(SimpleTestCase):
    def test_sans_taux_aucun_appel_au_bareme(self):
        with mock.patch.object(pa, "_lignes_bareme") as bareme:
            self.assertEqual(pa.coefficients_reductions({"TauxReduction": "0", "Bns": ""}), (1, 1))
        bareme.assert_not_called()

    def test_rapport_des_primes_du_bareme_avec_et_sans_taux(self):
        appels = []

        def bareme(donnees, reduction, bns):
            appels.append((Decimal(reduction), Decimal(bns)))
            return AVEC_TAUX if bns else SANS_TAUX

        with mock.patch.object(pa, "_lignes_bareme", side_effect=bareme):
            coefficient_pn, coefficient_rc = pa.coefficients_reductions({"TauxReduction": "35", "Bns": "25"})
        self.assertEqual(appels, [(Decimal(35), Decimal(25)), (Decimal(0), Decimal(0))])
        self.assertEqual(coefficient_pn, Decimal(49875) / Decimal(70000))
        self.assertEqual(coefficient_rc, Decimal("0.75"))

    def test_sans_rc_au_bareme_bns_seul(self):
        with mock.patch.object(pa, "_lignes_bareme", return_value=[ligne(3, 1000)]):
            self.assertEqual(pa.coefficients_reductions({"TauxReduction": "10", "Bns": "20"}), (Decimal("0.8"), Decimal("0.8")))


class LibelleDesReductions(SimpleTestCase):
    def test_libelles(self):
        self.assertEqual(pa._reductions_texte(Decimal(25), Decimal(35)), "BNS 25 % et réduction commerciale 35 % déduits")
        self.assertEqual(pa._reductions_texte(Decimal(25), Decimal(0)), "BNS 25 % déduit")
        self.assertEqual(pa._reductions_texte(Decimal(0), Decimal("12.50")), "réduction commerciale 12,5 % déduite")
        self.assertEqual(pa._reductions_texte(Decimal(0), Decimal(0)), "")
