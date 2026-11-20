"""Recalcul des primes d'un contrat corrigé dans l'Administration des contrats (production/recalcul_contrat.py)."""

from decimal import Decimal as D

from django.test import SimpleTestCase

from .recalcul_contrat import Contexte, calculer, repartir


def garantie(idgarantie, pn, taxe, pa=None, acquise=True):
    return {"idgarantie": idgarantie, "acquise": acquise, "primenette": D(pn), "primeannuelle": D(pa if pa is not None else pn),
            "taxe": D(taxe)}


def contrat(**montants):
    base = {
        "primeannuelle": D(0), "primenette": D(0), "accessoire": D(0), "accessoirecompagnie": D(0),
        "accessoireintermediaire": D(0), "accessoiregestionnaire": D(0), "taxe": D(0), "fga": D(0), "cedeao": D(0),
        "primettc": D(0), "commissionintermediaire": D(0), "taux_commission": D(0), "prime_imposee": False,
    }
    base.update({cle: D(v) if not isinstance(v, bool) else v for cle, v in montants.items()})
    return base


class RepartitionTests(SimpleTestCase):
    def test_somme_juste_aux_plus_forts_restes(self):
        parts = repartir(D(100), [("a", D(1)), ("b", D(1)), ("c", D(1))])
        self.assertEqual(sum(parts.values()), 100)
        self.assertEqual(sorted(parts.values()), [33, 33, 34])

    def test_poids_nuls_parts_egales(self):
        self.assertEqual(repartir(D(10), [("a", D(0)), ("b", D(0))]), {"a": 5, "b": 5})


class RecalculAutoTests(SimpleTestCase):
    """Véhicule calculé : RC 50 000, DR 10 000, CEDEAO 1 000 (garantie 3), FGA 500 sur le risque ; accessoire 5 000."""

    def setUp(self):
        self.ctx = Contexte(idproduit=1, taux_garanties={1: D("14.5"), 10: D("14.5")}, taux_produit=D("14.5"))
        self.avant = {
            "contrat": contrat(primeannuelle=61000, primenette=61500, accessoire=5000, accessoirecompagnie=2500,
                               accessoireintermediaire=2500, taxe=9425, fga=500, cedeao=1000, primettc=75925),
            "details": {
                7: {"primenette": D(61000), "primeannuelle": D(61000), "taxeenregistrement": D(8700), "fga": D(500),
                    "garanties": {71: garantie(1, 50000, 7250), 72: garantie(10, 10000, 1450), 73: garantie(3, 1000, 0)}},
            },
        }

    def test_prime_de_garantie_propagee_jusqu_a_la_ttc(self):
        r = calculer(self.ctx, self.avant, {"garanties": {72: {"primenette": D(20000)}}})
        self.assertEqual(r["garanties"][72], {"primenette": D(20000), "primeannuelle": D(20000), "taxe": D(2900)})
        self.assertEqual(r["details"][7]["primenette"], D(71000))
        self.assertEqual(r["details"][7]["taxeenregistrement"], D(10150))
        c = r["contrat"]
        self.assertEqual(c["primenette"], D(71500))
        # (prime nette hors FGA et CEDEAO + accessoire) x 14,5 % en une fois
        self.assertEqual(c["taxe"], D(10875))
        self.assertEqual(c["primettc"], D(71500) + D(5000) + D(10875))

    def test_garantie_decochee_retiree_des_totaux(self):
        r = calculer(self.ctx, self.avant, {"garanties": {72: {"acquise": False}}})
        self.assertEqual(r["details"][7]["primenette"], D(51000))
        self.assertEqual(r["contrat"]["primenette"], D(51500))
        self.assertEqual(r["contrat"]["taxe"], D(7975))

    def test_accessoire_seul_refait_taxe_ttc_et_partage(self):
        r = calculer(self.ctx, self.avant, {"contrat": {"accessoire": D(6000)}})
        self.assertEqual(r["contrat"]["taxe"], D(9570))
        self.assertEqual(r["contrat"]["primettc"], D(61500 + 6000 + 9570))
        self.assertEqual(r["contrat"]["accessoireintermediaire"], D(3000))
        self.assertEqual(r["contrat"]["accessoirecompagnie"], D(3000))

    def test_taxe_et_ttc_saisies_recalculees(self):
        r = calculer(self.ctx, self.avant, {"contrat": {"taxe": D(1), "primettc": D(2)}})
        self.assertEqual(r["contrat"]["taxe"], D(9425))
        self.assertEqual(r["contrat"]["primettc"], D(75925))

    def test_prime_nette_du_contrat_repartie_sur_les_garanties(self):
        r = calculer(self.ctx, self.avant, {"contrat": {"primenette": D(67500)}})
        g = r["garanties"]
        self.assertEqual(g[71]["primenette"] + g[72]["primenette"], D(66000))
        self.assertEqual(g[71]["primenette"], D(55000))
        self.assertNotIn(73, g)  # CEDEAO hors répartition
        self.assertEqual(r["contrat"]["primenette"], D(67500))
        self.assertEqual(r["contrat"]["taxe"], D(10295))

    def test_prime_imposee_cedeao_hors_prime_nette(self):
        self.ctx.cedeao_incluse = False
        self.avant["contrat"].update(primenette=D(60500), primettc=D(75925), prime_imposee=True)
        r = calculer(self.ctx, self.avant, {"garanties": {72: {"primenette": D(20000)}}})
        self.assertEqual(r["contrat"]["primenette"], D(70500))
        self.assertEqual(r["contrat"]["primettc"], D(70500) + D(1000) + D(5000) + D(10875))

    def test_commission_au_taux_suit_la_prime_ht(self):
        self.avant["contrat"].update(taux_commission=D(10), commissionintermediaire=D(6000))
        r = calculer(self.ctx, self.avant, {"garanties": {72: {"primenette": D(20000)}}})
        self.assertEqual(r["contrat"]["commissionintermediaire"], D(7000))

    def test_commission_convenue_gardee(self):
        self.avant["contrat"].update(taux_commission=D(10), commissionintermediaire=D(4321))
        r = calculer(self.ctx, self.avant, {"garanties": {72: {"primenette": D(20000)}}})
        self.assertNotIn("commissionintermediaire", r["contrat"])

    def test_rien_sans_prime_touchee(self):
        self.assertIsNone(calculer(self.ctx, self.avant, {"contrat": {"observation": "x"}, "details": {7: {"matricule": "AB"}}}))


class RecalculHorsAutoTests(SimpleTestCase):
    def test_taxes_des_garanties_et_de_l_accessoire(self):
        ctx = Contexte(idproduit=4, taux_garanties={30: D(25), 40: D("14.5")}, taux_produit=D("14.5"))
        avant = {
            "contrat": contrat(primenette=20000, primeannuelle=20000, accessoire=2000, taxe=4240, primettc=26240),
            "details": {1: {"primenette": D(20000), "primeannuelle": D(20000), "taxeenregistrement": D(3950), "fga": D(0),
                            "garanties": {11: garantie(30, 10000, 2500), 12: garantie(40, 10000, 1450),
                                          13: garantie(40, 10000, 0, acquise=False)}}},
        }
        r = calculer(ctx, avant, {"garanties": {13: {"acquise": True}}})
        self.assertEqual(r["garanties"][13]["taxe"], D(1450))
        self.assertEqual(r["details"][1]["primenette"], D(30000))
        self.assertEqual(r["contrat"]["taxe"], D(3950 + 1450 + 290))
        self.assertEqual(r["contrat"]["primettc"], D(30000 + 2000 + 5690))

    def test_taux_enregistre_autre_que_le_bareme_garde(self):
        # Dommages électriques taxés à 25 % à l'émission, 14,5 % au barème des taxes
        ctx = Contexte(idproduit=4, taux_garanties={40: D("14.5")}, taux_produit=D("14.5"))
        avant = {
            "contrat": contrat(primenette=302990, taxe=75748, primettc=378738),
            "details": {1: {"primenette": D(302990), "primeannuelle": D(302990), "taxeenregistrement": D(75748), "fga": D(0),
                            "garanties": {11: garantie(40, 302990, 75748)}}},
        }
        r = calculer(ctx, avant, {"garanties": {11: {"primenette": D(400000)}}})
        self.assertEqual(r["garanties"][11]["taxe"], D(100000))
        self.assertEqual(r["contrat"]["taxe"], D(100000))

    def test_garantie_jamais_taxee_reste_sans_taxe(self):
        ctx = Contexte(idproduit=10, taux_produit=D(0))
        avant = {
            "contrat": contrat(primenette=1000, primettc=1000),
            "details": {1: {"primenette": D(1000), "primeannuelle": D(1000), "taxeenregistrement": D(0), "fga": D(0),
                            "garanties": {11: garantie(900, 1000, 0)}}},
        }
        r = calculer(ctx, avant, {"garanties": {11: {"primenette": D(2000)}}})
        self.assertEqual(r["contrat"]["taxe"], D(0))
        self.assertEqual(r["contrat"]["primettc"], D(2000))

    def test_taxe_globale_gardee(self):
        ctx = Contexte(idproduit=8, taux_garanties={50: D("14.5")}, taux_produit=D("14.5"))
        avant = {
            "contrat": contrat(primenette=300000, accessoire=11500, taxe=45168, primettc=356668),
            "details": {1: {"primenette": D(300000), "primeannuelle": D(300000), "taxeenregistrement": D(43000), "fga": D(0),
                            "garanties": {11: garantie(50, 300000, 43000)}}},
        }
        r = calculer(ctx, avant, {"contrat": {"accessoire": D(12500)}})
        self.assertEqual(r["contrat"]["taxe"], D(45313))

    def test_offre_exoneree_sans_taxe(self):
        ctx = Contexte(idproduit=5, exonere=True, taux_garanties={98: D(8)}, taux_produit=D(8))
        avant = {
            "contrat": contrat(primenette=100000, accessoire=50000, primettc=150000),
            "details": {1: {"primenette": D(100000), "primeannuelle": D(100000), "taxeenregistrement": D(0), "fga": D(0),
                            "garanties": {11: garantie(98, 100000, 0)}}},
        }
        r = calculer(ctx, avant, {"garanties": {11: {"primenette": D(120000)}}})
        self.assertEqual(r["garanties"][11]["taxe"], D(0))
        self.assertEqual(r["contrat"]["taxe"], D(0))
        self.assertEqual(r["contrat"]["primettc"], D(170000))

    def test_transport_risques_sans_garanties(self):
        ctx = Contexte(idproduit=6, taux_produit=D("14.5"))
        avant = {
            "contrat": contrat(primenette=3000, taxe=210, primettc=3210),
            "details": {1: {"primenette": D(1000), "primeannuelle": D(1000), "taxeenregistrement": D(70), "fga": D(0), "garanties": {}},
                        2: {"primenette": D(2000), "primeannuelle": D(2000), "taxeenregistrement": D(140), "fga": D(0), "garanties": {}}},
        }
        r = calculer(ctx, avant, {"details": {2: {"primenette": D(3000)}}})
        self.assertEqual(r["details"][2]["taxeenregistrement"], D(210))
        self.assertEqual(r["contrat"]["primenette"], D(4000))
        self.assertEqual(r["contrat"]["taxe"], D(280))
        self.assertEqual(r["contrat"]["primettc"], D(4280))
        # Prime nette du contrat saisie : répartie sur les risques au prorata
        r = calculer(ctx, avant, {"contrat": {"primenette": D(6000)}})
        self.assertEqual((r["details"][1]["primenette"], r["details"][2]["primenette"]), (D(2000), D(4000)))
        self.assertEqual(r["contrat"]["primettc"], D(6000 + 420))

    def test_taux_de_commission_seul(self):
        ctx = Contexte(idproduit=2, taux_produit=D("14.5"))
        avant = {"contrat": contrat(primenette=100000, taxe=14500, primettc=114500, taux_commission=20,
                                    commissionintermediaire=20000), "details": None}
        r = calculer(ctx, avant, {"contrat": {"taux_commission": D(25)}})
        self.assertEqual(r["contrat"], {"commissionintermediaire": D(25000)})
