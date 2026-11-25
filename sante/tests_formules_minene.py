"""Formule MINENE suivant la taille de la famille (formules_minene.py) : au-delà de la tranche, formule suivante ; en deçà, formule
précédente. Sans base de données : curseur simulé qui répond selon la requête et garde trace des écritures."""

import re
from datetime import date

from django.test import SimpleTestCase

from .formules_minene import ErreurFormule, ranger_familles, texte


class CurseurSimule:
    def __init__(self, regles):
        self.regles, self.requetes, self.reponse = regles, [], []

    def execute(self, sql, params=None):
        sql = " ".join(sql.split())
        self.requetes.append((sql, params))
        self.reponse = []
        for motif, reponse in self.regles:
            if re.search(motif, sql):
                self.reponse = reponse
                break

    def fetchone(self):
        if isinstance(self.reponse, list):
            return self.reponse[0] if self.reponse else None
        return self.reponse

    def fetchall(self):
        return self.reponse if isinstance(self.reponse, list) else [self.reponse]

    def ecritures(self, debut):
        return [params for sql, params in self.requetes if sql.startswith(debut)]


EFFET, ECHEANCE = date(2026, 1, 1), date(2026, 12, 31)


def famille(option, mini, maxi, taille, offre=19):
    # adhérent, couverture, offre, offre commerciale (idtarif), collège, zone, effet, échéance, option, min, max, taille, nom
    return (5, 10, offre, 87, 1, 2, EFFET, ECHEANCE, option, mini, maxi, taille, "KOUASSI JEAN")


def regles(familles, adaptee=(18, "FAMILLE"), couverture=(11,), confirme=False, creee=(77, 900, "")):
    return [
        (r"^SELECT COALESCE\(confirme", (confirme,)),
        (r"^SELECT a\.idadherent", familles),
        (r"^SELECT f\.idoffre, f\.option", adaptee),
        (r"^SELECT idfiliale FROM stdfiliale", couverture),
        (r"^CALL sp_saisie_filiale_sante", creee),
    ]


class FormuleSuivantLaTaille(SimpleTestCase):
    def test_famille_plus_de_trois_personnes_passe_en_famille(self):
        curseur = CurseurSimule(regles([famille("FAMILLE PLUS", 4, 6, 3)]))
        passages = ranger_familles(curseur, 12, 900)
        self.assertEqual(passages, [{"IdAdherent": 5, "Famille": "KOUASSI JEAN", "Taille": 3, "Avant": "FAMILLE PLUS", "Apres": "FAMILLE"}])
        self.assertEqual(curseur.ecritures("UPDATE stdadherent"), [[11, 5, 900]])
        # Formule cherchée dans la même offre commerciale, pour la taille de la famille
        self.assertEqual(curseur.ecritures("SELECT f.idoffre, f.option"), [[87, 3]])
        # Couverture vidée retirée
        self.assertEqual(curseur.ecritures("DELETE FROM stdfiliale"), [[[10], 900]])
        self.assertEqual(texte(passages[0]), "Famille KOUASSI JEAN (3 personnes) : elle passe de FAMILLE PLUS à FAMILLE.")

    def test_famille_de_quatre_passe_en_famille_plus(self):
        curseur = CurseurSimule(regles([famille("FAMILLE", 2, 3, 4, offre=18)], adaptee=(19, "FAMILLE PLUS"), couverture=(12,)))
        self.assertEqual(ranger_familles(curseur, 12, 900)[0]["Apres"], "FAMILLE PLUS")
        self.assertEqual(curseur.ecritures("UPDATE stdadherent"), [[12, 5, 900]])

    def test_famille_d_une_personne_passe_en_solo(self):
        curseur = CurseurSimule(regles([famille("FAMILLE", 2, 3, 1, offre=18)], adaptee=(17, "SOLO")))
        self.assertEqual(ranger_familles(curseur, 12, 900)[0]["Apres"], "SOLO")

    def test_famille_dans_sa_tranche_inchangee(self):
        for option, mini, maxi, taille in (("FAMILLE", 2, 3, 2), ("FAMILLE", 2, 3, 3), ("FAMILLE PLUS", 4, 6, 6), ("SOLO", 1, 1, 1)):
            curseur = CurseurSimule(regles([famille(option, mini, maxi, taille)]))
            self.assertEqual(ranger_familles(curseur, 12, 900), [])
            self.assertFalse(curseur.ecritures("UPDATE"))

    def test_couverture_creee_si_le_devis_n_en_a_pas(self):
        curseur = CurseurSimule(regles([famille("FAMILLE PLUS", 4, 6, 2)], couverture=[]))
        ranger_familles(curseur, 12, 900)
        appel = curseur.ecritures("CALL sp_saisie_filiale_sante")[0]
        # Collège, formule, zone, dates de la couverture d'origine, source, opérateur, nouvelle couverture, devis
        self.assertEqual(appel[:9], [1, 18, 2, EFFET, ECHEANCE, "S", 12, 0, 900])
        self.assertEqual(curseur.ecritures("UPDATE stdadherent"), [[77, 5, 900]])

    def test_famille_trop_grande_sans_formule_refusee(self):
        curseur = CurseurSimule(regles([famille("FAMILLE PLUS", 4, 6, 7)], adaptee=[]))
        with self.assertRaisesRegex(ErreurFormule, "aucune formule de l'offre n'accueille une famille de 7 personnes"):
            ranger_familles(curseur, 12, 900)

    def test_devis_confirme_non_touche(self):
        curseur = CurseurSimule(regles([famille("FAMILLE PLUS", 4, 6, 2)], confirme=True))
        self.assertEqual(ranger_familles(curseur, 12, 900), [])
        self.assertEqual(len(curseur.requetes), 1)

    def test_apercu_garde_les_couvertures(self):
        curseur = CurseurSimule(regles([famille("FAMILLE PLUS", 4, 6, 3)]))
        ranger_familles(curseur, 12, 900, retirer_vides=False)
        self.assertFalse(curseur.ecritures("DELETE"))

    def test_retrait_d_une_personne_vise_sa_famille(self):
        curseur = CurseurSimule(regles([famille("FAMILLE PLUS", 4, 6, 3)]))
        ranger_familles(curseur, 12, 900, id_adherent=5)
        sql, params = next((s, p) for s, p in curseur.requetes if s.startswith("SELECT a.idadherent"))
        self.assertIn("AND a.idadherent = %s", sql)
        self.assertEqual(params, [900, 12, 5])
