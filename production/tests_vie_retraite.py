"""Offre Vie Retraite complémentaire (demande du 2026-11-10) : lecture de l'état mensuel des cotisations, sans base de données.
Le lecteur a été vérifié sur les dix états ARC de CI-ENERGIES (janvier à octobre 2026) : effectifs et totaux au franc près."""

import io
from datetime import date
from unittest import mock

from django.test import SimpleTestCase
from openpyxl import Workbook

from .afa import ErreurAfa
from .vie_retraite import _employeur, comparer, controler_periode, cotisants_saisis, fin_de_mois, lire_fichier, mois_du_texte

SALARIES = [("05002M", "EBAH Anasthasie", "ADINGRA", 30000, 41657), ("05004P", "Marie Madeleine", "BEDIA", 15000, 94807),
            ("05010W", "AHOU SOPHIE", "KOUAKOU", 30000, 43732)]


def etat_arc(salaries=SALARIES, inverse=True, total=None, titre="ETAT DES COTISATIONS DU MOIS DE JANVIER  2026"):
    """État au format CI-ENERGIES : titres, en-tête sur deux lignes (cellules fusionnées), ligne numérotée vide, Montant Total."""
    classeur = Workbook()
    f = classeur.active
    f.title = "JANVIER 26"
    f["A1"] = "CALCUL DES SALAIRES"
    f["C2"] = "ASSURANCE RETRAITE COMPLEMENTAIRE"
    f["C3"] = titre
    for colonne, intitule in enumerate(["N°", "Matric.", "Nom", "Prénoms", "Cotisations Mensuelles", None, "Total Cotisations", "Observations"], 1):
        if intitule:
            f.cell(5, colonne, intitule)
    f["E6"], f["F6"] = "SALARIES REELS", "CI-ENERGIES REELS"
    for plage in ("A5:A6", "B5:B6", "C5:C6", "D5:D6", "E5:F5", "G5:G6", "H5:H6"):
        f.merge_cells(plage)
    for rang, (matricule, prenoms, nom, salarie, employeur) in enumerate(salaries, 1):
        ligne = 6 + rang
        f.cell(ligne, 1, rang)
        f.cell(ligne, 2, matricule)
        f.cell(ligne, 3, prenoms if inverse else nom)
        f.cell(ligne, 4, nom if inverse else prenoms)
        f.cell(ligne, 5, salarie)
        f.cell(ligne, 6, employeur)
        f.cell(ligne, 7, salarie + employeur)
    fin = 7 + len(salaries)
    f.cell(fin, 1, len(salaries) + 1)  # ligne numérotée sans salarié, comme dans les états réels
    f.cell(fin + 2, 1, "Montant Total")
    f.cell(fin + 2, 7, total if total is not None else sum(s + e for *_, s, e in salaries))
    tampon = io.BytesIO()
    classeur.save(tampon)
    return tampon.getvalue()


class LectureEtatTests(SimpleTestCase):
    def test_entete_sur_deux_lignes_et_noms_remis_en_place(self):
        etat = lire_fichier(etat_arc(), "ARC - Janvier 2026.xlsx")
        self.assertEqual([l["matricule"] for l in etat["Lignes"]], ["05002M", "05004P", "05010W"])
        self.assertTrue(etat["Inversion"])
        self.assertEqual((etat["Lignes"][0]["nom"], etat["Lignes"][0]["prenoms"]), ("ADINGRA", "EBAH Anasthasie"))
        self.assertEqual((etat["Lignes"][0]["salarie"], etat["Lignes"][0]["employeur"]), (30000, 41657))
        self.assertEqual(etat["Mois"], date(2026, 1, 1))
        self.assertEqual(etat["Employeur"], "CI-ENERGIES")
        self.assertEqual(etat["TotauxFichier"]["total"], 255196)

    def test_colonnes_dans_le_bon_ordre_non_inversees(self):
        etat = lire_fichier(etat_arc(inverse=False), "x.xlsx")
        self.assertFalse(etat["Inversion"])
        self.assertEqual(etat["Lignes"][1]["nom"], "BEDIA")

    def test_mois_du_titre_de_la_feuille_ou_du_fichier(self):
        self.assertEqual(mois_du_texte("ETAT DES COTISATIONS DU MOIS D'OCTOBRE  2026"), date(2026, 10, 1))
        self.assertEqual(mois_du_texte("", "SEPT 26"), date(2026, 9, 1))
        self.assertEqual(mois_du_texte("sans mois", "ARC - Août 2026.xlsx"), date(2026, 8, 1))
        self.assertIsNone(mois_du_texte("ASSURANCE RETRAITE COMPLEMENTAIRE"))
        self.assertEqual(fin_de_mois(date(2028, 2, 1)), date(2028, 2, 29))

    def test_employeur_tire_de_l_intitule(self):
        self.assertEqual(_employeur("CI-ENERGIES REELS"), "CI-ENERGIES")
        self.assertEqual(_employeur("PART PATRONALE"), "")

    def test_fichier_sans_en_tete_refuse(self):
        classeur = Workbook()
        classeur.active["A1"] = "rien"
        tampon = io.BytesIO()
        classeur.save(tampon)
        with self.assertRaises(ErreurAfa):
            lire_fichier(tampon.getvalue())


class SaisieEtComparaisonTests(SimpleTestCase):
    def test_cotisants_controles(self):
        lignes = cotisants_saisis({"Cotisants": [{"Matricule": "05002m", "Nom": "adingra", "CotisationSalarie": "30 000", "CotisationEmployeur": 41657}]})
        self.assertEqual((lignes[0]["Matricule"], lignes[0]["Nom"], int(lignes[0]["CotisationSalarie"])), ("05002M", "ADINGRA", 30000))
        for cotisants, attendu in (([], "au moins un salarié"), ([{"Nom": "A", "CotisationSalarie": 0, "CotisationEmployeur": 0}], "nulles"),
                                   ([{"Nom": "A", "CotisationSalarie": -5}], "négative"),
                                   ([{"Matricule": "X", "Nom": "A", "CotisationSalarie": 1}, {"Matricule": "X", "Nom": "B", "CotisationSalarie": 1}], "déjà saisi")):
            with self.subTest(attendu=attendu), self.assertRaisesRegex(ErreurAfa, attendu):
                cotisants_saisis({"Cotisants": cotisants})

    def test_periode_d_un_mois_entier(self):
        offre = {"Libelle": "Retraite complémentaire", "Periodicite": "MENSUELLE"}
        controler_periode(offre, {"DateEffet": date(2026, 2, 1), "DateExpiration": date(2026, 2, 28)})
        with self.assertRaisesRegex(ErreurAfa, "mois entier"):
            controler_periode(offre, {"DateEffet": date(2026, 2, 3), "DateExpiration": date(2026, 3, 2)})
        controler_periode(offre | {"Periodicite": "ANNUELLE"}, {"DateEffet": date(2026, 2, 3), "DateExpiration": date(2027, 2, 2)})

    def test_comparaison_avec_le_mois_precedent(self):
        precedent = {"IdDevis": 1, "NumeroDevis": "D1", "Mois": "2026-01-01", "LibelleMois": "janvier 2026", "Confirme": True, "Cotisants": [
            {"Matricule": "A1", "Nom": "X", "Prenoms": "", "CotisationSalarie": 100, "CotisationEmployeur": 200},
            {"Matricule": "B2", "Nom": "Y", "Prenoms": "", "CotisationSalarie": 100, "CotisationEmployeur": 200}]}
        lignes = [{"Matricule": "A1", "Nom": "X", "Prenoms": "", "CotisationSalarie": 100, "CotisationEmployeur": 250},
                  {"Matricule": "C3", "Nom": "Z", "Prenoms": "", "CotisationSalarie": 50, "CotisationEmployeur": 50}]
        c = comparer(lignes, precedent)
        self.assertEqual(([l["Matricule"] for l in c["Entrants"]], [l["Matricule"] for l in c["Sortants"]]), (["C3"], ["B2"]))
        self.assertEqual((c["Modifies"][0]["Matricule"], c["Modifies"][0]["AncienneEmployeur"]), ("A1", 200))
        self.assertEqual(c["Ecart"], 450 - 600)
        self.assertIsNone(comparer(lignes, None))


class AnalyseTests(SimpleTestCase):
    @mock.patch("production.vie_retraite.connection")
    @mock.patch("production.vie_retraite.mois_deja_enregistre", return_value=None)
    @mock.patch("production.vie_retraite.etat_precedent", return_value=None)
    @mock.patch("production.vie_retraite.polices_annotees", return_value=[])
    @mock.patch("production.vie_retraite._souscripteur", return_value={"Texte": "CI-ENERGIES", "IdClient": 4, "Nom": "CI-ENERGIES"})
    def test_totaux_et_ecart_avec_la_ligne_montant_total(self, *_):
        from .vie_retraite import analyser
        a = analyser(etat_arc(total=255000), "ARC - Janvier 2026.xlsx")
        self.assertEqual((a["Totaux"]["Salaries"], a["Totaux"]["Total"], a["DateExpiration"]), (3, 255196, "2026-01-31"))
        self.assertTrue(any("différent de la somme" in m for m in a["Avertissements"]))
        self.assertTrue(any("inversées" in m for m in a["Avertissements"]))
        self.assertEqual(a["Erreurs"], [])
