from datetime import date

from django.test import SimpleTestCase

from .incorporation import ErreurRenouvellement, _verifier_periode, _verifier_periode_devis


class IncorporationPeriodeTests(SimpleTestCase):
    def setUp(self):
        self.jour = date(2026, 10, 31)
        self.debut = date(2026, 1, 1)
        self.echeance = date(2026, 12, 31)

    def test_accepte_une_date_future_dans_la_periode(self):
        _verifier_periode(date(2026, 11, 15), self.debut, self.echeance, self.jour)

    def test_refuse_une_date_anterieure_au_jour(self):
        with self.assertRaises(ErreurRenouvellement):
            _verifier_periode(date(2026, 10, 30), self.debut, self.echeance, self.jour)

    def test_refuse_une_date_apres_echeance(self):
        with self.assertRaises(ErreurRenouvellement):
            _verifier_periode(date(2027, 1, 1), self.debut, self.echeance, self.jour)

    def test_refuse_une_date_avant_effet_du_contrat(self):
        with self.assertRaises(ErreurRenouvellement):
            _verifier_periode(date(2025, 12, 31), self.debut, self.echeance, self.jour)

    def test_refuse_une_date_absente(self):
        with self.assertRaises(ErreurRenouvellement):
            _verifier_periode(None, self.debut, self.echeance, self.jour)

    def test_periode_devis_incorporation_immuable(self):
        _verifier_periode_devis("INC", self.jour, self.echeance, self.jour, self.echeance)
        with self.assertRaises(ValueError):
            _verifier_periode_devis("INC", self.jour, self.echeance, self.debut, self.echeance)
        with self.assertRaises(ValueError):
            _verifier_periode_devis("INC", self.jour, self.echeance, self.jour, self.debut)

    def test_periode_des_autres_mouvements_inchangee(self):
        _verifier_periode_devis("REN", self.jour, self.echeance, self.debut, self.debut)
