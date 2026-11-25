"""Centre des corrections : mise en cohérence d'un contrat corrigé (coherence_contrat.py) et règles de la fusion de fiches clients
(customer/fusion.py). Sans base de données : curseur simulé qui répond selon la requête et garde trace des écritures."""

import re
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from customer import fusion
from . import coherence_contrat
from .coherence_contrat import ErreurCoherence, propager


class CurseurSimule:
    """Répond à chaque requête selon la première règle (expression, réponse) qui la reconnaît ; une réponse liste sert
    fetchall, un tuple fetchone. Les écritures sans règle ne renvoient rien."""

    def __init__(self, regles):
        self.regles, self.requetes, self.reponse, self.rowcount = regles, [], [], 0

    def execute(self, sql, params=None):
        texte = " ".join(sql.split())
        self.requetes.append((texte, params))
        self.reponse = []
        for motif, reponse in self.regles:
            if re.search(motif, texte):
                self.reponse = reponse(texte, params) if callable(reponse) else reponse
                break
        self.rowcount = len(self.reponse) if isinstance(self.reponse, list) else 1

    def fetchone(self):
        if isinstance(self.reponse, list):
            return self.reponse[0] if self.reponse else None
        return self.reponse

    def fetchall(self):
        return self.reponse if isinstance(self.reponse, list) else [self.reponse]

    def ecritures(self, debut):
        return [(sql, params) for sql, params in self.requetes if sql.startswith(debut)]


AVANT = {"idclient": 1, "idassure": 1, "idcompagnie": 1, "idaperiteur": 1, "numeropolice": "P1"}


def contrat(**valeurs):
    base = {"pk": 7, "idclient_id": 1, "idassure": 1, "idcompagnie_id": 1, "idaperiteur": 1, "numeropolice": "P1", "idquittance_id": 10}
    return SimpleNamespace(**{**base, **valeurs})


NOMS = (r"^SELECT TRIM\(COALESCE\(nom|^SELECT TRIM\(raisonsociale", ("NOM",))


class SouscripteurCorrige(SimpleTestCase):
    def regles(self, statut="V", autres=2):
        return [
            (r"^SELECT COALESCE\(statut", (statut,)),
            NOMS,
            (r"^SELECT q\.idquittance, TRIM\(q\.numeroquittance\), q\.idclient", [(10, "Q1", 1, Decimal("100000"))]),
            (r"^SELECT COALESCE\(solde, 0\)", (Decimal("500000"),)),
            (r"^SELECT d\.iddevis, TRIM\(COALESCE\(d\.numerodevis::text, d\.iddevis::text\)\), d\.idclient", [(20, "D1", 1)]),
            (r"^UPDATE stdcontrat SET idassure", [(7,)]),
            (r"^SELECT idcontrat FROM stdcontrat WHERE numeropolice", [(8,), (9,)]),
            (r"^SELECT COUNT\(\*\) FROM stdcontrat", (autres,)),
        ]

    def test_quittance_devis_assure_et_reste_du_suivent(self):
        curseur = CurseurSimule(self.regles())
        resultat = propager(curseur, contrat(idclient_id=2), AVANT)
        self.assertEqual(curseur.ecritures("UPDATE stdquittance SET idclient"), [("UPDATE stdquittance SET idclient = %s WHERE idquittance = %s", [2, 10])])
        # Reste dû (100 000 F) retiré du solde de l'ancien client et porté à celui du nouveau
        soldes = [p for _, p in curseur.ecritures("UPDATE stdclient SET solde")]
        self.assertIn([Decimal("-100000"), 1], soldes)
        self.assertIn([Decimal("100000"), 2], soldes)
        self.assertEqual(curseur.ecritures("UPDATE stddevis SET idclient")[0][1], [2, 20])
        self.assertEqual(curseur.ecritures("UPDATE stddevis SET idassure")[0][1], [2, 20, 1])
        self.assertTrue(curseur.ecritures("UPDATE stdcontrat SET idassure"))
        self.assertTrue(any(p["Champ"] == "Solde (reste dû)" for p in resultat["propagations"]))
        # Les autres mouvements de la police, non choisis, sont signalés
        self.assertTrue(any("2 autres mouvements de la police restent" in a for a in resultat["avertissements"]))

    def test_assure_corrige_a_l_ecran_non_remplace(self):
        curseur = CurseurSimule(self.regles())
        propager(curseur, contrat(idclient_id=2), AVANT, saisis={"idclient", "idassure"})
        self.assertFalse(curseur.ecritures("UPDATE stdcontrat SET idassure"))
        self.assertFalse(curseur.ecritures("UPDATE stddevis SET idassure"))

    def test_toute_la_police(self):
        curseur = CurseurSimule(self.regles())
        resultat = propager(curseur, contrat(idclient_id=2), AVANT, toute_la_police=True)
        self.assertEqual(curseur.ecritures("UPDATE stdcontrat SET idclient")[0][1], [2, [8, 9]])
        self.assertEqual(resultat["avertissements"], [])

    def test_fiche_archivee_refusee(self):
        with self.assertRaisesRegex(ErreurCoherence, "archivée"):
            propager(CurseurSimule(self.regles(statut="A")), contrat(idclient_id=2), AVANT)


class CompagnieCorrigee(SimpleTestCase):
    def regles(self, bloquees):
        return [
            NOMS,
            (r"^SELECT DISTINCT TRIM\(q\.numeroquittance\)", bloquees),
            (r"^UPDATE stdcontrat SET idaperiteur", [(7,)]),
            (r"^SELECT q\.idquittance, TRIM\(q\.numeroquittance\), q\.idaperiteur", [(10, "Q1", 1)]),
            (r"^SELECT d\.iddevis, TRIM\(COALESCE\(d\.numerodevis::text, d\.iddevis::text\)\), d\.idcompagnie", [(20, "D1", 1, True)]),
            (r"^SELECT COUNT\(\*\) FROM stdcontrat", (0,)),
        ]

    def test_refusee_si_prime_reversee_ou_commission_reclamee(self):
        with self.assertRaisesRegex(ErreurCoherence, "Annulez d'abord le bordereau"):
            propager(CurseurSimule(self.regles([("Q1",)])), contrat(idcompagnie_id=3), AVANT)

    def test_aperiteur_quittance_et_devis_suivent(self):
        curseur = CurseurSimule(self.regles([]))
        resultat = propager(curseur, contrat(idcompagnie_id=3), AVANT)
        self.assertEqual(curseur.ecritures("UPDATE stdcontrat SET idaperiteur")[0][1], [3, [7], 1])
        self.assertTrue(curseur.ecritures("UPDATE stdquittance q SET idaperiteur"))
        self.assertTrue(curseur.ecritures("UPDATE stddevis d SET idcompagnie"))
        self.assertTrue(any("taux de commission" in a for a in resultat["avertissements"]))

    def test_aperiteur_corrige_a_l_ecran_garde(self):
        curseur = CurseurSimule(self.regles([]))
        propager(curseur, contrat(idcompagnie_id=3, idaperiteur=5), AVANT, saisis={"idcompagnie", "idaperiteur"})
        self.assertFalse(curseur.ecritures("UPDATE stdcontrat SET idaperiteur"))


class PoliceCorrigee(SimpleTestCase):
    def test_numero_deja_pris_refuse(self):
        curseur = CurseurSimule([(r"^SELECT 1 FROM stdcontrat WHERE numeropolice", (1,))])
        with self.assertRaisesRegex(ErreurCoherence, "appartient déjà à une autre police"):
            propager(curseur, contrat(numeropolice="P2"), AVANT)

    def test_numero_trop_long_refuse(self):
        with self.assertRaisesRegex(ErreurCoherence, "15 caractères"):
            propager(CurseurSimule([]), contrat(numeropolice="P" * 16), AVANT)

    def test_tous_les_mouvements_et_quittances_suivent(self):
        curseur = CurseurSimule([
            (r"^SELECT 1 FROM stdcontrat WHERE numeropolice", []),
            (r"^UPDATE stdcontrat SET numeropolice", [(8,), (9,)]),
            (r"^UPDATE stdquittance SET numeropolice", [(1,), (2,), (3,)]),
            (r"^SELECT to_regclass", ("table",)),
        ])
        resultat = propager(curseur, contrat(numeropolice="P2"), AVANT)
        self.assertEqual(curseur.ecritures("UPDATE stdcontrat SET numeropolice")[0][1], ["P2", "P1"])
        elements = [p["Element"] for p in resultat["propagations"]]
        self.assertIn("2 autres mouvements de la police", elements)
        self.assertIn("3 quittances", elements)
        # Polices rattachées, commissions d'apporteur, voyages et certificats de transport
        self.assertEqual(len([s for s, _ in curseur.requetes if re.match(r'^UPDATE \w+ SET "(numeropolice|numeropoliceconnexe)"', s)]),
                         len(coherence_contrat.POLICE_AILLEURS))

    def test_rien_ne_change_rien_n_est_ecrit(self):
        curseur = CurseurSimule([])
        self.assertEqual(propager(curseur, contrat(), AVANT), {"propagations": [], "avertissements": []})
        self.assertFalse([s for s, _ in curseur.requetes if s.startswith("UPDATE")])


def fiche(idclient, particulier=True, statut="V"):
    return {"idclient": idclient, "nom": "KOUASSI", "prenoms": "JEAN", "statut": statut, "particulier": particulier}


class FusionClients(SimpleTestCase):
    def refus(self, garder, fusionner, a, b, regroupee=None):
        with mock.patch.object(fusion.ClientNettoyage.objects, "filter") as filtre:
            filtre.return_value.first.return_value = regroupee
            return fusion._refus(garder, fusionner, a, b)

    def test_deux_fiches_valides(self):
        self.assertEqual(self.refus(1, 2, fiche(1), fiche(2)), [])

    def test_meme_fiche(self):
        self.assertIn("Choisissez deux fiches différentes.", self.refus(1, 1, fiche(1), fiche(1)))

    def test_fiche_inconnue(self):
        self.assertTrue(any("n'existe pas" in r for r in self.refus(1, 2, fiche(1), None)))

    def test_personne_et_entreprise(self):
        self.assertTrue(any("une personne, l'autre une entreprise" in r for r in self.refus(1, 2, fiche(1, True), fiche(2, False))))

    def test_fiche_a_garder_archivee(self):
        self.assertTrue(any("restaurez-la" in r for r in self.refus(1, 2, fiche(1, statut="A"), fiche(2))))

    def test_deja_regroupee(self):
        regroupee = SimpleNamespace(idclient_reference=9)
        self.assertTrue(any("déjà regroupée sur la fiche n° 9" in r for r in self.refus(1, 2, fiche(1), fiche(2, statut="A"), regroupee)))

    def test_motif_obligatoire(self):
        with self.assertRaisesRegex(fusion.ErreurFusion, "motif"):
            fusion.fusionner_fiches(1, 2, " abc ")

    def test_coordonnees_vides(self):
        self.assertTrue(fusion.vide("telephone", "07 00"))
        self.assertFalse(fusion.vide("telephone", "07 08 09 10 11"))
        self.assertTrue(fusion.vide("email", "aucun"))
        self.assertTrue(fusion.vide("adresse1", " néant ".upper().replace("É", "E")))
        self.assertFalse(fusion.vide("adresse1", "Cocody"))
