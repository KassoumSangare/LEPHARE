"""Tableau de bord des consommations : état des cotisations, rapprochement entreprise / police, tranches d'âge, score. Sans base de données."""

import io
from decimal import Decimal as D

from django.test import SimpleTestCase
from openpyxl import Workbook

from .consommations import _lire, exercice_du_fichier
from .consommations_pilotage import entreprises_a_risque, proposer_liens, tranche

ENTETE = ["Entreprises", " Effectifs par entreprise ", "OPTIONS", "Primes HT par personnes", "Primes HT par entreprise ", "Primes TTC Oreole santé encaisées",
          "Primes IA", "Primes AFA ", "Cotisations santé pure", "Honoraires MCI (11%)", "Commissions (7%)", "Apporteurs d'affaires",
          "Provisions pour paiement de dépenses de santé"]


def classeur(feuilles):
    wb = Workbook()
    wb.remove(wb.active)
    for titre, lignes in feuilles:
        ws = wb.create_sheet(titre)
        for l in lignes:
            ws.append(l)
    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


class EtatDesCotisations(SimpleTestCase):
    def test_feuille_des_donnees_lue_total_ecarte(self):
        contenu = classeur([("DONNER 2026", [ENTETE, ["SM PUB", 20, 3, 123333, 2466660, 8693180, 120000, 150000, 8423180, 271332.6, 172666.2, 100000, 7879181.2],
                                             ["Total", 20, None, None, 2466660, None, None, None, 8423180, None, None, None, 7879181.2]])])
        cotisations = _lire(contenu)[4]
        self.assertEqual(len(cotisations), 1)
        self.assertEqual(cotisations[0]["entreprise"], "SM PUB")
        self.assertEqual(cotisations[0]["provision"], D("7879181.2"))
        self.assertEqual(cotisations[0]["apporteurs"], D("100000"))
        self.assertEqual(cotisations[0]["effectif"], 20)

    def test_feuille_de_pilotage_ecartee(self):
        pilotage = ["ENTREPRISES", "PRIMES HT", "COTISATION SANTE PURE", "PROVISION POUR PAIEMENT DE DEPENSES", "CONSOMMATION PAR ENTREPRISE"]
        contenu = classeur([("DONNER 2026", [ENTETE, ["SM PUB", 20, 3, 0, 0, 0, 0, 0, 8423180, 0, 0, 0, 7879181.2]]),
                            ("CONTRÔLE", [pilotage, ["SM PUB", 1, 2, 3, 4]])])
        self.assertEqual([c["provision"] for c in _lire(contenu)[4]], [D("7879181.2")])

    def test_exercice_du_nom_du_fichier(self):
        self.assertEqual(exercice_du_fichier("ETAT 2026.xlsx"), 2026)
        self.assertEqual(exercice_du_fichier("ETAT.xlsx", {1: {"date_cloture": __import__("datetime").date(2025, 7, 31)}}), 2025)


class RapprochementDesNoms(SimpleTestCase):
    POLICES = ["PHARMACIE & LABORATOIRE LONGCHAMP", "VISION NOUVELLE EN TECHNOLOGIE (VNT)", "YAM CGA", "CGA LES HIRONDELLES", "OREOLE SANTE", "OREOLE SANTE PLUS",
               "BLOOMFIELD INVESTMENT", "BLOOMFIELD INTELLIGENCE", "TYM MEDICAL SOLUTIONS"]

    def test_propositions(self):
        p = proposer_liens(["PHARMACIE LONGCHAMP", "CGA POUR COMPTE VNT", "OREOLE SANTE", "OREOLE SANTE PLUS", "CGA HIRONDELLES"], self.POLICES, {})
        self.assertEqual(p, {"PHARMACIE LONGCHAMP": "PHARMACIE & LABORATOIRE LONGCHAMP", "CGA POUR COMPTE VNT": "VISION NOUVELLE EN TECHNOLOGIE (VNT)",
                             "OREOLE SANTE": "OREOLE SANTE", "OREOLE SANTE PLUS": "OREOLE SANTE PLUS", "CGA HIRONDELLES": "CGA LES HIRONDELLES"})

    def test_ambiguite_sans_proposition(self):
        self.assertEqual(proposer_liens(["BLOOMFIELD"], self.POLICES, {}), {})

    def test_une_police_pour_une_seule_entreprise(self):
        p = proposer_liens(["TYM MEDICAL", "MEDICAL SERVICE & SARL IDD"], self.POLICES, {})
        self.assertEqual(p, {"TYM MEDICAL": "TYM MEDICAL SOLUTIONS"})

    def test_lien_confirme_prioritaire(self):
        self.assertEqual(proposer_liens(["TYM MEDICAL", "AUTRE"], self.POLICES, {"AUTRE": "TYM MEDICAL SOLUTIONS"}), {})


class TranchesEtScore(SimpleTestCase):
    def test_tranches_du_rapport(self):
        self.assertEqual([tranche(a) for a in (0, 7, 8, 18, 30, 31, 55, 56, None)],
                         ["0-7 ans", "0-7 ans", "8-11 ans", "16-18 ans", "26-30 ans", "31-40 ans", "41-55 ans", "56 et plus", "Non renseigné"])

    def test_score_et_alertes(self):
        def p(police, benef, montant):
            return {"police": police, "matricule_beneficiaire": benef, "mt_rembourse": D(montant), "mt_reclame": D(montant), "date_naissance": None}
        prestations = [p("A", 1, 1000), p("A", 2, 1000), p("B", 3, 5000)] + [p("B", 3, 5000) for _ in range(11)]
        lignes, _portefeuille = entreprises_a_risque(prestations, [], None)
        b = next(l for l in lignes if l["Police"] == "B")
        a = next(l for l in lignes if l["Police"] == "A")
        self.assertGreater(b["Score"], 1)
        self.assertIn("Trop d'actes", b["Alertes"])
        self.assertLess(a["Score"], 1)
        self.assertEqual(a["Alertes"], [])
        self.assertIn("Critique", b["Alertes"])

    def test_critique_des_que_le_score_vaut_1(self):
        # Une seule entreprise : ses rapports au portefeuille valent tous 1, le score aussi
        prestations = [{"police": "SEULE", "matricule_beneficiaire": i, "mt_rembourse": D(1000), "mt_reclame": D(1000), "date_naissance": None} for i in range(3)]
        ligne = entreprises_a_risque(prestations, [], None)[0][0]
        self.assertEqual(ligne["Score"], 1)
        self.assertIn("Critique", ligne["Alertes"])
