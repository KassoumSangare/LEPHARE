import io
from datetime import date, datetime
from decimal import Decimal

from django.test import SimpleTestCase
from openpyxl import Workbook

from .afa import ErreurAfa, _acte, _date, _montant, lire_fichier


def classeur_afa(lignes, total=True):
    """Liste AFA au format d'OREOLE : titre, en-tête en ligne 3, acte et dates fusionnés, ligne TOTAL."""
    classeur = Workbook()
    feuille = classeur.active
    feuille["A1"] = "LISTE AFA P/C ATM INFORMATIQUE"
    for colonne, intitule in enumerate(["N°", "ACTE", "DATE D'EFFET", "DATE D'ECHEANCE", "SOUSCRIPTEUR", "NOMS ET PRENOMS",
                                        "DATE DE NAISSANCE", "EN QUALITE DE", "CAPITAL ASSURE", "BENEFICIAIRES", "PRIMES TTC"], 1):
        feuille.cell(3, colonne, intitule)
    for rang, (nom, naissance, prime) in enumerate(lignes, 4):
        feuille.cell(rang, 1, rang - 3)
        feuille.cell(rang, 6, nom)
        feuille.cell(rang, 7, naissance)
        feuille.cell(rang, 9, 500000)
        feuille.cell(rang, 10, "BENEFICIAIRE")
        feuille.cell(rang, 11, prime)
    fin = 3 + len(lignes)
    feuille.cell(4, 2, "RENOUVELLEMENT")
    feuille.cell(4, 3, datetime(2026, 2, 18))
    feuille.cell(4, 4, datetime(2026, 12, 31))
    feuille.cell(4, 5, "ATM INFORMATIQUE")
    for colonne in (2, 3, 4, 5):
        feuille.merge_cells(start_row=4, start_column=colonne, end_row=fin, end_column=colonne)
    if total:
        feuille.cell(fin + 1, 1, "TOTAL")
        feuille.merge_cells(start_row=fin + 1, start_column=1, end_row=fin + 1, end_column=8)
        feuille.cell(fin + 1, 11, sum(p for _, _, p in lignes))
    tampon = io.BytesIO()
    classeur.save(tampon)
    return tampon.getvalue()


class LectureListeAfaTests(SimpleTestCase):
    def test_cellules_fusionnees_reportees_sur_chaque_assure(self):
        fichier = lire_fichier(classeur_afa([("TUO NANGA ABOUBAKAR", datetime(1986, 3, 31), 7500),
                                             ("KONATE MOUSTAPHA", datetime(1993, 6, 15), 7500)]))
        self.assertEqual(len(fichier["Lignes"]), 2)
        for ligne in fichier["Lignes"]:
            self.assertEqual(ligne["acte"], "RENOUVELLEMENT")
            self.assertEqual(ligne["souscripteur"], "ATM INFORMATIQUE")
            self.assertEqual(ligne["effet"], datetime(2026, 2, 18))
        self.assertEqual(fichier["TotalPrime"], 15000)
        self.assertEqual(fichier["Titre"], "LISTE AFA P/C ATM INFORMATIQUE")

    def test_ligne_total_arrete_la_lecture(self):
        fichier = lire_fichier(classeur_afa([("DAO ADAMA", datetime(2000, 6, 19), 7500)]))
        self.assertEqual([l["nom"] for l in fichier["Lignes"]], ["DAO ADAMA"])

    def test_fichier_sans_entete_refuse(self):
        classeur = Workbook()
        classeur.active["A1"] = "rien"
        tampon = io.BytesIO()
        classeur.save(tampon)
        with self.assertRaises(ErreurAfa):
            lire_fichier(tampon.getvalue())

    def test_fichier_illisible_refuse(self):
        with self.assertRaises(ErreurAfa):
            lire_fichier(b"pas un classeur")


class ConversionsAfaTests(SimpleTestCase):
    def test_dates(self):
        self.assertEqual(_date("18/02/2026"), date(2026, 2, 18))
        self.assertEqual(_date("2026-02-18"), date(2026, 2, 18))
        self.assertEqual(_date(46071), date(2026, 2, 18))
        self.assertIsNone(_date(""))
        with self.assertRaises(ValueError):
            _date("31/02/2026")

    def test_montants(self):
        self.assertEqual(_montant("7 500"), Decimal("7500"))
        self.assertEqual(_montant("500 000 F"), Decimal("500000"))
        self.assertEqual(_montant(7500.0), Decimal("7500.0"))
        with self.assertRaises(ValueError):
            _montant("sept mille")

    def test_actes(self):
        self.assertEqual(_acte("RENOUVELLEMENT"), "Renouvellement")
        self.assertEqual(_acte("incorporation"), "Incorporation")
        self.assertEqual(_acte("Affaire nouvelle"), "Affaire nouvelle")
        self.assertEqual(_acte(None), "")
