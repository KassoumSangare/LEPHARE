"""Règlements d'une police : le nom de l'utilisateur qui a encaissé n'est lu et envoyé qu'avec encaissements.auteur. Sans base."""
from datetime import date, datetime
from unittest import mock

from django.test import SimpleTestCase

from production import encaissements_police as ep


class CurseurFactice:
    """Rend, requête après requête : la police, les règlements, les quittances (montant hors caisse)."""

    def __init__(self):
        self.requetes = []
        self.reponses = [
            (["numeropolice"], [("1186201250492L",)]),
            (["iddetailencaissement", "idencaissement", "numeropiece", "dateencaissement", "datesaisie", "jour_saisie", "numeroquittance", "montant",
              "mode", "reference", "annule", "avenant", "auteur_connu", "auteur"],
             [(10, 5, "P1", date(2026, 11, 20), datetime(2026, 11, 20, 9, 30), date(2026, 11, 20), "Q1", 50000, "Espèces", "", False, "AFN", True, "Agent caisse"),
              (9, 4, "P0", date(2025, 1, 2), datetime(2025, 12, 11, 10, 14), date(2025, 12, 3), "Q0", 40000, "Chèque", "123", False, "AFN", False, None)]),
            (["numeroquittance", "dateemission", "ecart", "avenant", "auteur"],
             [("Q1", date(2026, 11, 1), 0, "AFN", None), ("QR", date(2025, 6, 1), 30000, "AFN", "Saisie reprise")]),
        ]
        self._courante = None

    def execute(self, sql, params=None):
        self.requetes.append(sql)
        self._courante = self.reponses.pop(0)
        self.description = [(c,) for c in self._courante[0]]

    def fetchall(self):
        return self._courante[1]


class ReglementsDePolice(SimpleTestCase):
    def _lire(self, droit):
        curseur = CurseurFactice()
        with mock.patch.object(ep, "a_le_droit", return_value=droit) as controle:
            resultat = ep.reglements_de_police(curseur, 1, object())
        controle.assert_called_once_with(mock.ANY, ep.DROIT_AUTEUR)
        return resultat, curseur.requetes

    def test_sans_le_droit_le_nom_n_est_ni_lu_ni_envoye(self):
        resultat, requetes = self._lire(False)
        self.assertFalse(resultat["VoirAuteur"])
        self.assertNotIn("u.name", requetes[1])
        self.assertNotIn("lephare_reprise", requetes[2])
        self.assertTrue(all("EncaissePar" not in r and "SaisieLe" not in r for r in resultat["Reglements"] + resultat["HorsCaisse"]))
        self.assertEqual([r["Montant"] for r in resultat["Reglements"]], [50000.0, 40000.0])

    def test_avec_le_droit(self):
        resultat, requetes = self._lire(True)
        self.assertTrue(resultat["VoirAuteur"])
        self.assertIn(f"{ep.SQL_NOM_COMPTE} AS auteur", requetes[1])
        # Historique repris de l'ancien logiciel (décembre 2025) : auteur inconnu, chaîne vide (« Historique repris » à l'écran)
        self.assertEqual([r["EncaissePar"] for r in resultat["Reglements"]], ["Agent caisse", ""])
        self.assertEqual(resultat["Reglements"][0]["Heure"], "09:30")
        # Pièce sans auteur : pas d'heure (celle de la reprise), jour où elle est entrée en base
        self.assertEqual(resultat["Reglements"][1]["Heure"], "")
        self.assertEqual([r["SaisieLe"] for r in resultat["Reglements"]], [None, "2025-12-03"])

    def test_montant_encaisse_hors_caisse(self):
        resultat, _ = self._lire(True)
        self.assertEqual(resultat["HorsCaisse"], [{"Quittance": "QR", "Avenant": "AFN", "Montant": 30000.0, "Date": "2025-06-01",
                                                   "EncaissePar": "Saisie reprise"}])
