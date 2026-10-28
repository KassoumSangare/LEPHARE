"""
Tableau de bord de la direction (/admin/dashboard) : production, encaissements et résultats du cabinet sur un
exercice, comparés à la même période de l'exercice précédent, par mois, par branche et par compagnie, et alertes de
conformité à la date du jour. Chiffres réels de la base, mêmes règles que le cockpit, la caisse, les reversements et
les commissions.

GET /api/tableau-de-bord/?exercice=2026 (droit reporting.view)
"""
from datetime import date, timedelta

from django.db import connection
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from autorisations.models import DemandeAutorisation, StatutDemande
from autorisations.rbac import a_le_droit
from institutionnel.models import ConventionAssureur

from . import views_finance
from .views_cockpit import CONTRAT_VALIDE, _franc, _lignes, _meme_jour, _une
from .views_reprise import AUTHENTIFICATION

DROIT = "reporting.view"
EXERCICES_PROPOSES = 6
COMPAGNIES_AFFICHEES = 8
# Délai de reversement des primes encaissées quand la convention de la compagnie n'en fixe pas
DELAI_REVERSEMENT_JOURS = 30
# Prime non soldée … jours après l'effet ; commissions réclamées sans règlement depuis plus de … jours
IMPAYE_APRES_JOURS = 30
RECLAMATION_ANCIENNE_JOURS = 60

# Catégorie des états CIMA de chaque produit (correspondance de fn_etat_cima_source d'URANUS)
CATEGORIES_CIMA = {
    1: "Automobile", 2: "Assurance des personnes", 3: "Assurance des personnes", 4: "Incendie et multirisques",
    5: "Assurance des personnes", 6: "Transport", 7: "Incendie et multirisques", 8: "Responsabilité civile",
    9: "Autres dommages aux biens", 10: "Vie",
}

# Montant d'une ligne d'encaissement : décaissement de prime mal affectée compté en négatif, comme la caisse
MONTANT_ENCAISSE = ("CASE WHEN UPPER(TRIM(COALESCE(m.abregereglement, ''))) = ANY(%(decaissements)s) "
                    "THEN -de.montant_encaissement ELSE de.montant_encaissement END")


def _taux(part, total):
    return round(float(part) * 100 / float(total), 1) if total else None


def _exercices(cursor, annee_courante):
    annees = [l["annee"] for l in _lignes(cursor, """
        SELECT DISTINCT EXTRACT(YEAR FROM dateemission)::int AS annee FROM stdcontrat
        WHERE dateemission IS NOT NULL AND EXTRACT(YEAR FROM dateemission) <= %s ORDER BY 1 DESC LIMIT %s
    """, [annee_courante, EXERCICES_PROPOSES])]
    return sorted(set(annees) | {annee_courante}, reverse=True)[:EXERCICES_PROPOSES]


def _production(cursor, p):
    t = _une(cursor, f"""
        SELECT COUNT(*) FILTER (WHERE x.n) AS nombre, COALESCE(SUM(c.primettc) FILTER (WHERE x.n), 0) AS ttc,
               COALESCE(SUM(c.primenette) FILTER (WHERE x.n), 0) AS pn,
               COALESCE(SUM(c.commissionintermediaire) FILTER (WHERE x.n), 0) AS commission,
               COUNT(*) FILTER (WHERE x.n AND a.codeavenant = 'AFN') AS afn,
               COUNT(*) FILTER (WHERE x.n AND a.codeavenant = 'REN') AS ren,
               COUNT(*) FILTER (WHERE x.n1) AS nombre_n1, COALESCE(SUM(c.primettc) FILTER (WHERE x.n1), 0) AS ttc_n1,
               COALESCE(SUM(c.commissionintermediaire) FILTER (WHERE x.n1), 0) AS commission_n1
        FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
        CROSS JOIN LATERAL (SELECT c.dateemission::date BETWEEN %(debut)s AND %(au)s AS n,
                                   c.dateemission::date BETWEEN %(debut_n1)s AND %(au_n1)s AS n1) x
        WHERE {CONTRAT_VALIDE} AND c.dateemission::date BETWEEN %(debut_n1)s AND %(au)s
    """, p)
    return {
        "Nombre": t["nombre"], "PrimeTtc": _franc(t["ttc"]), "PrimeNette": _franc(t["pn"]),
        "Commission": _franc(t["commission"]), "AffairesNouvelles": t["afn"], "Renouvellements": t["ren"],
        "Avenants": t["nombre"] - t["afn"] - t["ren"],
        "Precedent": {"Nombre": t["nombre_n1"], "PrimeTtc": _franc(t["ttc_n1"]), "Commission": _franc(t["commission_n1"])},
    }


def _par_mois(cursor, p):
    """Primes TTC émises par mois (exercice et précédent) et encaissements par mois de l'exercice."""
    emis = _lignes(cursor, f"""
        SELECT EXTRACT(YEAR FROM c.dateemission)::int AS annee, EXTRACT(MONTH FROM c.dateemission)::int AS mois,
               SUM(c.primettc) AS ttc
        FROM stdcontrat c WHERE {CONTRAT_VALIDE} AND c.dateemission::date BETWEEN %(debut_n1)s AND %(au)s
        GROUP BY 1, 2
    """, p)
    encaisse = _lignes(cursor, f"""
        SELECT EXTRACT(MONTH FROM e.dateencaissement)::int AS mois, SUM({MONTANT_ENCAISSE}) AS montant
        FROM stddetailencaissement de
        JOIN stdencaissement e ON e.idencaissement = de.idencaissement
        LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
        WHERE NOT COALESCE(e.piece_annulee, FALSE) AND e.dateencaissement::date BETWEEN %(debut)s AND %(au)s
        GROUP BY 1
    """, p)
    annee = p["debut"].year
    ttc = {(l["annee"], l["mois"]): l["ttc"] for l in emis}
    enc = {l["mois"]: l["montant"] for l in encaisse}
    return [{
        "Mois": m,
        # Mois à venir de l'exercice en cours : pas de chiffre (et non zéro)
        "PrimeTtc": _franc(ttc.get((annee, m))) if m <= p["au"].month else None,
        "PrimeTtcPrecedent": _franc(ttc.get((annee - 1, m))),
        "Encaisse": _franc(enc.get(m)) if m <= p["au"].month else None,
    } for m in range(1, 13)]


def _par_branche(cursor, p):
    production = _lignes(cursor, f"""
        SELECT c.idproduit, COUNT(*) AS nombre, SUM(c.primettc) AS ttc, SUM(c.primenette) AS pn,
               SUM(c.commissionintermediaire) AS commission
        FROM stdcontrat c WHERE {CONTRAT_VALIDE} AND c.dateemission::date BETWEEN %(debut)s AND %(au)s
        GROUP BY 1
    """, p)
    # Encaissements saisis sur l'exercice : primes de l'exercice et des exercices antérieurs
    encaissements = _lignes(cursor, f"""
        SELECT q.idproduit, (q.dateemission::date >= %(debut)s) AS exercice, SUM({MONTANT_ENCAISSE}) AS montant
        FROM stddetailencaissement de
        JOIN stdencaissement e ON e.idencaissement = de.idencaissement
        LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
        LEFT JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
        WHERE NOT COALESCE(e.piece_annulee, FALSE) AND e.dateencaissement::date BETWEEN %(debut)s AND %(au)s
        GROUP BY 1, 2
    """, p)
    # Recouvrement des primes émises sur l'exercice : quittances des contrats, encaissé à ce jour
    recouvrement = _lignes(cursor, f"""
        SELECT q.idproduit, COUNT(*) FILTER (WHERE q.primettc - COALESCE(q.mt_encaisse, 0) > 0) AS impayees,
               SUM(q.primettc) AS ttc, SUM(LEAST(GREATEST(COALESCE(q.mt_encaisse, 0), 0), q.primettc)) AS encaisse,
               SUM(GREATEST(q.primettc - COALESCE(q.mt_encaisse, 0), 0)) AS reste
        FROM stdquittance q
        WHERE q.primettc > 0 AND q.idquittance IN (
            SELECT c.idquittance FROM stdcontrat c
            WHERE {CONTRAT_VALIDE} AND c.dateemission::date BETWEEN %(debut)s AND %(au)s)
        GROUP BY 1
    """, p)
    # Commissions perçues : règlements des compagnies datés de l'exercice, et affaires antérieures soldées
    percues = _lignes(cursor, """
        SELECT q.idproduit, SUM(dp.montant_commission_paye) AS montant
        FROM std_detail_paiement_commission dp
        JOIN std_paiement_commission pc ON pc.id = dp.paiement_id
        JOIN stddetailreversement d ON d.iddetailreversement = dp.detail_reversement_id
        JOIN stddetailencaissement de ON de.iddetailencaissement = d.iddetailencaissement
        JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
        WHERE NOT dp.est_annule AND pc.date_paiement::date BETWEEN %(debut)s AND %(au)s
        GROUP BY 1
    """, p)
    reprises = _lignes(cursor, f"""
        SELECT c.idproduit, SUM(c.commissionintermediaire) AS montant
        FROM lephare_reprise r JOIN stdcontrat c ON c.idcontrat = r.idcontrat
        WHERE r.commission_percue AND {CONTRAT_VALIDE} AND c.dateemission::date BETWEEN %(debut)s AND %(au)s
        GROUP BY 1
    """, p)
    produits = {l["idproduit"]: l["libelleproduit"] for l in _lignes(cursor, "SELECT idproduit, libelleproduit FROM stdproduit")}

    branches = {}

    def branche(id_produit):
        return branches.setdefault(id_produit, {
            "IdProduit": id_produit,
            "Branche": views_finance._branche(id_produit, produits.get(id_produit)) if id_produit else "Sans branche",
            "CategorieCima": CATEGORIES_CIMA.get(id_produit, "Autres"),
            "Nombre": 0, "PrimeTtc": 0.0, "PrimeNette": 0.0, "Commission": 0.0, "EncaisseExercice": 0.0,
            "EncaisseAnterieur": 0.0, "PrimeEmiseQuittancee": 0.0, "EncaisseSurEmissions": 0.0, "ResteAEncaisser": 0.0,
            "QuittancesImpayees": 0, "CommissionPercue": 0.0, "CommissionReprise": 0.0,
        })

    for l in production:
        b = branche(l["idproduit"])
        b.update(Nombre=l["nombre"], PrimeTtc=float(l["ttc"] or 0), PrimeNette=float(l["pn"] or 0),
                 Commission=float(l["commission"] or 0))
    for l in encaissements:
        b = branche(l["idproduit"])
        b["EncaisseExercice" if l["exercice"] else "EncaisseAnterieur"] += float(l["montant"] or 0)
    for l in recouvrement:
        b = branche(l["idproduit"])
        b.update(PrimeEmiseQuittancee=float(l["ttc"] or 0), EncaisseSurEmissions=float(l["encaisse"] or 0),
                 ResteAEncaisser=float(l["reste"] or 0), QuittancesImpayees=l["impayees"])
    for l in percues:
        branche(l["idproduit"])["CommissionPercue"] += float(l["montant"] or 0)
    for l in reprises:
        branche(l["idproduit"])["CommissionReprise"] += float(l["montant"] or 0)

    resultat = []
    for b in sorted(branches.values(), key=lambda b: (-b["PrimeTtc"], b["Branche"])):
        ligne = {k: (_franc(v) if isinstance(v, float) else v) for k, v in b.items()}
        ligne["TauxRecouvrement"] = _taux(b["EncaisseSurEmissions"], b["PrimeEmiseQuittancee"])
        ligne["TauxCommission"] = _taux(b["Commission"], b["PrimeNette"])
        resultat.append(ligne)
    return resultat


def _par_compagnie(cursor, p):
    lignes = _lignes(cursor, f"""
        SELECT c.idcompagnie, COALESCE(TRIM(co.raisonsociale), 'Compagnie non renseignée') AS compagnie, COUNT(*) AS nombre,
               SUM(c.primettc) AS ttc, SUM(c.commissionintermediaire) AS commission
        FROM stdcontrat c LEFT JOIN stdcompagnie co ON co.idcompagnie = c.idcompagnie
        WHERE {CONTRAT_VALIDE} AND c.dateemission::date BETWEEN %(debut)s AND %(au)s
        GROUP BY 1, 2 ORDER BY 4 DESC NULLS LAST
    """, p)
    resultat = [{"IdCompagnie": l["idcompagnie"], "Compagnie": l["compagnie"], "Nombre": l["nombre"],
                 "PrimeTtc": _franc(l["ttc"]), "Commission": _franc(l["commission"])} for l in lignes]
    if len(resultat) > COMPAGNIES_AFFICHEES:
        autres = resultat[COMPAGNIES_AFFICHEES - 1:]
        resultat = resultat[:COMPAGNIES_AFFICHEES - 1] + [{
            "IdCompagnie": None, "Compagnie": f"Autres compagnies ({len(autres)})", "Nombre": sum(a["Nombre"] for a in autres),
            "PrimeTtc": sum(a["PrimeTtc"] for a in autres), "Commission": sum(a["Commission"] for a in autres),
        }]
    return resultat


def _situation(cursor, jour):
    """Situation au jour, quel que soit l'exercice affiché : reversements, commissions, chèques, impayés, dérogations."""
    # Primes encaissées à reverser, au-delà du délai de la convention de la compagnie (30 jours sinon)
    delais = {c.idcompagnie: c.delai_reversement_jours for c in ConventionAssureur.objects.exclude(idcompagnie=None)
              if c.delai_reversement_jours}
    a_reverser = views_finance.encaissements_a_reverser()
    en_retard = []
    for l in a_reverser:
        delai = delais.get(l["IdCompagnie"]) or DELAI_REVERSEMENT_JOURS
        if l["DateEncaissement"] and (jour - date.fromisoformat(l["DateEncaissement"])).days > delai:
            en_retard.append(l)
    plus_ancien = min((l["DateEncaissement"] for l in a_reverser if l["DateEncaissement"]), default=None)

    recap = views_finance.recapitulatif_commissions(jour=jour)
    total = recap["Total"]
    anciennes = [r for r in recap["Reclamations"] if (r["Anciennete"] or 0) > RECLAMATION_ANCIENNE_JOURS]

    cheques = _une(cursor, """
        SELECT COUNT(*) AS n, COALESCE(SUM(montantinitial), 0) AS m FROM stdcheque
        WHERE statut = 'A_DEPOSER' AND dateecheance < %s
    """, [jour])
    # Polices en vigueur dont la prime n'est pas soldée … jours après l'effet (la garantie suit le paiement de la prime)
    impayes = _une(cursor, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(q.primettc - COALESCE(q.mt_encaisse, 0)), 0) AS m
        FROM stdquittance q
        WHERE q.primettc - COALESCE(q.mt_encaisse, 0) > 0 AND q.dateeffet::date < %s AND q.dateexpiration::date >= %s
          AND EXISTS (SELECT 1 FROM stdcontrat c WHERE c.idquittance = q.idquittance AND c.numeropolice = q.numeropolice
                        AND {CONTRAT_VALIDE})
    """, [jour - timedelta(days=IMPAYE_APRES_JOURS), jour])
    derogations = DemandeAutorisation.objects.filter(statut=StatutDemande.EN_ATTENTE).count()

    return {
        "Reversements": {
            "Nombre": len(a_reverser), "Montant": _franc(sum(l["ResteAReverser"] for l in a_reverser)),
            "Compagnies": len({l["IdCompagnie"] for l in a_reverser}), "PlusAncien": plus_ancien,
            "EnRetard": {"Nombre": len(en_retard), "Montant": _franc(sum(l["ResteAReverser"] for l in en_retard)),
                         "Compagnies": len({l["IdCompagnie"] for l in en_retard})},
            "DelaiJours": DELAI_REVERSEMENT_JOURS,
        },
        "Commissions": {
            "AReclamer": _franc(total["EnAttenteAReclamer"]), "Reclamees": _franc(total["EnAttenteReclamee"]),
            "Payees": _franc(total["CommissionPayee"]), "TauxRecouvrement": total["TauxRecouvrement"],
            "ReclamationsAnciennes": {"Nombre": len(anciennes), "Montant": _franc(sum(r["Reste"] for r in anciennes))},
        },
        "ChequesEchus": {"Nombre": cheques["n"], "Montant": _franc(cheques["m"])},
        "Impayes": {"Nombre": impayes["n"], "Montant": _franc(impayes["m"]), "ApresJours": IMPAYE_APRES_JOURS},
        "DerogationsEnAttente": derogations,
    }


def _alertes(s):
    """Points de conformité à traiter, les plus urgents d'abord (seulement ceux qui comptent au moins un élément)."""
    r, c = s["Reversements"], s["Commissions"]
    alertes = []
    if r["EnRetard"]["Nombre"]:
        alertes.append({
            "Code": "reversements_retard", "Ton": "critique", "Vers": "/admin/remittances", "Droit": "reversements.view",
            "Libelle": f"Primes encaissées non reversées au-delà du délai de la convention ({r['DelaiJours']} jours sinon)",
            "Nombre": r["EnRetard"]["Nombre"], "Montant": r["EnRetard"]["Montant"],
        })
    if s["ChequesEchus"]["Nombre"]:
        alertes.append({
            "Code": "cheques_echus", "Ton": "critique", "Vers": "/user/cheques", "Droit": "encaissements.view",
            "Libelle": "Chèques arrivés à échéance et pas encore déposés en banque",
            "Nombre": s["ChequesEchus"]["Nombre"], "Montant": s["ChequesEchus"]["Montant"],
        })
    if s["Impayes"]["Nombre"]:
        alertes.append({
            "Code": "impayes", "Ton": "attention", "Vers": "/user/cash", "Droit": "encaissements.view",
            "Libelle": f"Polices en vigueur dont la prime n'est pas soldée {s['Impayes']['ApresJours']} jours après l'effet",
            "Nombre": s["Impayes"]["Nombre"], "Montant": s["Impayes"]["Montant"],
        })
    if c["ReclamationsAnciennes"]["Nombre"]:
        alertes.append({
            "Code": "reclamations_anciennes", "Ton": "attention", "Vers": "/admin/commissions", "Droit": "commissions.view",
            "Libelle": f"Bordereaux de commissions réclamés sans règlement depuis plus de {RECLAMATION_ANCIENNE_JOURS} jours",
            "Nombre": c["ReclamationsAnciennes"]["Nombre"], "Montant": c["ReclamationsAnciennes"]["Montant"],
        })
    if s["DerogationsEnAttente"]:
        alertes.append({
            "Code": "derogations", "Ton": "attention", "Vers": "/admin/approvals", "Droit": "approbations.view",
            "Libelle": "Demandes de dérogation en attente de décision", "Nombre": s["DerogationsEnAttente"], "Montant": None,
        })
    if c["AReclamer"]:
        alertes.append({
            "Code": "commissions_a_reclamer", "Ton": "info", "Vers": "/admin/commissions", "Droit": "commissions.view",
            "Libelle": "Commissions des primes reversées pas encore réclamées aux compagnies", "Nombre": None,
            "Montant": c["AReclamer"],
        })
    return alertes


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def tableau_de_bord(request):
    if not a_le_droit(request.user, DROIT):
        return Response({"detail": "Droit « Consulter les états » requis."}, status=status.HTTP_403_FORBIDDEN)
    jour = timezone.localdate()
    try:
        exercice = int(request.query_params.get("exercice") or jour.year)
    except (TypeError, ValueError):
        return Response({"detail": "Exercice invalide."}, status=status.HTTP_400_BAD_REQUEST)
    if not 2000 <= exercice <= jour.year:
        return Response({"detail": f"Exercice hors limites : de 2000 à {jour.year}."}, status=status.HTTP_400_BAD_REQUEST)

    # Exercice en cours : arrêté au jour, comparé à la même date de l'an dernier ; exercice clos : année entière
    au = jour if exercice == jour.year else date(exercice, 12, 31)
    p = {"debut": date(exercice, 1, 1), "au": au, "debut_n1": date(exercice - 1, 1, 1), "au_n1": _meme_jour(au, exercice - 1),
         "decaissements": sorted(views_finance.MODES_DECAISSEMENT)}
    with connection.cursor() as cursor:
        production = _production(cursor, p)
        branches = _par_branche(cursor, p)
        resultat = {
            "Jour": jour.isoformat(), "Exercice": exercice, "Exercices": _exercices(cursor, jour.year),
            "Du": p["debut"].isoformat(), "Au": au.isoformat(), "AuPrecedent": p["au_n1"].isoformat(),
            "EnCours": exercice == jour.year,
            "Production": production,
            "ParMois": _par_mois(cursor, p),
            "ParBranche": branches,
            "ParCompagnie": _par_compagnie(cursor, p),
        }
        situation = _situation(cursor, jour)

    somme = lambda cle: sum(b[cle] for b in branches)  # noqa: E731
    emis_quittance = somme("PrimeEmiseQuittancee")
    resultat["Encaissements"] = {
        "Total": somme("EncaisseExercice") + somme("EncaisseAnterieur"),
        "SurExercice": somme("EncaisseExercice"), "SurAnterieurs": somme("EncaisseAnterieur"),
        "PrimeEmise": emis_quittance, "EncaisseSurEmissions": somme("EncaisseSurEmissions"),
        "ResteAEncaisser": somme("ResteAEncaisser"), "QuittancesImpayees": somme("QuittancesImpayees"),
        "TauxRecouvrement": _taux(somme("EncaisseSurEmissions"), emis_quittance),
    }
    resultat["Resultats"] = {
        "CommissionsAcquises": production["Commission"],
        "CommissionsAcquisesPrecedent": production["Precedent"]["Commission"],
        "TauxMoyen": _taux(production["Commission"], production["PrimeNette"]),
        "CommissionsPercues": somme("CommissionPercue") + somme("CommissionReprise"),
        "PercuesReglements": somme("CommissionPercue"), "PercuesReprises": somme("CommissionReprise"),
    }
    resultat["Situation"] = situation
    resultat["Alertes"] = _alertes(situation)
    return Response(resultat)
