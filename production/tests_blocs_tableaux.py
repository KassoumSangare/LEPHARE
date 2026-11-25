"""Blocs du cockpit et du tableau de bord visibles selon les droits (demande du 2026-11-23) et paiement d'un reversement en
espèces : règles pures, sans base de données (catalogue, droits et modes de paiement simulés)."""
import copy
import importlib
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from autorisations import garde, rbac
from autorisations.catalogue import BLOCS_COCKPIT, BLOCS_TABLEAU, DROITS, ROLES_INITIAUX, TOUS
from . import blocs_tableaux, views_bordereaux, views_finance, views_tableau_de_bord
from .blocs_tableaux import chiffre_affaires_selon_blocs
from .decaissements import SQL_REVERSE, refus_reverse
from .views_tableau_de_bord import _selon_blocs

ZERO = Decimal(0)
TOUS_TABLEAU = frozenset(c.split(".", 1)[1] for c in BLOCS_TABLEAU)
CA = {"Total": 44, "Commissions": 40, "Accessoires": 4, "Rafas": 0, "Nombre": 3, "TauxMoyen": 20.0, "Precedent": 30,
      "Apporteurs": {"Total": 0}, "Net": 44, "PartDesPrimes": 14.7, "Percu": {"Total": 9}, "PercuPrecedent": 0,
      "EnAttente": {"Total": 5}, "ResteAPercevoir": {"Total": 35}}


def reponse():
    """Réponse du tableau de bord réduite à sa forme (mêmes clés que GET /api/tableau-de-bord/ avant filtrage)."""
    return {
        "Production": {"Nombre": 3, "PrimeTtc": 300, "Commission": 60, "Precedent": {"Nombre": 1, "PrimeTtc": 100, "Commission": 20}},
        "ParMois": [{"Mois": m, "PrimeTtc": 10, "PrimeTtcPrecedent": 5, "Encaisse": 4, "ChiffreAffaires": 2,
                     "ChiffreAffairesPrecedent": 1, "Percu": 0} for m in range(1, 13)],
        "ParBranche": [
            {"IdProduit": 1, "Branche": "Automobile", "Nombre": 2, "PrimeTtc": 200, "Commission": 30, "Accessoires": 5,
             "ChiffreAffaires": 35, "ChiffreAffairesPercu": 0, "TauxCommission": 20.0, "EncaisseExercice": 100, "TauxRecouvrement": 50.0},
            {"IdProduit": 2, "Branche": "Santé", "Nombre": 1, "PrimeTtc": 500, "ChiffreAffaires": 5, "EncaisseExercice": 0},
            {"IdProduit": None, "Branche": "RAFAS - Régime autofinancé", "Nombre": 0, "PrimeTtc": 0, "ChiffreAffaires": 90,
             "LibelleBase": "des cotisations du régime"},
        ],
        "ParCompagnie": [
            {"IdCompagnie": 1, "Compagnie": "NSIA", "Nombre": 2, "PrimeTtc": 200, "ChiffreAffaires": 35, "ChiffreAffairesPercu": 0},
            {"IdCompagnie": 2, "Compagnie": "SUNU", "Nombre": 0, "PrimeTtc": 0, "ChiffreAffaires": 0, "ChiffreAffairesPercu": 7},
        ],
        "Encaissements": {"Total": 100, "SurExercice": 90, "SurAnterieurs": 10, "TauxRecouvrement": 50.0, "EncaisseSurEmissions": 90,
                          "ResteAEncaisser": 210, "QuittancesImpayees": 2, "PrimeEmise": 300},
        "ChiffreAffaires": dict(CA),
        "Situation": {"Reversements": {"Montant": 1}, "Commissions": {"AReclamer": 1, "ReclamationsCumul": {"Nombre": 2, "Montant": 8}},
                      "ChequesEchus": {"Nombre": 0}, "Impayes": {"Nombre": 1}, "DerogationsEnAttente": 1},
        "Alertes": [{"Code": "reversements_retard", "Droit": "reversements.view"}, {"Code": "impayes", "Droit": "encaissements.view"},
                    {"Code": "derogations", "Droit": "approbations.view"}],
    }


def filtrer(blocs, droits=("reversements.view", "encaissements.view", "approbations.view", "commissions.view")):
    with mock.patch.object(views_tableau_de_bord, "a_le_droit", side_effect=lambda u, code: code in droits):
        return _selon_blocs(reponse(), frozenset(blocs), object())


class TableauDeBordParBloc(SimpleTestCase):
    def test_tous_les_blocs(self):
        r = filtrer(TOUS_TABLEAU)
        self.assertEqual(r["Blocs"], sorted(TOUS_TABLEAU))
        self.assertEqual(r["ChiffreAffaires"]["Total"], 44)
        self.assertEqual(r["ChiffreAffaires"]["Reclamations"], {"Cumul": {"Nombre": 2, "Montant": 8}})
        self.assertNotIn("Commission", r["Production"])  # chiffre d'affaires de la production : jamais affiché
        self.assertEqual(len(r["ParBranche"]), 3)
        self.assertEqual(len(r["Alertes"]), 3)
        self.assertEqual(sorted(r["Situation"]), ["Commissions", "Reversements"])

    def test_aucun_bloc(self):
        r = filtrer(set())
        for cle in ("ChiffreAffaires", "Production", "Encaissements", "Alertes", "Situation"):
            self.assertNotIn(cle, r)
        self.assertEqual((r["ParBranche"], r["ParCompagnie"]), ([], []))
        self.assertEqual(r["ParMois"][0], {"Mois": 1})

    def test_chaque_tuile_du_chiffre_d_affaires_a_ses_champs(self):
        self.assertEqual(set(filtrer({"percu"})["ChiffreAffaires"]), {"Percu", "PercuPrecedent"})
        self.assertEqual(set(filtrer({"reste_a_percevoir"})["ChiffreAffaires"]), {"EnAttente", "ResteAPercevoir", "Reclamations"})
        ca = filtrer({"chiffre_affaires"})["ChiffreAffaires"]
        self.assertNotIn("Percu", ca)
        self.assertNotIn("EnAttente", ca)

    def test_tuiles_des_encaissements(self):
        self.assertEqual(set(filtrer({"encaisse"})["Encaissements"]), {"Total", "SurExercice", "SurAnterieurs"})
        self.assertNotIn("Total", filtrer({"recouvrement"})["Encaissements"])

    def test_graphiques_mensuels(self):
        self.assertEqual(set(filtrer({"ca_par_mois"})["ParMois"][0]), {"Mois", "ChiffreAffaires", "ChiffreAffairesPrecedent", "Percu"})
        self.assertEqual(set(filtrer({"primes_par_mois"})["ParMois"][0]), {"Mois", "PrimeTtc", "PrimeTtcPrecedent", "Encaisse"})

    def test_branches_sans_le_chiffre_d_affaires(self):
        r = filtrer({"branches", "compagnies"})
        self.assertEqual([b["Branche"] for b in r["ParBranche"]], ["Santé", "Automobile"])  # RAFAS retirée, ordre des primes
        self.assertFalse({"ChiffreAffaires", "Commission", "TauxCommission", "LibelleBase"} & {c for b in r["ParBranche"] for c in b})
        self.assertEqual([c["Compagnie"] for c in r["ParCompagnie"]], ["NSIA"])
        self.assertNotIn("ChiffreAffaires", r["ParCompagnie"][0])

    def test_branches_avec_le_chiffre_d_affaires(self):
        r = filtrer({"branches", "ca_listes"})
        self.assertEqual(len(r["ParBranche"]), 3)
        self.assertEqual(r["ParBranche"][0]["ChiffreAffaires"], 35)

    def test_alertes_selon_le_droit_du_module(self):
        r = filtrer({"alertes"}, droits=("encaissements.view",))
        self.assertEqual([a["Code"] for a in r["Alertes"]], ["impayes"])
        self.assertEqual(r["Situation"], {})


class ChiffreAffairesSelonBlocs(SimpleTestCase):
    def test_aucun_bloc_du_chiffre_d_affaires(self):
        self.assertIsNone(chiffre_affaires_selon_blocs(dict(CA), {"primes"}))

    def test_mois_du_cockpit(self):
        ca = {**CA, "Mois": {"Total": 7, "Percu": 3}}
        self.assertEqual(chiffre_affaires_selon_blocs(ca, {"percu"})["Mois"], {"Percu": 3})
        self.assertEqual(chiffre_affaires_selon_blocs(ca, {"chiffre_affaires"})["Mois"], {"Total": 7})


class BlocsVisibles(SimpleTestCase):
    def _visibles(self, catalogue, droits):
        filtre = mock.MagicMock()
        filtre.values_list.return_value = list(catalogue)
        with mock.patch("autorisations.models.Droit.objects.filter", return_value=filtre), \
                mock.patch.object(blocs_tableaux, "droits_utilisateur", return_value=frozenset(droits)):
            return blocs_tableaux.blocs_cockpit(object())

    def test_jamais_d_acces_par_defaut(self):
        # Droits des blocs absents du catalogue (avant la migration 0017) et aucun droit : rien
        self.assertEqual(self._visibles([], []), frozenset())
        self.assertEqual(self._visibles(BLOCS_COCKPIT, []), frozenset())

    def test_avant_la_migration_regle_d_avant(self):
        self.assertEqual(self._visibles([], ["contrats.view"]),
                         frozenset({"primes", "polices", "branches", "echeances", "derniers_contrats"}))
        self.assertEqual(self._visibles([], ["reporting.view"]),
                         frozenset({"chiffre_affaires", "percu", "reste_a_percevoir", "commissions_listes"}))

    def test_regle_d_avant_pour_chaque_bloc(self):
        self.assertEqual(set(blocs_tableaux.DROITS_AVANT_MIGRATION), set(BLOCS_COCKPIT) | set(BLOCS_TABLEAU))

    def test_selon_les_droits_du_profil(self):
        self.assertEqual(self._visibles(BLOCS_COCKPIT, ["cockpit.devis", "cockpit.a_traiter", "contrats.view"]),
                         frozenset({"devis", "a_traiter"}))

    def test_listes_de_clients_exigent_le_module(self):
        listes = ["cockpit.echeances", "cockpit.derniers_contrats", "cockpit.derniers_devis"]
        self.assertEqual(self._visibles(BLOCS_COCKPIT, listes), frozenset())
        self.assertEqual(self._visibles(BLOCS_COCKPIT, listes + ["contrats.view"]), frozenset({"echeances", "derniers_contrats"}))
        self.assertEqual(self._visibles(BLOCS_COCKPIT, listes + ["devis.view"]), frozenset({"derniers_devis"}))


class MigrationDesRoles(SimpleTestCase):
    """Chaque rôle reçoit les blocs qu'il voyait avant (migration autorisations 0017)."""
    migration = importlib.import_module("autorisations.migrations.0017_blocs_cockpit_tableau")

    def test_gestionnaire_sans_chiffre_d_affaires_au_cockpit(self):
        codes = {"contrats.view", "devis.view", "encaissements.view", "reversements.view"}
        blocs = set(self.migration.blocs_du_role(codes, familles_en_base=set()))
        self.assertTrue({"cockpit.primes", "cockpit.polices", "cockpit.devis", "cockpit.encaisse", "cockpit.a_reverser",
                         "cockpit.a_traiter", "cockpit.branches"} <= blocs)
        self.assertFalse({"cockpit.chiffre_affaires", "cockpit.commissions_listes", "cockpit.commissions"} & blocs)
        self.assertTrue({c for c in BLOCS_TABLEAU} <= blocs)  # tableau de bord : tous les blocs, comme avant

    def test_famille_retiree_par_la_migration_0016(self):
        familles = {f"tableaux.{f}" for f in self.migration.ANCIENNES_FAMILLES}
        codes = {"commissions.view", "contrats.view"} | (familles - {"tableaux.chiffre_affaires"})
        blocs = set(self.migration.blocs_du_role(codes, familles_en_base=familles))
        self.assertNotIn("cockpit.chiffre_affaires", blocs)
        self.assertNotIn("tableau.ca_par_mois", blocs)
        self.assertIn("cockpit.commissions", blocs)  # tuile affichée sans le chiffre d'affaires


class PaiementDuCabinetEnEspeces(SimpleTestCase):
    MODES = {2: ("ESP", "espèces"), 3: ("CHQ", "chèque"), 4: ("VIR", "virement"), 27: ("ESP", "espèce ppa"),
             28: ("CHQ", "a la compagnie"), 29: ("PYM", "paiement mobile")}

    def _controle(self, donnees):
        def lignes(_sql, params):
            abrege, libelle = self.MODES.get(params[0], ("", ""))
            return [{"abrege": abrege, "libelle": libelle}] if abrege else []
        with mock.patch.object(views_finance, "_lignes", side_effect=lignes):
            return views_finance.controle_paiement_cabinet(donnees)

    def test_especes_sans_banque_ni_numero(self):
        self.assertEqual(self._controle({"IdMode": 2}), 2)

    def test_cheque_et_virement_exigent_la_banque(self):
        with self.assertRaisesMessage(views_finance.ErreurFinance, "Banque du cabinet"):
            self._controle({"IdMode": 4})
        with self.assertRaisesMessage(views_finance.ErreurFinance, "N° du chèque"):
            self._controle({"IdMode": 3, "IdBanque": 5})
        self.assertEqual(self._controle({"IdMode": 3, "IdBanque": 5, "NumeroCheque": "123"}), 3)

    def test_modes_refuses(self):
        for mode in (27, 28, 29):
            with self.assertRaisesMessage(views_finance.ErreurFinance, "par chèque, par virement ou en espèces"):
                self._controle({"IdMode": mode, "IdBanque": 5, "NumeroCheque": "1"})

    def test_textes_du_bordereau_et_du_courrier(self):
        entete = {"valide": True, "datereversement": date(2026, 11, 23), "montantreversement": 150000, "banque": None,
                  "abrege": "ESP", "numerocheque": None, "mode": "Espèces"}
        self.assertEqual(views_bordereaux._paiement_cabinet(copy.copy(entete)), "Espèces du 23/11/2026 de FCFA 150 000")
        self.assertEqual(views_bordereaux._paiement_cabinet(entete, pour_courrier=True),
                         "le règlement en espèces du 23/11/2026 de FCFA 150 000")


class OngletsSelonLeProfil(SimpleTestCase):
    """Onglets du tableau de bord et du guide de l'administration (demande du 2026-11-24, migration autorisations 0018)."""

    def _droits(self, droits_roles, en_base):
        def filtre(**criteres):
            resultat = mock.MagicMock()
            if "code__in" in criteres:
                resultat.values_list.return_value = [c for c in criteres["code__in"] if c in en_base]
            else:
                resultat.values_list.return_value.distinct.return_value = list(droits_roles)
            return resultat

        utilisateur = SimpleNamespace(is_authenticated=True, is_active=True, expiry_date=None, is_admin=False)
        rbac._remplacants_en_base.clear()
        try:
            with mock.patch("autorisations.models.Droit.objects.filter", side_effect=filtre):
                return rbac.droits_utilisateur(utilisateur)
        finally:
            rbac._remplacants_en_base.clear()

    def test_catalogue(self):
        self.assertTrue({"tableau.view", "guide.view"} <= set(TOUS))
        self.assertNotIn("tableau.view", BLOCS_TABLEAU)  # droit de l'écran, pas un bloc
        self.assertEqual(views_tableau_de_bord.DROIT, "tableau.view")

    def test_avant_la_migration_consulter_les_etats_en_tient_lieu(self):
        self.assertIn("tableau.view", self._droits({"reporting.view"}, en_base=set()))
        self.assertNotIn("tableau.view", self._droits({"contrats.view"}, en_base=set()))  # jamais d'accès par défaut

    def test_apres_la_migration_seul_le_role_decide(self):
        self.assertNotIn("tableau.view", self._droits({"reporting.view"}, en_base={"tableau.view"}))
        self.assertIn("tableau.view", self._droits({"tableau.view"}, en_base={"tableau.view"}))
        self.assertNotIn("guide.view", self._droits({"reporting.view", "users.view"}, en_base={"tableau.view", "guide.view"}))


class OreoleSanteSansReversement(SimpleTestCase):
    """Part Santé d'Oreole Santé gérée sans assureur (consigne du 2026-11-24) : ni reversée ni réclamée, honoraires et frais
    courtiers gardés à l'encaissement ; IA et AFA du package reversées comme toute prime d'assureur."""

    def ligne(self, **valeurs):
        return {"annulee": False, "abrege": "CHQ", "statutcheque": None, "montant_encaissement": Decimal("100000"),
                "montantreverse": ZERO, "partcompagnie": None, "sansreversement": False, "dateencaissement": date(2026, 11, 2),
                **valeurs}

    def test_part_sante_ni_reversee_ni_proposee(self):
        sante = self.ligne(sansreversement=True, partcompagnie=Decimal("0.42"))
        self.assertEqual(views_finance._a_reverser(sante), ZERO)
        with mock.patch.object(views_finance, "debut_reversements", return_value=date(2025, 12, 1)):
            self.assertEqual(views_finance._statut_encaissement(sante, ZERO), "SANS_REVERSEMENT")
            # Reversée à MCI avant la consigne : reste « Reversé » jusqu'à l'annulation de son bordereau
            self.assertEqual(views_finance._statut_encaissement(dict(sante, montantreverse=Decimal("42000")), ZERO), "REVERSE")
            # IA ou AFA du package, toute autre prime : à reverser en entier
            autre = self.ligne()
            self.assertEqual(views_finance._a_reverser(autre), Decimal("100000"))
            self.assertEqual(views_finance._statut_encaissement(autre, Decimal("100000")), "A_REVERSER")

    def test_aucune_commission_a_reclamer(self):
        self.assertTrue(views_finance.COMMISSION_DUE.startswith("CASE WHEN EXISTS (SELECT 1 FROM lephare_oreole_package"))
        self.assertIn("opk.iddevis_sante = ct.iddevis", views_finance.COMMISSION_DUE.format(d="d", de="de", ct="ct"))

    def test_honoraires_percus_a_l_encaissement(self):
        curseur = mock.MagicMock()
        curseur.description = [("idproduit",), ("idcompagnie",), ("jour",), ("montant",)]
        curseur.fetchall.return_value = []
        curseur.fetchone.return_value = (True,)
        p = {"debut": date(2026, 1, 1), "au": date(2026, 11, 24), "debut_n1": date(2025, 1, 1), "au_n1": date(2025, 11, 24)}
        from . import chiffre_affaires
        chiffre_affaires.lire_percu(curseur, p)
        requetes = " ".join(str(appel.args[0]) for appel in curseur.execute.call_args_list)
        self.assertIn("c.accessoireintermediaire", requetes)
        self.assertIn("c.commissionintermediaire", requetes)

    def _suivi(self, oreole):
        """Tableau « Suivi des primes et commissions » d'une quittance reversée (bordereau payé), sans base de données."""
        detail = {"iddetailreversement": 1, "idreversement": 5, "montantreverse": Decimal("7200000"), "idencaissement": 9,
                  "numeroquittance": "Q1", "datebordereau": date(2026, 11, 10), "datedecharge": None, "numero": "B1",
                  "nature": views_bordereaux.REVERSEMENT, "datereversement": date(2026, 11, 10),
                  "montantreversement": Decimal("7200000"), "valide": True, "numerocheque": "123", "mode": "Chèque",
                  "abrege": "CHQ", "banque": None}
        q = {"idquittance": 1, "numeroquittance": "Q1", "idcontrat": 2, "client": "CLIENT", "idproduit": 5, "libelleproduit": "SANTE",
             "numeropolice": "P1", "policecompagnie": None, "avenantcompagnie": None, "avenant": None, "dateeffet": None,
             "dateexpiration": None, "primeht": Decimal("7200000"), "primettc": Decimal("7200000"), "partcompagnie": None,
             "acccourtier": ZERO, "taux": Decimal("7"), "commission": Decimal("504000"), "oreole": oreole}
        with mock.patch.object(views_bordereaux, "_lignes", side_effect=[[detail], []]), \
                mock.patch.object(views_bordereaux, "_quittances", return_value={"Q1": q}), \
                mock.patch.object(views_bordereaux, "_reglements", return_value={}):
            return views_bordereaux.tableau_reversement(29, date(2026, 1, 1), date(2026, 12, 31))[0]

    def test_suivi_sans_commission_a_percevoir(self):
        # Cotisation reversée à MCI avant la consigne : rien à percevoir de la compagnie, comme l'état des commissions
        ligne = self._suivi(oreole=True)
        self.assertEqual((ligne["CommissionAPercevoir"], ligne["SoldeCommission"]), (0, 0))
        self.assertIn("honoraires gardés à l'encaissement", ligne["Observation"])
        # Toute autre prime reversée : commission à percevoir de la compagnie
        self.assertEqual(self._suivi(oreole=False)["SoldeCommission"], 504000)


class AnnulationDUnReversement(SimpleTestCase):
    """Annulation d'un bordereau de reversement avec le droit dédié « Annuler un reversement » (demande du 2026-11-24,
    migration autorisations 0019)."""

    _droits = OngletsSelonLeProfil._droits

    def test_catalogue(self):
        droit = next(d for d in DROITS if d[0] == "reversements.cancel")
        _, libelle, _, sensible, motif, _ = droit
        self.assertEqual(libelle, "Annuler un reversement")
        self.assertTrue(sensible)
        self.assertTrue(motif)  # motif obligatoire, exigé par la garde (en-tête X-Motif)
        self.assertIn("reversements.cancel", {r[0]: r[3] for r in ROLES_INITIAUX}["RESPONSABLE"])

    def test_route_d_annulation(self):
        regle, _ = garde._regle(garde.REGLES, "POST", "finance/bordereaux/12/annuler/")
        self.assertEqual(regle.droit, "reversements.cancel")
        # Valider (payer) un bordereau reste un droit à part
        regle, _ = garde._regle(garde.REGLES, "POST", "finance/reversements/12/valider/")
        self.assertEqual(regle.droit, "reversements.validate")

    def test_avant_la_migration_valider_en_tient_lieu(self):
        self.assertIn("reversements.cancel", self._droits({"reversements.validate"}, en_base=set()))
        self.assertNotIn("reversements.cancel", self._droits({"reversements.create"}, en_base=set()))

    def test_refus_d_annuler_un_encaissement_reverse(self):
        curseur = mock.MagicMock()
        curseur.fetchall.return_value = [("11861126B0004",)]
        self.assertEqual(
            refus_reverse(curseur, [750], "Ce chèque"),
            "Ce chèque a réglé une prime déjà reversée à la compagnie (bordereau N° 11861126B0004) : annulez d'abord ce "
            "bordereau dans Reversements aux compagnies.")
        # Bordereau annulé : la requête ne le renvoie plus, plus rien n'est reversé
        curseur.fetchall.return_value = []
        curseur.fetchone.return_value = (False,)
        self.assertEqual(refus_reverse(curseur, [750], "Ce chèque"), "")
        self.assertIn("NOT COALESCE(rc.pieceannulee, FALSE)", SQL_REVERSE)

    def test_apres_la_migration_seul_le_role_decide(self):
        en_base = {"tableau.view", "reversements.cancel"}
        self.assertNotIn("reversements.cancel", self._droits({"reversements.validate"}, en_base=en_base))
        self.assertIn("reversements.cancel", self._droits({"reversements.cancel"}, en_base=en_base))
