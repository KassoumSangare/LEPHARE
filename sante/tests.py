from datetime import date

from django.test import SimpleTestCase

from production.renouvellement import ErreurRenouvellement

from .avenant import _membre


class MembreIncorporeTests(SimpleTestCase):
    """Nouveau membre d'un avenant d'incorporation Santé (sante/avenant.py)."""

    def test_sans_membre(self):
        self.assertIsNone(_membre(None))
        self.assertIsNone(_membre({}))

    def test_membre_complet(self):
        membre = _membre({"Lien": "e", "Nom": " Kone ", "Prenom": "Awa", "DateNaissance": "2015-01-01", "Sexe": "f",
                          "Certificat": True, "NombrePathologie": "1"})
        self.assertEqual(membre, {"lien": "E", "nom": "KONE", "prenom": "AWA", "sexe": "F", "naissance": date(2015, 1, 1),
                                  "certificat": True, "pathologies": 1})

    def test_valeurs_par_defaut(self):
        membre = _membre({"Lien": "C", "Nom": "Kone", "DateNaissance": "10/05/1990", "Sexe": "M"})
        self.assertEqual((membre["prenom"], membre["certificat"], membre["pathologies"]), ("", False, 0))
        self.assertEqual(membre["naissance"], date(1990, 5, 10))

    def test_saisies_refusees(self):
        complet = {"Lien": "E", "Nom": "Kone", "DateNaissance": "2015-01-01", "Sexe": "M"}
        for modification in ({"Lien": "A"}, {"Nom": " "}, {"DateNaissance": ""}, {"DateNaissance": "31/02/2015"},
                             {"Sexe": ""}, {"Sexe": "X"}, {"NombrePathologie": "deux"}):
            with self.subTest(modification=modification), self.assertRaises(ErreurRenouvellement):
                _membre({**complet, **modification})
        with self.assertRaises(ErreurRenouvellement):
            _membre(["Kone"])
