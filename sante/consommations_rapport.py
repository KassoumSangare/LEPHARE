"""
Rapport d'analyse des dépenses santé (Word), seul export du suivi des consommations (demande du 2026-11-06 : « je voudrais que seul le rapport
puisse être exporté » ; modèle : RAPPORT OREOLE SANTE 2026.docx). Gabarit : sante/modeles/rapport_consommations.docx (en-tête, logo et pied de
page du modèle, corps vidé). Plan du modèle : I. effectifs, II. dépenses, III. entreprises à risque et leurs fiches ; IV. contrôle de gestion
(provision face à la consommation, feuille CONTRÔLE DE GESTION de l'ETAT) quand l'état des cotisations est importé.
Calculs : consommations_pilotage.py. Données de santé : réservé au droit consommations.view, chaque export est inscrit au journal d'audit.
"""

import io
import os
from collections import defaultdict
from decimal import Decimal

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from django.db import connection
from django.http import HttpResponse
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from autorisations.journal import journaliser
from production.renouvellement import AUTHENTIFICATION

from .consommations import ErreurConsommation, _reponse
from .consommations_pilotage import (MOIS, STATUTS, GENRES, TRANCHES, _age, _div, _periode, charger, entreprises_a_risque,
                                     indicateurs, repartition, tableau_de_bord, tranche)

GABARIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modeles", "rapport_consommations.docx")
ZERO = Decimal("0")
BLEU = RGBColor(0x1F, 0x3A, 0x68)
FICHES_MAX = 5


def _f(v):
    if v is None:
        return "-"
    return f"{round(float(v)):,}".replace(",", " ")


def _p(v):
    return "-" if v is None else f"{float(v) * 100:.2f} %".replace(".", ",")


def _d(jour):
    return jour.strftime("%d/%m/%Y") if jour else ""


class Rapport:
    def __init__(self):
        self.doc = Document(GABARIT) if os.path.exists(GABARIT) else Document()
        style = self.doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(10)
        self.numero = 0

    def titre(self, texte, niveau=1):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14 if niveau == 1 else 8)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(texte)
        r.bold = True
        r.font.size = Pt({0: 16, 1: 13, 2: 11.5, 3: 10.5}[niveau])
        r.font.color.rgb = BLEU
        if niveau == 0:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return p

    def para(self, texte, italique=False, taille=10):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(texte)
        r.italic = italique
        r.font.size = Pt(taille)
        return p

    def tableau(self, legende, entetes, lignes, droite=(), taille=8.5, total=None):
        self.numero += 1
        legende_p = self.doc.add_paragraph()
        legende_p.paragraph_format.keep_with_next = True
        r = legende_p.add_run(f"Tableau {self.numero} - {legende}")
        r.bold = True
        r.font.size = Pt(9.5)
        lignes = list(lignes) + ([total] if total else [])
        t = self.doc.add_table(rows=1 + len(lignes), cols=len(entetes))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, e in enumerate(entetes):
            self._cellule(t.cell(0, j), e, gras=True, fond="1F3A68", couleur=RGBColor(0xFF, 0xFF, 0xFF), taille=taille, droite=j in droite)
        for i, ligne in enumerate(lignes, start=1):
            gras = bool(total) and i == len(lignes)
            for j, v in enumerate(ligne):
                self._cellule(t.cell(i, j), v, gras=gras, fond="EAF0F8" if gras else None, taille=taille, droite=j in droite)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    @staticmethod
    def _cellule(cellule, texte, gras=False, fond=None, couleur=None, taille=8.5, droite=False):
        cellule.text = ""
        p = cellule.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if droite else WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run("" if texte is None else str(texte))
        r.bold = gras
        r.font.size = Pt(taille)
        if couleur:
            r.font.color.rgb = couleur
        if fond:
            tc = cellule._tc.get_or_add_tcPr()
            ombre = OxmlElement("w:shd")
            ombre.set(qn("w:val"), "clear")
            ombre.set(qn("w:color"), "auto")
            ombre.set(qn("w:fill"), fond)
            tc.append(ombre)

    def repartition(self, legende, colonne, groupes, beneficiaires=False, limite=None):
        groupes = groupes[:limite] if limite else groupes
        if beneficiaires:
            entetes = [colonne, "Bénéficiaires", "Dépenses", "%", "Actes", "% actes", "Coût moyen / acte"]
            lignes = [(g["Libelle"], _f(g["Beneficiaires"]), _f(g["Depenses"]), _p(g["Part"]), _f(g["Actes"]), _p(g["PartActes"]), _f(g["CoutParActe"])) for g in groupes]
            droite = (1, 2, 3, 4, 5, 6)
        else:
            entetes = [colonne, "Dépenses", "%", "Actes", "% actes", "Coût moyen / acte"]
            lignes = [(g["Libelle"], _f(g["Depenses"]), _p(g["Part"]), _f(g["Actes"]), _p(g["PartActes"]), _f(g["CoutParActe"])) for g in groupes]
            droite = (1, 2, 3, 4, 5)
        self.tableau(legende, entetes, lignes, droite)

    def octets(self):
        tampon = io.BytesIO()
        self.doc.save(tampon)
        return tampon.getvalue()


def _indicateurs_tableau(r, legende, ind, effectif_libelle="Effectif total de bénéficiaires"):
    r.tableau(legende, ["Indicateur", "Valeur"], [
        (effectif_libelle, _f(ind["Effectif"])), ("Bénéficiaires ayant exposé des frais", _f(ind["Consommants"])),
        ("Bénéficiaires n'ayant pas exposé de frais", _f(ind["NonConsommants"])), ("Nombre d'actes", _f(ind["Actes"])),
        ("Taux de recours", _p(ind["TauxRecours"])), ("Montant total réclamé", _f(ind["Reclame"])), ("Montant total remboursé", _f(ind["Rembourse"])),
        ("Coût moyen par bénéficiaire", _f(ind["CoutParBeneficiaire"])), ("Coût moyen par acte", _f(ind["CoutParActe"])),
        ("Fréquence moyenne d'actes", "-" if ind["Frequence"] is None else f"{ind['Frequence']:.1f}".replace(".", ",")),
        ("Âge moyen", "-" if ind["AgeMoyen"] is None else f"{ind['AgeMoyen']} ans"),
    ], droite=(1,))


def _famille_tranche(r, legende, prestations, au):
    tranches = [t[2] for t in TRANCHES]
    cumul = defaultdict(lambda: defaultdict(lambda: ZERO))
    for p in prestations:
        cumul[p["famille"] or "Non renseigné"][tranche(_age(p["date_naissance"], au))] += p["mt_rembourse"]
    familles = sorted(cumul, key=lambda f: -sum(cumul[f].values()))
    lignes = [[f] + [_f(cumul[f].get(t)) if cumul[f].get(t) else "-" for t in tranches] + [_f(sum(cumul[f].values()))] for f in familles]
    total = ["Total"] + [_f(sum((cumul[f].get(t, ZERO) for f in familles), ZERO)) for t in tranches] + [_f(sum((sum(cumul[f].values()) for f in familles), ZERO))]
    r.tableau(legende, ["Famille"] + [t.replace(" ans", "") for t in tranches] + ["Total"], lignes, droite=tuple(range(1, len(tranches) + 2)), taille=6.5, total=total)


def _familles_depensieres(r, legende, prestations, seuil=None, limite=None):
    """Familles (assuré principal) les plus dépensières, avec leurs bénéficiaires et familles de prestation (comme le modèle)."""
    par_assure = defaultdict(lambda: ZERO)
    for p in prestations:
        par_assure[p["matricule_assure"]] += p["mt_rembourse"]
    retenus = [m for m, v in sorted(par_assure.items(), key=lambda kv: -kv[1]) if seuil is None or v > seuil][:limite]
    detail = defaultdict(lambda: [ZERO, 0])
    noms = {}
    for p in prestations:
        if p["matricule_assure"] in retenus:
            d = detail[(p["matricule_assure"], p["beneficiaire"], p["police"], p["famille"])]
            d[0] += p["mt_rembourse"]
            d[1] += 1
            noms[p["matricule_assure"]] = p["assure"]
    lignes = []
    for m in retenus:
        for (ma, benef, police, famille), (dep, actes) in sorted(((k, v) for k, v in detail.items() if k[0] == m), key=lambda kv: -kv[1][0]):
            lignes.append((f"{noms.get(m, '')} ({m})", benef, police, famille, _f(dep), _f(actes)))
    if lignes:
        r.tableau(legende, ["Assuré principal", "Bénéficiaire", "Souscripteur", "Famille de prestation", "Dépenses", "Actes"], lignes, droite=(4, 5), taille=7.5)
    else:
        r.para("Aucune famille ne dépasse ce seuil sur la période.", italique=True)


def _top(r, legende, prestations, cle, colonne, limite=20):
    r.repartition(legende, colonne, repartition(prestations, cle), beneficiaires=True, limite=limite)


def _effectifs(r, effectif, du, au):
    actifs = [e for e in effectif if e["actif"]]
    statuts = defaultdict(list)
    for e in actifs:
        statuts[e["statut"]].append(e)
    ages = [a for a in (_age(e["date_naissance"], au) for e in actifs) if a is not None]
    r.titre("I.1. Description de la population assurée", 2)
    r.tableau("Indicateurs clés de l'effectif", ["Indicateur", "Valeur"], [
        ("Effectif total", _f(len(actifs))), ("Nombre d'assurés principaux", _f(len(statuts["A"]))), ("Nombre de conjoints", _f(len(statuts["C"]))),
        ("Nombre d'enfants", _f(len(statuts["E"]))), ("Âge moyen de l'effectif", f"{round(sum(ages) / len(ages))} ans" if ages else "-"),
    ], droite=(1,))
    par_police = defaultdict(lambda: {"Maintenus": 0, "Sortis": 0, "Nouveaux": 0, "Effectif": 0, "A": 0, "C": 0, "E": 0, "Ages": []})
    for e in effectif:
        x = par_police[e["police"]]
        if not e["actif"]:
            x["Sortis"] += 1
            continue
        x["Effectif"] += 1
        x["Nouveaux" if e["date_effet"] and e["date_effet"] >= du else "Maintenus"] += 1
        x[e["statut"] if e["statut"] in ("A", "C", "E") else "E"] += 1
        a = _age(e["date_naissance"], au)
        if a is not None:
            x["Ages"].append(a)
    polices = sorted(par_police, key=lambda p: -par_police[p]["Effectif"])
    r.tableau("Effectif consolidé par entreprise", ["Entreprise", "Maintenus", "Sortis", "Nouveaux", "Effectif"],
              [(p, _f(par_police[p]["Maintenus"]), _f(par_police[p]["Sortis"]), _f(par_police[p]["Nouveaux"]), _f(par_police[p]["Effectif"])) for p in polices],
              droite=(1, 2, 3, 4), total=("Total", _f(sum(x["Maintenus"] for x in par_police.values())), _f(sum(x["Sortis"] for x in par_police.values())),
                                         _f(sum(x["Nouveaux"] for x in par_police.values())), _f(len(actifs))))
    r.tableau("Répartition des effectifs par statut et par entreprise", ["Entreprise", "A", "C", "E", "Total", "Âge moyen"],
              [(p, _f(par_police[p]["A"]), _f(par_police[p]["C"]), _f(par_police[p]["E"]), _f(par_police[p]["Effectif"]),
                f"{round(sum(par_police[p]['Ages']) / len(par_police[p]['Ages']))}" if par_police[p]["Ages"] else "-") for p in polices if par_police[p]["Effectif"]],
              droite=(1, 2, 3, 4, 5))
    lignes = []
    for s in ("A", "C", "E"):
        a = [x for x in (_age(e["date_naissance"], au) for e in statuts[s]) if x is not None]
        lignes.append((f"{s} - {STATUTS[s]}", _f(len(statuts[s])), _p(_div(len(statuts[s]), len(actifs))), f"{round(sum(a) / len(a))} ans" if a else "-"))
    r.tableau("Répartition des effectifs par statut", ["Statut", "Bénéficiaires", "%", "Âge moyen"], lignes, droite=(1, 2, 3),
              total=("Total", _f(len(actifs)), "100 %", f"{round(sum(ages) / len(ages))} ans" if ages else "-"))
    par_tranche = defaultdict(lambda: {"A": 0, "C": 0, "E": 0, "Ages": []})
    for e in actifs:
        a = _age(e["date_naissance"], au)
        x = par_tranche[tranche(a)]
        x[e["statut"] if e["statut"] in ("A", "C", "E") else "E"] += 1
        if a is not None:
            x["Ages"].append(a)
    ordre = [t[2] for t in TRANCHES] + ["Non renseigné"]
    presentes = [t for t in ordre if t in par_tranche]
    r.tableau("Répartition des effectifs par tranche d'âge", ["Tranche d'âge", "Bénéficiaires", "%", "Âge moyen"],
              [(t, _f(sum(par_tranche[t][s] for s in "ACE")), _p(_div(sum(par_tranche[t][s] for s in "ACE"), len(actifs))),
                f"{round(sum(par_tranche[t]['Ages']) / len(par_tranche[t]['Ages']))} ans" if par_tranche[t]["Ages"] else "-") for t in presentes], droite=(1, 2, 3),
              total=("Total", _f(len(actifs)), "100 %", ""))
    r.tableau("Répartition des effectifs par tranche d'âge et par statut", ["Tranche d'âge", "A", "C", "E", "Total", "%"],
              [(t, _f(par_tranche[t]["A"]), _f(par_tranche[t]["C"]), _f(par_tranche[t]["E"]), _f(sum(par_tranche[t][s] for s in "ACE")),
                _p(_div(sum(par_tranche[t][s] for s in "ACE"), len(actifs)))) for t in presentes], droite=(1, 2, 3, 4, 5))
    # Contrôle de cohérence (même liste que le modèle)
    r.titre("I.2. Contrôle de cohérence et anomalies", 2)
    r.para("Contrôles réalisés sur l'effectif avant exploitation : unicité des personnes, âges plausibles, statuts cohérents avec l'assuré principal.")
    identites = defaultdict(set)
    for e in actifs:
        if e["nom"] and e["date_naissance"]:
            identites[(e["nom"].strip().upper(), (e["prenoms"] or "").strip().upper(), e["date_naissance"])].add(e["matricule_beneficiaire"])
    doublons = sum(1 for v in identites.values() if len(v) > 1)
    ages_incoherents = sum(1 for e in actifs if (lambda a: a is not None and (a < 0 or a > 100 or (e["statut"] in ("A", "C") and a < 16)))(_age(e["date_naissance"], au)))
    principaux = {e["matricule_beneficiaire"] for e in actifs if e["statut"] == "A"}
    statuts_errones = sum(1 for e in actifs if e["statut"] not in ("A", "C", "E") or (e["statut"] == "A" and e["matricule_beneficiaire"] != e["matricule_assure"])
                          or (e["statut"] in ("C", "E") and e["matricule_assure"] not in principaux))
    r.tableau("Anomalies de l'effectif", ["Type d'anomalie", "Nombre de cas", "Statut"], [
        ("Doublon d'identité (même nom, prénoms et naissance)", _f(doublons), "Conforme" if not doublons else "À vérifier"),
        ("Âge incohérent (négatif, plus de 100 ans, assuré ou conjoint de moins de 16 ans)", _f(ages_incoherents), "Conforme" if not ages_incoherents else "À vérifier"),
        ("Statut erroné (hors A, C, E ou sans assuré principal)", _f(statuts_errones), "Conforme" if not statuts_errones else "À vérifier"),
    ], droite=(1,))


def _fiche(r, police, prestations, effectif, au):
    ps = [p for p in prestations if p["police"] == police]
    beneficiaires = [e for e in effectif if e["police"] == police and e["actif"]]
    r.titre(f"Fiche d'entreprise : {police}", 3)
    _indicateurs_tableau(r, "Indicateurs clés de l'entreprise", indicateurs(ps, beneficiaires, au))
    r.repartition("Répartition des dépenses par famille de prestation", "Famille de prestation", repartition(ps, lambda p: p["famille"]))
    r.repartition("Répartition des dépenses par statut", "Statut", repartition(ps, lambda p: f"{p['statut']} - {STATUTS.get(p['statut'], 'Non renseigné')}"))
    r.repartition("Répartition des dépenses par tranche d'âge", "Tranche d'âge", repartition(ps, lambda p: tranche(_age(p["date_naissance"], au))))
    r.repartition("Répartition des dépenses par genre", "Genre", repartition(ps, lambda p: GENRES.get(p["genre"], "Non renseigné")))
    _top(r, "Top 10 des centres prescripteurs", ps, lambda p: p["centre_prescripteur"], "Centre prescripteur", 10)
    _top(r, "Top 10 des centres exécutants", ps, lambda p: p["centre_executant"], "Centre exécutant", 10)
    _familles_depensieres(r, "Top 10 des familles les plus dépensières", ps, limite=10)
    _top(r, "Top 10 des médecins les plus coûteux", ps, lambda p: p["medecin"], "Médecin", 10)


def produire(params):
    with connection.cursor() as cursor:
        exercice, du, au, _exercices = _periode(cursor, params)
        garant = str(params.get("garant") or "").strip()
        prestations, effectif = charger(cursor, du, au, garant)
    if not prestations and not effectif:
        raise ErreurConsommation("Aucune donnée sur cette période : importez d'abord les relevés du gestionnaire.")
    bord = tableau_de_bord(params)
    r = Rapport()
    r.titre(f"ANALYSE DES DÉPENSES SANTÉ {exercice} OREOLE SANTÉ", 0)
    sous = r.para(f"Du {_d(du)} au {_d(au)}" + (f" - garant {garant}" if garant else ""))
    sous.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r.para("Source : relevés de prestations et effectif du gestionnaire importés dans LE PHARE ; mois et période selon la date de clôture du relevé ; "
           "âges à la fin de la période. Document contenant des données de santé : diffusion restreinte.", italique=True, taille=8.5)

    r.titre("I. ANALYSE DES EFFECTIFS", 1)
    _effectifs(r, effectif, du, au)

    r.titre("II. ANALYSE GLOBALE DES DÉPENSES SANTÉ", 1)
    portefeuille = indicateurs(prestations, [e for e in effectif if e["actif"]], au)
    _indicateurs_tableau(r, "Indicateurs clés du portefeuille", portefeuille, "Effectif total assuré")
    mensuel = defaultdict(lambda: [ZERO, 0])
    for p in prestations:
        m = mensuel[(p["date_cloture"].year, p["date_cloture"].month)]
        m[0] += p["mt_rembourse"]
        m[1] += 1
    total = sum((v[0] for v in mensuel.values()), ZERO)
    r.tableau(f"Dépenses mensuelles {exercice}", ["Mois", "Dépenses", "%", "Actes", "% actes", "Coût moyen / acte"],
              [(f"{MOIS[m - 1]} {a}", _f(v[0]), _p(_div(v[0], total)), _f(v[1]), _p(_div(v[1], len(prestations))), _f(_div(v[0], v[1])))
               for (a, m), v in sorted(mensuel.items())], droite=(1, 2, 3, 4, 5),
              total=("Total", _f(total), "100 %", _f(len(prestations)), "100 %", _f(_div(total, len(prestations)))))
    par_entreprise = repartition(prestations, lambda p: p["police"])
    r.tableau("Répartition des dépenses par entreprise", ["Entreprise", "Bénéficiaires", "Dépenses", "%", "Actes", "Coût moyen / bénéficiaire", "Coût moyen / acte"],
              [(g["Libelle"], _f(g["Beneficiaires"]), _f(g["Depenses"]), _p(g["Part"]), _f(g["Actes"]), _f(_div(g["Depenses"], g["Beneficiaires"])), _f(g["CoutParActe"]))
               for g in par_entreprise], droite=(1, 2, 3, 4, 5, 6), taille=7.5)
    r.repartition("Répartition des dépenses par famille de prestation", "Famille de prestation", repartition(prestations, lambda p: p["famille"]))
    r.repartition("Répartition des dépenses par statut", "Statut", repartition(prestations, lambda p: f"{p['statut']} - {STATUTS.get(p['statut'], 'Non renseigné')}"))
    r.repartition("Répartition des dépenses par tranche d'âge", "Tranche d'âge", repartition(prestations, lambda p: tranche(_age(p["date_naissance"], au))))
    _famille_tranche(r, "Dépenses par famille de prestation et tranche d'âge", prestations, au)
    _top(r, "Top 20 des centres prescripteurs", prestations, lambda p: p["centre_prescripteur"], "Centre prescripteur")
    _top(r, "Top 20 des centres exécutants", prestations, lambda p: p["centre_executant"], "Centre exécutant")
    _familles_depensieres(r, "Familles dont le montant remboursé dépasse 1 000 000 F", prestations, seuil=Decimal("1000000"))
    _top(r, "Top 20 des médecins les plus coûteux", prestations, lambda p: p["medecin"], "Médecin")
    couples = repartition([p for p in prestations if p["centre_prescripteur"] and p["centre_prescripteur"] != p["centre_executant"]],
                          lambda p: f"{p['centre_prescripteur']} > {p['centre_executant']}")[:20]
    r.tableau("Dépenses prescrites par un centre et exécutées par un autre (20 premiers couples)", ["Prescripteur > exécutant", "Dépenses", "%", "Actes", "Coût moyen / acte"],
              [(g["Libelle"], _f(g["Depenses"]), _p(g["Part"]), _f(g["Actes"]), _f(g["CoutParActe"])) for g in couples], droite=(1, 2, 3, 4), taille=7.5)

    r.titre("III. ANALYSE CIBLÉE DES ENTREPRISES À RISQUE", 1)
    r.titre("III.1. Sélection des entreprises à risque", 2)
    r.para("Critères : coût moyen par acte supérieur de plus de 30 % à la moyenne du portefeuille ; plus de 10 actes par bénéficiaire ; score égal ou supérieur à 1 (entreprise critique). "
           "Le score est la moyenne des rapports à la moyenne du portefeuille du coût par bénéficiaire, du nombre d'actes par bénéficiaire et du coût par acte "
           "(formule proposée, à valider).")
    risque, _p_ = entreprises_a_risque(prestations, effectif, au)
    r.tableau("Indicateurs et score par entreprise", ["Entreprise", "Bénéf.", "Actes", "Dépenses", "Âge moyen", "Coût / bénéf.", "Actes / bénéf.", "Coût / acte", "Alerte", "Score"],
              [(l["Police"], _f(l["Beneficiaires"]), _f(l["Actes"]), _f(l["Depenses"]), _f(l["AgeMoyen"]), _f(l["CoutParBeneficiaire"]),
                "-" if l["ActesParBeneficiaire"] is None else f"{l['ActesParBeneficiaire']:.1f}".replace(".", ","), _f(l["CoutParActe"]), ", ".join(l["Alertes"]),
                f"{l['Score']:.2f}".replace(".", ",")) for l in risque], droite=(1, 2, 3, 4, 5, 6, 7, 9), taille=7)
    a_risque = [l["Police"] for l in risque if l["Alertes"]][:FICHES_MAX]
    r.titre("III.2. Analyse des entreprises à risque", 2)
    if not a_risque:
        r.para("Aucune entreprise ne répond aux critères sur la période.", italique=True)
    for police in a_risque:
        _fiche(r, police, prestations, effectif, au)

    if bord["CotisationsImportees"]:
        t = bord["Totaux"]
        r.titre(f"IV. CONTRÔLE DE GESTION {exercice}", 1)
        r.para("Provision pour paiement des dépenses de santé (état des cotisations) face à la consommation des relevés de l'exercice.")
        r.tableau("Pilotage global", ["Indicateur", "Montant"], [
            ("Primes HT", _f(t["PrimeHt"])), ("Cotisations santé pure", _f(t["CotisationPure"])), ("Honoraires du gestionnaire", _f(t["Honoraires"])),
            ("Commissions", _f(t["Commissions"])), ("Apporteurs d'affaires", _f(t["Apporteurs"])), ("Provisions pour paiement des dépenses", _f(t["Provision"])),
            ("Consommation", _f(t["Consommation"])), ("Reste sur les provisions", _f(t["Reste"])), ("Taux de consommation des provisions", _p(t["Taux"])),
            ("Entreprises", _f(t["Entreprises"])),
        ], droite=(1,))
        r.tableau("Contrôle de gestion par entreprise", ["Entreprise", "Police du gestionnaire", "Provision", "Consommation", "Reste", "Taux", "Situation"],
                  [(l["Entreprise"] or "-", l["Police"] or "-", _f(l["Provision"]), _f(l["Consommation"]), _f(l["Reste"]), _p(l["Taux"]), l["Situation"])
                   for l in bord["Controle"]], droite=(2, 3, 4, 5), taille=7)
    return r.octets(), f"RAPPORT CONSOMMATIONS SANTE {exercice} du {du:%d-%m-%Y} au {au:%d-%m-%Y}.docx", {"Exercice": exercice, "Du": du, "Au": au,
                                                                                                       "Prestations": len(prestations)}


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def vue_rapport(request):
    """GET /api/consommations/rapport/?exercice=&du=&au=&garant= : le rapport Word, seul export du suivi des consommations."""
    try:
        contenu, nom, resume = produire(request.query_params)
    except ErreurConsommation:
        return _reponse(produire, request.query_params)
    journaliser(request=request, module="consommations", action="consommations.rapport", objet_type="rapport_consommations", objet_id=str(resume["Exercice"]),
                description=f"Export du rapport des consommations santé du {resume['Du']:%d/%m/%Y} au {resume['Au']:%d/%m/%Y} ({resume['Prestations']} prestations).")
    reponse = HttpResponse(contenu, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    reponse["Content-Disposition"] = f'attachment; filename="{nom}"'
    return reponse
