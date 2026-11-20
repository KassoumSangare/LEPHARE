"""Consommations MINENE Santé : lecture des états personnalisés du gestionnaire et analyse (sante/consommations_minene.py)."""

import datetime as dt
import io
from decimal import Decimal as D

from django.test import SimpleTestCase
from openpyxl import Workbook

from .consommations import _lire, lire_date
from .consommations_minene import analyser

ENTETE = ["DateCloture", "Numero", "CodGar", "Garant", "Souscripteur", "idPolice", "Police", "codeCollege", "College", "MatriculeP", "Matric",
          "SouscP", "Patient", "Statut", "dateNaissance", "sexe", "MatriculeA", "Assure", "localitecentreExecutant", "centreExecutant",
          "LocalitecentrePrescripteur", "centrePrescripteur", "libelle", "NPrestations", "codeActe", "Actes", "Medecin", "dateConsultation",
          "DatedeSoins", "CodeTypeAffection", "TypeAffection", "codeAffection", "TypePrestation", "Reclamé", "tm", "MontantExclus",
          "depassement", "Remboursé", "partPatient"]


def ligne(numero, matricule, famille, reclame, rembourse, exclus=0, affection="CARDIO", type_="TP"):
    return ["01/2026", "104", "OREOLEMINENE", "NSIA ASSURANCES", "FAMILLE A", "907", "FAMILLE A", "1648", "COLLEGE A", matricule, "", "",
            "PATIENT", "C", "1971-01-06", "F", "09070001", "ASSURE A", "COCODY", "CENTRE X", "COCODY", "CENTRE X", famille, numero,
            "AC1", "ACTE", "MEDECIN", "2025-12-31", "2025-12-31", "02", affection, "22", type_, reclame, 30, exclus, 0, rembourse,
            reclame - rembourse - exclus]


def classeur(*lignes):
    wb = Workbook()
    ws = wb.active
    ws.title = "ETATS PERSONNALISES"
    ws.append(ENTETE)
    for l in lignes:
        ws.append(l)
    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


class LectureEtatsPersonnalisesTests(SimpleTestCase):
    def test_cloture_au_mois(self):
        self.assertEqual(lire_date("01/2026"), dt.date(2026, 1, 31))
        self.assertEqual(lire_date("12/2025"), dt.date(2025, 12, 31))
        self.assertEqual(lire_date("02/2024"), dt.date(2024, 2, 29))
        self.assertIsNone(lire_date("13/2026"))

    def test_prestations_lues_sous_les_noms_du_releve(self):
        prestations, effectif, feuilles, manquantes, _c, _p = _lire(classeur(
            ligne(2418653, "0907000102", "BIOLOGIE", 12425, 8697),
            ligne(2418654, "0907000102", "AUXILIAIRES MÉDICAUX", 10000, 6000, exclus=1000, affection="infectieux"),
        ))
        self.assertEqual(manquantes, [])
        self.assertEqual(feuilles[0]["Nature"], "PRESTATIONS")
        p = prestations[2418653]
        self.assertEqual(p["date_cloture"], dt.date(2026, 1, 31))
        self.assertEqual(p["garant"], "OREOLEMINENE")
        self.assertEqual((p["matricule_beneficiaire"], p["matricule_assure"], p["npol"]), (907000102, 9070001, 907))
        self.assertEqual((p["type"], p["type_affection"], p["sexe"], p["localite_centre"]), ("TP", "CARDIO", "F", "COCODY"))
        self.assertEqual((p["mt_reclame"], p["mt_rembourse"], p["ticket_moderateur"]), (D(12425), D(8697), D(30)))
        self.assertEqual(p["date_soins_retenue"], dt.date(2025, 12, 31))
        autre = prestations[2418654]
        self.assertEqual(autre["famille"], "AUXILIAIRES MEDICAUX")
        self.assertEqual(autre["type_affection"], "INFECTIEUX")
        self.assertEqual(autre["base_decomptee"], D(9000))


def prestation(numero, beneficiaire, assure, rembourse, mois=1, famille="BIOLOGIE", type_="TP", affection="CARDIO", statut="C", sexe="F"):
    jour = dt.date(2026, mois, 10)
    return {"numero_prest": numero, "matricule_beneficiaire": beneficiaire, "matricule_assure": assure, "mt_reclame": D(rembourse) * D("1.4"),
            "mt_rembourse": D(rembourse), "exclusion": D(0), "depassement": D(0), "date_soins_retenue": jour, "date_cloture": jour + dt.timedelta(days=20),
            "famille": famille, "type": type_, "type_affection": affection, "statut": statut, "sexe": sexe, "date_naissance": dt.date(1980, 5, 1),
            "assure": f"ASSURE {assure}", "police": "POLICE MCI", "centre_executant": "CENTRE", "localite_centre": "COCODY", "medecin": "MEDECIN",
            "acte": "ACTE", "code_acte": "AC1"}


class AnalyseMineneTests(SimpleTestCase):
    def setUp(self):
        self.prestations = [
            prestation(1, 101, 10, 300000, mois=1),
            prestation(2, 102, 10, 100000, mois=2, famille="CONSULTATION", affection="INFECTIEUX", statut="E", sexe="M"),
            prestation(3, 201, 20, 50000, mois=2, type_="RD"),
            prestation(4, 301, 30, 10000, mois=2),
        ]
        self.liens = {
            101: {"Police": "P1", "Formule": "FAMILLE", "PrimeNette": D(600000), "IdAdherent": 1, "Famille": "F1"},
            102: {"Police": "P1", "Formule": "FAMILLE", "PrimeNette": D(600000), "IdAdherent": 1, "Famille": "F1"},
            201: {"Police": "P2", "Formule": "SOLO", "PrimeNette": D(300000), "IdAdherent": 2, "Famille": "F2"},
        }
        self.portefeuille = [
            {"Police": "P1", "IdAdherent": 1, "Famille": "F1", "Formule": "FAMILLE", "PrimeNette": D(600000), "Personnes": 4},
            {"Police": "P2", "IdAdherent": 2, "Famille": "F2", "Formule": "SOLO", "PrimeNette": D(300000), "Personnes": 1},
            {"Police": "P3", "IdAdherent": 3, "Famille": "F3", "Formule": "SOLO", "PrimeNette": D(300000), "Personnes": 1},
        ]

    def test_indicateurs_et_repartitions(self):
        r = analyser(self.prestations, self.liens, self.portefeuille)
        i = r["Indicateurs"]
        self.assertEqual((i["Prestations"], i["Beneficiaires"], i["Familles"]), (4, 4, 3))
        self.assertEqual(i["Rembourse"], 460000)
        self.assertEqual(r["Periode"]["NombreMois"], 2)
        # Primes acquises sur 2 mois : (600 000 + 300 000 + 300 000) x 2 / 12 = 200 000 ; rattaché = 450 000
        self.assertEqual(i["PrimesAcquises"], 200000)
        self.assertEqual(i["RembourseRattache"], 450000)
        self.assertAlmostEqual(i["TauxConsommation"], 2.25)
        self.assertEqual({t["Code"]: t["Prestations"] for t in r["ParType"]}, {"TP": 3, "RD": 1})
        self.assertEqual(r["ParAffection"][0]["Libelle"], "CARDIO")
        self.assertEqual([m["Code"] for m in r["ParMois"]], ["2026-01", "2026-02"])

    def test_familles_taux_et_situations(self):
        r = analyser(self.prestations, self.liens, self.portefeuille)
        familles = {f["Code"]: f for f in r["Familles"]}
        # Famille 10 : 400 000 remboursés pour 600 000 x 2 / 12 = 100 000 acquis
        self.assertEqual(familles[10]["Formule"], "FAMILLE")
        self.assertAlmostEqual(familles[10]["Taux"], 4.0)
        self.assertEqual(familles[10]["Situation"], "DEPASSEE")
        self.assertEqual(familles[20]["Situation"], "NORMALE" if familles[20]["Taux"] < 0.8 else familles[20]["Situation"])
        self.assertEqual(familles[30]["Situation"], "SANS_CONTRAT")
        formules = {f["Formule"]: f for f in r["Formules"]}
        self.assertEqual((formules["SOLO"]["Familles"], formules["SOLO"]["Consommatrices"]), (2, 1))

    def test_membre_sans_matricule_rattache_par_sa_famille(self):
        # Le relevé désigne le membre 3002 de la famille 30 ; LE PHARE ne connaît que le membre 3001 de cette famille
        liens = {**self.liens, 3001: {"Police": "P3", "Formule": "SOLO", "PrimeNette": D(300000), "IdAdherent": 3, "Famille": "F3"}}
        prestations = [*self.prestations[:3], prestation(4, 3002, 30, 10000, mois=2)]
        r = analyser(prestations, liens, self.portefeuille)
        famille = next(f for f in r["Familles"] if f["Code"] == 30)
        self.assertEqual((famille["PoliceLePhare"], famille["Formule"]), ("P3", "SOLO"))
        self.assertEqual(next(f for f in r["Formules"] if f["Formule"] == "SOLO")["Consommatrices"], 2)

    def test_periode_imposee(self):
        r = analyser(self.prestations, self.liens, self.portefeuille, mois_couverts=12)
        self.assertEqual(r["Indicateurs"]["PrimesAcquises"], 1200000)

    def test_relevé_vide(self):
        r = analyser([], {}, self.portefeuille)
        self.assertEqual(r["Indicateurs"]["Prestations"], 0)
        self.assertEqual(r["Familles"], [])


class SeparationProgrammesTests(SimpleTestCase):
    """Oreole Santé et MINENE Santé : deux espaces séparés (demande du 2026-11-19)."""

    def test_conditions_sql(self):
        from .consommations import MINENE, OREOLE, programme_demande, sql_programme, sql_releve_programme

        self.assertEqual(sql_programme(MINENE), "p.garant = 'OREOLEMINENE'")
        self.assertEqual(sql_programme(OREOLE, "e.garant"), "COALESCE(e.garant, '') <> 'OREOLEMINENE'")
        self.assertIn("NOT", sql_releve_programme(OREOLE))
        self.assertEqual(programme_demande({"programme": "MINENE"}), MINENE)
        self.assertEqual(programme_demande({}), OREOLE)

    def test_fichier_refuse_hors_de_son_espace(self):
        from .consommations import MINENE, OREOLE, ErreurConsommation, verifier_programme

        minene = {1: {"garant": "OREOLEMINENE"}}
        oreole = {2: {"garant": "OREOLE CGA"}}
        verifier_programme(MINENE, minene, {}, {}, [])
        verifier_programme(OREOLE, oreole, {}, {}, [])
        verifier_programme(None, {**minene, **oreole}, {}, {}, [])
        with self.assertRaises(ErreurConsommation):
            verifier_programme(OREOLE, minene, {}, {}, [])
        with self.assertRaises(ErreurConsommation):
            verifier_programme(MINENE, oreole, {}, {}, [])
        with self.assertRaises(ErreurConsommation):
            verifier_programme(MINENE, minene, {}, {}, [{"entreprise": "X"}])
        with self.assertRaises(ErreurConsommation):
            verifier_programme(MINENE, {**minene, **oreole}, {}, {}, [])


class DroitAnomaliesMineneTests(SimpleTestCase):
    """Les anomalies MINENE (bénéficiaires, scores, niveaux) suivent le droit consommations.fraude, comme la fiche famille."""

    def _appel(self, droit):
        from unittest import mock

        from rest_framework.test import APIRequestFactory, force_authenticate

        from . import consommations_minene

        requete = APIRequestFactory().get("/api/consommations/minene/")
        force_authenticate(requete, user=mock.Mock(is_authenticated=True))
        resultat = {"Indicateurs": {"Prestations": 1}, "Anomalies": {"Signales": 1, "Beneficiaires": [{"Score": 20}]}}
        # Le garde central (droit consommations.view) est éprouvé ailleurs : seul le masquage propre à la vue est contrôlé ici
        with mock.patch("autorisations.garde.controler"), mock.patch.object(consommations_minene, "analyse", return_value=resultat), \
                mock.patch.object(consommations_minene, "a_le_droit", return_value=droit) as controle:
            reponse = consommations_minene.vue_minene(requete)
        controle.assert_called_once()
        self.assertEqual(controle.call_args.args[1], "consommations.fraude")
        return reponse.data

    def test_anomalies_masquees_sans_le_droit(self):
        donnees = self._appel(False)
        self.assertIsNone(donnees["Anomalies"])
        self.assertEqual(donnees["Indicateurs"]["Prestations"], 1)

    def test_anomalies_lues_avec_le_droit(self):
        self.assertEqual(self._appel(True)["Anomalies"]["Beneficiaires"], [{"Score": 20}])
