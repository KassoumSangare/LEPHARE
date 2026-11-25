"""Chiffre d'affaires du cabinet (courtier : commissions et accessoires, demande du 2026-11-12) : assemblage des lectures,
sans base de données."""
from datetime import date

from django.test import SimpleTestCase

from . import views_finance
from .chiffre_affaires import assembler, ventiler_reste

EN_COURS = {"debut": date(2026, 1, 1), "au": date(2026, 11, 12), "debut_n1": date(2025, 1, 1), "au_n1": date(2025, 11, 12)}
CLOS = {"debut": date(2025, 1, 1), "au": date(2025, 12, 31), "debut_n1": date(2024, 1, 1), "au_n1": date(2024, 12, 31)}
SANS_RAFAS = {"Lignes": [], "NonReglee": 0.0}
SANS_APPORTEUR = {"Payees": 0.0, "APayer": 0.0}


def acte(annee, mois, commission, accessoires=0, pn=0, nombre=1, comparable=True):
    return {"annee": annee, "mois": mois, "comparable": comparable, "nombre": nombre, "commission": commission,
            "accessoires": accessoires, "pn": pn}


def percu(source, jour, montant, produit=1, compagnie=1):
    return {"source": source, "jour": jour, "montant": montant, "idproduit": produit, "idcompagnie": compagnie}


class ChiffreAffairesAcquis(SimpleTestCase):
    def test_commissions_et_accessoires_du_cabinet(self):
        ca = assembler(EN_COURS, [acte(2026, 3, 100_000, 5_000, 400_000), acte(2026, 11, 20_000, 1_000, 100_000)], [], SANS_RAFAS, SANS_APPORTEUR)
        self.assertEqual((ca["Total"], ca["Commissions"], ca["Accessoires"]), (126_000, 120_000, 6_000))
        self.assertEqual(ca["TauxMoyen"], 25.2)  # 126 000 sur 500 000 de prime nette
        self.assertEqual(ca["ParMois"][2]["ChiffreAffaires"], 105_000)

    def test_comparaison_a_la_meme_date_de_l_an_dernier(self):
        lignes = [acte(2026, 1, 50_000), acte(2025, 1, 30_000), acte(2025, 12, 70_000, comparable=False)]
        ca = assembler(EN_COURS, lignes, [], SANS_RAFAS, SANS_APPORTEUR)
        self.assertEqual(ca["Precedent"], 30_000)  # décembre 2025 hors de la même période
        self.assertEqual(ca["ParMois"][11]["ChiffreAffairesPrecedent"], 70_000)  # mais dans le graphique

    def test_mois_a_venir_sans_chiffre(self):
        ca = assembler(EN_COURS, [acte(2026, 1, 10_000)], [], SANS_RAFAS, SANS_APPORTEUR)
        self.assertIsNone(ca["ParMois"][11]["ChiffreAffaires"])
        self.assertEqual(ca["ParMois"][10]["ChiffreAffaires"], 0)
        clos = assembler(CLOS, [acte(2025, 12, 10_000)], [], SANS_RAFAS, SANS_APPORTEUR)
        self.assertEqual(clos["ParMois"][11]["ChiffreAffaires"], 10_000)

    def test_montant_invalide_compte_pour_zero(self):
        ca = assembler(EN_COURS, [acte(2026, 2, float("nan"), 2_000)], [], SANS_RAFAS, SANS_APPORTEUR)
        self.assertEqual(ca["Total"], 2_000)

    def test_rafas_dans_le_chiffre_d_affaires(self):
        rafas = {"Lignes": [{"sens": "emis", "jour": date(2026, 6, 30), "nombre": 1, "montant": 650_000, "base": 10_000_000},
                            {"sens": "regle", "jour": date(2026, 7, 15), "nombre": 1, "montant": 650_000, "base": 0},
                            {"sens": "emis", "jour": date(2025, 6, 30), "nombre": 1, "montant": 500_000, "base": 8_000_000}],
                 "NonReglee": 100_000}
        ca = assembler(EN_COURS, [acte(2026, 6, 50_000, pn=200_000)], [], rafas, SANS_APPORTEUR)
        self.assertEqual((ca["Total"], ca["Rafas"], ca["Precedent"]), (700_000, 650_000, 500_000))
        self.assertEqual(ca["TauxMoyen"], 25.0)  # RAFAS à part : pas de prime d'assurance
        self.assertEqual((ca["Percu"]["Rafas"], ca["EnAttente"]["Rafas"]), (650_000, 100_000))
        self.assertEqual(ca["ParMois"][5]["ChiffreAffaires"], 700_000)


class ChiffreAffairesPercu(SimpleTestCase):
    def test_sources_et_repartition(self):
        lignes = [percu("Compagnies", date(2026, 4, 2), 80_000, produit=1, compagnie=7),
                  percu("FraisCourtiers", date(2026, 11, 3), 12_500, produit=5, compagnie=29),
                  percu("Reprises", date(2026, 2, 1), 9_000, produit=1, compagnie=7),
                  percu("Compagnies", date(2025, 4, 2), 40_000), percu("Compagnies", date(2025, 12, 2), 99_000)]
        ca = assembler(EN_COURS, [], lignes, SANS_RAFAS, SANS_APPORTEUR, en_attente={"AReclamer": 15_000, "Reclamees": 5_000})
        self.assertEqual(ca["Percu"], {"Total": 101_500, "Compagnies": 80_000, "FraisCourtiers": 12_500, "Reprises": 9_000, "Rafas": 0})
        self.assertEqual(ca["PercuPrecedent"], 40_000)  # décembre 2025 hors de la même période
        self.assertEqual(ca["PercuParProduit"], {1: 89_000, 5: 12_500})
        self.assertEqual(ca["PercuParCompagnie"], {7: 89_000, 29: 12_500})
        self.assertEqual(ca["ParMois"][3]["Percu"], 80_000)
        self.assertEqual(ca["EnAttente"]["Total"], 20_000)

    def test_net_des_apporteurs(self):
        ca = assembler(EN_COURS, [acte(2026, 5, 300_000)], [], SANS_RAFAS, {"Payees": 25_000, "APayer": 50_000})
        self.assertEqual((ca["Apporteurs"]["Total"], ca["Net"]), (75_000, 225_000))


def quittance(ca, exercice=True, encaisse=0, lephare=None, reverse=0, paye=0, payee=0, reclamations=(), oreole=False,
              reprise=False, ttc=0, direct=0):
    """Ligne de chiffre_affaires.lire_reste : commission de la quittance et où en est sa prime, situation au jour."""
    return {"ca": ca, "exercice": exercice, "oreole": oreole, "reprise_percue": reprise, "primettc": ttc, "encaisse": encaisse,
            "encaisse_lephare": encaisse if lephare is None else lephare, "encaisse_direct": direct, "reverse": reverse, "reverse_paye": paye,
            "payee": payee, "reclamations": list(reclamations)}


class ResteAPercevoir(SimpleTestCase):
    """Demande du 2026-11-24 : le cadre reprend l'écran Reversements aux compagnies, la commission rangée à l'étape où attend sa
    prime ; chiffre d'affaires de la période = déjà perçu sur ses actes + reste à percevoir."""

    LIGNES = [
        quittance(10_000),                                                              # prime à encaisser
        quittance(20_000, encaisse=100_000),                                            # encaissée, à reverser
        quittance(15_000, encaisse=100_000, direct=100_000),                            # payée à la compagnie : réclamation directe
        quittance(12_000, encaisse=100_000, direct=40_000),                             # en partie au cabinet : à reverser
        quittance(30_000, encaisse=100_000, reverse=100_000),                           # bordereau émis, paiement à saisir
        quittance(40_000, encaisse=100_000, reverse=40_000, paye=40_000),               # acompte reversé : commission due
        quittance(50_000, encaisse=100_000, reverse=100_000, paye=100_000, payee=20_000, reclamations=[7]),
        quittance(60_000, encaisse=200_000, reverse=200_000, paye=200_000, payee=60_000, reclamations=[8]),  # payée
        quittance(70_000, encaisse=300_000, lephare=0),                                 # encaissée sous URANUS
        quittance(80_000, oreole=True, ttc=1_000_000, encaisse=250_000),                # Oreole Santé : 1/4 gardé
        quittance(5_000, reprise=True),                                                 # reprise, commission perçue
        quittance(9_000, exercice=False, encaisse=50_000),                              # antérieur à reverser
        quittance(4_000, exercice=False, encaisse=50_000, reverse=50_000, paye=50_000),  # antérieur à réclamer
        quittance(3_000, exercice=False, encaisse=50_000, lephare=0),                   # antérieur sous URANUS : à part
    ]
    RAFAS = {"Lignes": [], "NonReglee": 9_999, "Periode": {"NombreNonReglee": 1, "NonReglee": 6_500, "Reglee": 1_000}}

    def test_etapes_de_la_prime(self):
        r = ventiler_reste(self.LIGNES, self.RAFAS)
        self.assertEqual(r["AEncaisser"], {"Nombre": 2, "Montant": 70_000})  # 10 000 + 3/4 des 80 000 d'Oreole Santé
        self.assertEqual(r["AReverser"], {"Nombre": 2, "Montant": 32_000})
        self.assertEqual(r["ADirect"], {"Nombre": 1, "Montant": 15_000})
        self.assertEqual(r["BordereauxAPayer"], {"Nombre": 1, "Montant": 30_000})
        self.assertEqual(r["AReclamer"], {"Nombre": 1, "Montant": 40_000})
        self.assertEqual(r["Reclamees"], {"Nombre": 1, "Montant": 30_000, "Bordereaux": 1})  # bordereau 8 payé en entier
        self.assertEqual(r["EncaisseesUranus"], {"Nombre": 1, "Montant": 70_000})
        self.assertEqual(r["Rafas"], {"Nombre": 1, "Montant": 6_500})
        self.assertEqual(r["Total"], 293_500)
        self.assertEqual(r["DejaPercu"], 106_000)  # 20 000 + 60 000 payés, 20 000 Oreole Santé, 5 000 reprise, 1 000 RAFAS

    def test_chiffre_d_affaires_egal_au_percu_plus_le_reste(self):
        actes = [acte(2026, 3, sum(l["ca"] for l in self.LIGNES if l["exercice"]))]
        rafas = {**self.RAFAS, "Lignes": [{"sens": "emis", "jour": date(2026, 5, 2), "nombre": 2, "montant": 7_500, "base": 0}]}
        ca = assembler(EN_COURS, actes, [], rafas, SANS_APPORTEUR, en_attente={}, reste=self.LIGNES)
        self.assertEqual(ca["ResteAPercevoir"]["DejaPercu"] + ca["ResteAPercevoir"]["Total"], ca["Total"])

    def test_anterieurs_hors_total(self):
        r = ventiler_reste(self.LIGNES)
        self.assertEqual(r["Anterieurs"]["Nombre"], 2)
        self.assertEqual(r["Anterieurs"]["Montant"], 13_000)
        self.assertEqual((r["Anterieurs"]["AReverser"]["Montant"], r["Anterieurs"]["AReclamer"]["Montant"]), (9_000, 4_000))
        self.assertEqual(r["Rafas"], {"Nombre": 0, "Montant": 0})

    def test_sans_lecture_du_reste(self):
        ca = assembler(EN_COURS, [acte(2026, 3, 10_000)], [], SANS_RAFAS, SANS_APPORTEUR)
        self.assertNotIn("ResteAPercevoir", ca)


def ligne_commission(id_reclamation, date_reclamation, due, payee=0):
    return {"IdReclamation": id_reclamation, "DateReclamation": date_reclamation, "CommissionDue": due,
            "CommissionPayee": payee, "Reste": max(due - payee, 0)}


class CumulReclamations(SimpleTestCase):
    """Cadre « Reste à percevoir » (demande du 2026-11-20) : réclamations de commission cumulées de l'exercice, payées comprises."""

    LIGNES = [
        ligne_commission(7, "2026-03-10", 100_000, payee=100_000),   # réclamation de mars, payée
        ligne_commission(9, "2026-10-02", 40_000, payee=15_000),     # réclamation d'octobre, deux quittances
        ligne_commission(9, "2026-10-02", 60_000),
        ligne_commission(4, "2025-12-15", 80_000),                   # exercice précédent
        ligne_commission(None, None, 25_000),                        # pas encore réclamée
    ]

    def test_cumul_de_l_exercice(self):
        cumul = views_finance.cumul_reclamations(self.LIGNES, date(2026, 1, 1), date(2026, 11, 20))
        self.assertEqual(cumul, {"Montant": 200_000, "Payees": 115_000, "Reste": 85_000, "Nombre": 2})

    def test_exercice_clos(self):
        cumul = views_finance.cumul_reclamations(self.LIGNES, date(2025, 1, 1), date(2025, 12, 31))
        self.assertEqual(cumul, {"Montant": 80_000, "Payees": 0, "Reste": 80_000, "Nombre": 1})

    def test_borne_au_jour(self):
        cumul = views_finance.cumul_reclamations(self.LIGNES, date(2026, 1, 1), date(2026, 9, 30))
        self.assertEqual((cumul["Montant"], cumul["Nombre"]), (100_000, 1))
