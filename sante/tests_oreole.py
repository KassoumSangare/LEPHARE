"""Calcul de la cotisation Oreole Santé, sans base de données : python manage.py test sante.tests_oreole"""
from decimal import Decimal as D

from django.test import SimpleTestCase

from sante.oreole import ErreurOreole, taux_age, tarifer_adherent, ventiler_reglement

REGLES = {"SurprimeAffection": D(30), "Age1Debut": 60, "Age1Taux": D(30), "Age2Debut": 65, "Age2Taux": D(50), "Carte": D(3000)}
OFFRE_436 = {"cotisation": D(436800), "primeht": D(123333), "accessoires": D(10000), "partia": D(6000), "partafa": D(7500), "enfantsupplementaire": D(35000)}
OFFRE_400 = {"cotisation": D(400000), "primeht": D(123333), "accessoires": D(10000), "partia": D(0), "partafa": D(0), "enfantsupplementaire": D(35000)}
OFFRE_575 = {"cotisation": D(575000), "primeht": D(300000), "accessoires": D(5000), "partia": D(17000), "partafa": D(15000), "enfantsupplementaire": D(70000)}


class TarifOreole(SimpleTestCase):
    def test_decomposition_des_fichiers_tarifs(self):
        t = tarifer_adherent(OFFRE_436, {"Age": 40}, REGLES)
        self.assertEqual(t["Cotisation"], 436800)
        self.assertEqual(t["PartSante"], 423300)
        self.assertEqual(t["FraisCourtiers"], 289967)  # 244 209 de frais + 45 758 de la colonne taxes
        t = tarifer_adherent(OFFRE_575, {"Age": 40}, REGLES)
        self.assertEqual(t["PartSante"], 543000)
        self.assertEqual(t["FraisCourtiers"], 238000)

    def test_affection_sur_le_cumul_ia_et_afa_inchangees(self):
        t = tarifer_adherent(OFFRE_436, {"Age": 40, "Affections": 1}, REGLES)
        self.assertEqual(t["Cotisation"], 567840)  # 436 800 x 1,30
        self.assertEqual((t["PartIA"], t["PartAFA"]), (6000, 7500))
        self.assertEqual(t["PrimeHt"], 123333)  # le supplément va aux frais courtiers
        self.assertEqual(t["FraisCourtiers"], 289967 + 131040)

    def test_age_sur_la_part_sante(self):
        t = tarifer_adherent(OFFRE_436, {"Age": 62}, REGLES)
        self.assertEqual(t["SurprimeAge"], 126990)  # 423 300 x 30 %
        self.assertEqual(t["Cotisation"], 563790)
        t = tarifer_adherent(OFFRE_436, {"Age": 66}, REGLES)
        self.assertEqual(t["SurprimeAge"], 211650)  # 423 300 x 50 %

    def test_taux_age_par_tranche(self):
        self.assertEqual(taux_age(59, REGLES), 0)
        self.assertEqual(taux_age(60, REGLES), 30)
        self.assertEqual(taux_age(65, REGLES), 50)
        self.assertEqual(taux_age(None, REGLES), 0)

    def test_taux_saisis_remplacent_les_taux_calcules(self):
        t = tarifer_adherent(OFFRE_436, {"Age": 62, "Affections": 2, "TauxAffection": D(40), "TauxAge": D(0)}, REGLES)
        self.assertEqual(t["Cotisation"], 611520)  # 436 800 x 1,40

    def test_surprime_imposee_remplace_les_surprimes(self):
        t = tarifer_adherent(OFFRE_436, {"Age": 66, "Affections": 1, "SurprimeImposee": D(10000)}, REGLES)
        self.assertEqual(t["Cotisation"], 446800)

    def test_enfants_en_plus(self):
        t = tarifer_adherent(OFFRE_436, {"Age": 40, "EnfantsEnPlus": 2}, REGLES)
        self.assertEqual(t["Cotisation"], 506800)
        self.assertEqual(t["MontantEnfants"], 70000)

    def test_carte_seulement_si_cochee(self):
        self.assertEqual(tarifer_adherent(OFFRE_436, {"Age": 40, "Personnes": 3}, REGLES)["MontantCartes"], 0)
        t = tarifer_adherent(OFFRE_436, {"Age": 40, "Personnes": 3}, REGLES, carte=True)
        self.assertEqual(t["MontantCartes"], 9000)
        self.assertEqual(t["Cotisation"], 445800)

    def test_cotisation_imposee_du_fichier(self):
        t = tarifer_adherent(OFFRE_436, {"Age": 62, "Affections": 1, "CotisationImposee": D(400400)}, REGLES)
        self.assertEqual(t["Cotisation"], 400400)
        self.assertEqual(t["SurprimeAffection"], 0)
        self.assertEqual(t["SurprimeAge"], 0)
        self.assertEqual(t["PartSante"], 386900)

    def test_produit_lie_retire_retire_sa_part(self):
        t = tarifer_adherent(OFFRE_436, {"Age": 40, "PartIA": D(0)}, REGLES)
        self.assertEqual(t["Cotisation"], 430800)
        self.assertEqual(t["PartSante"], 423300)

    def test_prix_negocie(self):
        t = tarifer_adherent(OFFRE_436, {"Age": 40}, REGLES, prix_famille=D(400400))
        self.assertEqual(t["Cotisation"], 400400)
        self.assertEqual(t["FraisCourtiers"], 400400 - 13500 - 133333)

    def test_sante_seule(self):
        t = tarifer_adherent(OFFRE_400, {"Age": 40, "Affections": 1}, REGLES)
        self.assertEqual(t["Cotisation"], 520000)
        self.assertEqual(t["PartSante"], 520000)

class ReglementCommun(SimpleTestCase):
    QUITTANCES = [
        {"NumeroQuittance": "S", "PrimeTtc": D(423300), "Encaisse": D(0)},
        {"NumeroQuittance": "I", "PrimeTtc": D(6000), "Encaisse": D(0)},
        {"NumeroQuittance": "A", "PrimeTtc": D(7500), "Encaisse": D(0)},
    ]

    @staticmethod
    def _parts(lignes):
        return {l["numero_quittance"]: D(l["montant_encaissement"]) for l in lignes}

    def test_le_total_solde_les_trois_quittances(self):
        self.assertEqual(self._parts(ventiler_reglement(self.QUITTANCES, D(436800))), {"S": D(423300), "I": D(6000), "A": D(7500)})

    def test_un_acompte_au_prorata_sans_ecart(self):
        parts = self._parts(ventiler_reglement(self.QUITTANCES, D(100000)))
        self.assertEqual(sum(parts.values()), D(100000))
        self.assertEqual(parts["I"], D(1373))
        self.assertEqual(parts["A"], D(1717))

    def test_un_acompte_presque_complet_ne_depasse_aucune_part(self):
        parts = self._parts(ventiler_reglement([{"NumeroQuittance": "S", "PrimeTtc": D(50), "Encaisse": D(0)}, {"NumeroQuittance": "I", "PrimeTtc": D(30), "Encaisse": D(0)},
                                                {"NumeroQuittance": "A", "PrimeTtc": D(20), "Encaisse": D(0)}], D(99)))
        self.assertEqual(sum(parts.values()), D(99))
        self.assertLessEqual(parts["S"], D(50))
        self.assertLessEqual(parts["I"], D(30))
        self.assertLessEqual(parts["A"], D(20))

    def test_une_quittance_deja_soldee_est_ecartee(self):
        quittances = [{**self.QUITTANCES[0], "Encaisse": D(423300)}, *self.QUITTANCES[1:]]
        self.assertEqual(self._parts(ventiler_reglement(quittances, D(13500))), {"I": D(6000), "A": D(7500)})

    def test_un_montant_trop_eleve_ou_nul_est_refuse(self):
        with self.assertRaises(ErreurOreole):
            ventiler_reglement(self.QUITTANCES, D(436801))
        with self.assertRaises(ErreurOreole):
            ventiler_reglement(self.QUITTANCES, D(0))
