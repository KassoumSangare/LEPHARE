"""
Chiffre d'affaires du cabinet (demande du 2026-11-12 : « Oreole est un courtier d'assurances et son chiffre d'affaires, ce
sont les commissions qu'il perçoit »). Les primes émises reviennent aux compagnies ; le revenu du cabinet, ce sont ses
commissions et ses accessoires. Lu par le cockpit opérationnel (views_cockpit) et le tableau de bord de la direction
(views_tableau_de_bord).

Synonymes (consigne du 2026-11-16, documents d'OREOLE) : taux de commission OREOLE ASSURANCES, taux de commission COURTIER,
commission acquise, générée, réelle, prévisionnelle, à percevoir, Comm. Interm., frais de courtage, frais courtiers (Oreole
Santé, « chargement pour sinistres à payer »), accessoire courtier, honoraires de courtier ou du cabinet (« honoraires
OREOLE » d'Oreole Santé) désignent tous ce revenu : ils forment le chiffre d'affaires. Ne pas confondre avec les honoraires du
gestionnaire (MCI, VITALIS), les frais de gestion (ADEC, MINENE) ni la rétrocession aux apporteurs, qui ne sont pas au cabinet.

- Acquis : commission du contrat (stdcontrat.commissionintermediaire) + accessoires du cabinet
  (stdcontrat.accessoireintermediaire ; en Oreole Santé, frais courtiers gardés par le cabinet) des actes émis sur la
  période (date d'émission), contrats annulés exclus, comme la commission due des reversements (views_finance) ; plus la
  commission du courtier sur les régimes autofinancés RAFAS facturée sur la période (sante/rafas.py).
- Perçu : règlements de commissions des compagnies (date du règlement), honoraires et frais courtiers d'Oreole Santé gardés
  par le cabinet à l'encaissement de la cotisation, qui n'est ni reversée ni réclamée (date de l'encaissement, au prorata du
  montant encaissé), affaires antérieures
  saisies avec leur commission déjà perçue, commission RAFAS réglée (date du règlement).
- En attente (situation au jour) : commissions des primes reversées non encore payées (views_finance) et commission RAFAS
  facturée non réglée.
- Reste à percevoir (demande du 2026-11-24 : le cadre reprend l'écran Reversements aux compagnies) : commission des actes
  émis sur la période pas encore perçue, situation au jour, quittance par quittance, rangée à l'étape où elle attend
  (ETAPES_RESTE) : prime à encaisser, prime encaissée à reverser ou payée en direct à la compagnie (onglet « Quittances
  à reverser », bordereau de reversement de prime ou de réclamation de commission à émettre), bordereau de
  reversement à payer à la compagnie, commission à réclamer, réclamée non payée, prime encaissée avant LE PHARE (reprise
  d'URANUS) ; plus la commission RAFAS de la période non réglée. Chiffre d'affaires = déjà perçu sur ces actes + reste à
  percevoir. Les actes des exercices antérieurs dont la prime est passée par la caisse de LE PHARE et dont la commission
  n'est pas perçue sont comptés à part, hors total.
- Apporteurs : commissions dues aux apporteurs d'affaires sur les quittances émises de la période, d'après le dernier
  calcul du module Apporteurs (production/apporteurs.py).

Période p : {"debut", "au", "debut_n1", "au_n1"} (exercice arrêté au jour « au », même date de l'exercice précédent).
"""
import math
from datetime import date

from . import views_finance

CONTRAT_VALIDE = "COALESCE(c.idcontratannulation, 0) = 0"
# Montant valide (NaN : devis importé d'un fichier à cellules vides, compté pour zéro)
_VALIDE = "COALESCE(NULLIF({}, 'NaN'), 0)"
# Chiffre d'affaires d'un contrat c : commission + accessoires du cabinet
SQL_CHIFFRE_AFFAIRES = f"({_VALIDE.format('c.commissionintermediaire')} + {_VALIDE.format('c.accessoireintermediaire')})"
# Décaissement de prime mal affectée : compté en négatif, comme la caisse
_MONTANT_ENCAISSE = ("CASE WHEN UPPER(TRIM(COALESCE(m.abregereglement, ''))) = ANY(%(decaissements)s) "
                     "THEN -de.montant_encaissement ELSE de.montant_encaissement END")

SOURCES_PERCU = {
    "Compagnies": "Règlements de commissions des compagnies",
    "FraisCourtiers": "Honoraires et frais courtiers d'Oreole Santé gardés à l'encaissement",
    "Reprises": "Affaires antérieures saisies avec leur commission perçue",
    "Rafas": "Commission RAFAS réglée",
}


def _lignes(cursor, sql, params=None):
    cursor.execute(sql, params or [])
    colonnes = [c[0] for c in cursor.description]
    return [dict(zip(colonnes, ligne)) for ligne in cursor.fetchall()]


def _table(cursor, nom):
    cursor.execute("SELECT to_regclass(%s) IS NOT NULL", [f"public.{nom}"])
    return bool(cursor.fetchone()[0])


def _nombre(valeur):
    nombre = float(valeur or 0)
    return 0.0 if math.isnan(nombre) else nombre


def _franc(valeur):
    return round(_nombre(valeur))


def _taux(part, total):
    return round(float(part) * 100 / float(total), 1) if total else None


def _parametres(p):
    return {**p, "decaissements": sorted(views_finance.MODES_DECAISSEMENT)}


# ------------------------------------------------------------------ lectures
def lire_acquis(cursor, p):
    """Commissions et accessoires des actes émis du 1er janvier de l'exercice précédent au jour, par mois."""
    return _lignes(cursor, f"""
        SELECT EXTRACT(YEAR FROM c.dateemission)::int AS annee, EXTRACT(MONTH FROM c.dateemission)::int AS mois,
               (c.dateemission::date <= %(au_n1)s OR c.dateemission::date >= %(debut)s) AS comparable,
               COUNT(*) AS nombre, SUM({_VALIDE.format('c.commissionintermediaire')}) AS commission,
               SUM({_VALIDE.format('c.accessoireintermediaire')}) AS accessoires, SUM({_VALIDE.format('c.primenette')}) AS pn
        FROM stdcontrat c
        WHERE {CONTRAT_VALIDE} AND c.dateemission::date BETWEEN %(debut_n1)s AND %(au)s
        GROUP BY 1, 2, 3
    """, p)


def lire_percu(cursor, p):
    """Sommes perçues par le cabinet du 1er janvier de l'exercice précédent au jour : (source, idproduit, idcompagnie, jour, montant)."""
    p = _parametres(p)
    lignes = [dict(l, source="Compagnies") for l in _lignes(cursor, """
        SELECT q.idproduit, pc.compagnie_id AS idcompagnie, pc.date_paiement::date AS jour, SUM(dp.montant_commission_paye) AS montant
        FROM std_detail_paiement_commission dp
        JOIN std_paiement_commission pc ON pc.id = dp.paiement_id
        JOIN stddetailreversement d ON d.iddetailreversement = dp.detail_reversement_id
        JOIN stddetailencaissement de ON de.iddetailencaissement = d.iddetailencaissement
        JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
        WHERE NOT dp.est_annule AND pc.date_paiement::date BETWEEN %(debut_n1)s AND %(au)s
        GROUP BY 1, 2, 3
    """, p)]
    if _table(cursor, "lephare_oreole_package"):
        # Oreole Santé, part Santé : gérée sans assureur, ni reversée ni réclamée (consigne du 2026-11-24,
        # views_finance.SQL_EST_OREOLE) ; le cabinet garde ses honoraires (commission du contrat) et ses frais courtiers à
        # l'encaissement : part du cabinet = (honoraires + frais courtiers) / cotisation, au prorata de l'encaissé
        lignes += [dict(l, source="FraisCourtiers") for l in _lignes(cursor, f"""
            SELECT q.idproduit, ct.idcompagnie, e.dateencaissement::date AS jour,
                   SUM(({_MONTANT_ENCAISSE}) * ct.frais / NULLIF(q.primettc, 'NaN')) AS montant
            FROM stddetailencaissement de
            JOIN stdencaissement e ON e.idencaissement = de.idencaissement
            LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
            JOIN stdquittance q ON q.numeroquittance = de.numeroquittance
            JOIN LATERAL (SELECT c.iddevis, c.idcompagnie,
                                 {_VALIDE.format('c.accessoireintermediaire')} + {_VALIDE.format('c.commissionintermediaire')} AS frais
                          FROM stdcontrat c WHERE c.idquittance = q.idquittance ORDER BY c.idcontrat LIMIT 1) ct ON TRUE
            WHERE NOT COALESCE(e.piece_annulee, FALSE) AND e.dateencaissement::date BETWEEN %(debut_n1)s AND %(au)s
              AND NULLIF(q.primettc, 'NaN') > 0 AND ct.frais > 0
              AND EXISTS (SELECT 1 FROM lephare_oreole_package opk WHERE opk.iddevis_sante = ct.iddevis)
            GROUP BY 1, 2, 3
        """, p)]
    if _table(cursor, "lephare_reprise"):
        # Affaire antérieure soldée : commission déjà perçue hors LE PHARE (date de la reprise à défaut, celle de l'émission)
        lignes += [dict(l, source="Reprises") for l in _lignes(cursor, f"""
            SELECT c.idproduit, c.idcompagnie, COALESCE(r.date_commission_percue, c.dateemission::date) AS jour,
                   SUM({SQL_CHIFFRE_AFFAIRES}) AS montant
            FROM lephare_reprise r JOIN stdcontrat c ON c.idcontrat = r.idcontrat
            WHERE r.commission_percue AND {CONTRAT_VALIDE}
              AND COALESCE(r.date_commission_percue, c.dateemission::date) BETWEEN %(debut_n1)s AND %(au)s
            GROUP BY 1, 2, 3
        """, p)]
    return lignes


def lire_rafas(cursor, p):
    """Commission du courtier sur les régimes autofinancés : facturée (date d'émission), réglée (date de règlement), et reste
    non réglé au jour. Rien sans la migration production 0218."""
    if not _table(cursor, "lephare_rafas_honoraire"):
        return {"Lignes": [], "NonReglee": 0.0}
    lignes = _lignes(cursor, """
        SELECT 'emis' AS sens, date_emission AS jour, COUNT(*) AS nombre, SUM(montant) AS montant, SUM(base) AS base
        FROM lephare_rafas_honoraire WHERE beneficiaire = 'COURTIER' AND date_emission BETWEEN %(debut_n1)s AND %(au)s GROUP BY 2
        UNION ALL
        SELECT 'regle', date_paiement, COUNT(*), SUM(montant), 0
        FROM lephare_rafas_honoraire WHERE beneficiaire = 'COURTIER' AND date_paiement BETWEEN %(debut_n1)s AND %(au)s GROUP BY 2
    """, p)
    cursor.execute("""SELECT COALESCE(SUM(montant), 0) FROM lephare_rafas_honoraire
                      WHERE beneficiaire = 'COURTIER' AND date_paiement IS NULL AND date_emission <= %s""", [p["au"]])
    non_reglee = _nombre(cursor.fetchone()[0])
    # Commission facturée sur la période : réglée ou non, situation au jour (reste à percevoir)
    cursor.execute("""
        SELECT COUNT(*) FILTER (WHERE date_paiement IS NULL), COALESCE(SUM(montant) FILTER (WHERE date_paiement IS NULL), 0),
               COALESCE(SUM(montant) FILTER (WHERE date_paiement IS NOT NULL), 0)
        FROM lephare_rafas_honoraire WHERE beneficiaire = 'COURTIER' AND date_emission BETWEEN %(debut)s AND %(au)s
    """, p)
    nombre, montant, reglee = cursor.fetchone()
    return {"Lignes": lignes, "NonReglee": non_reglee,
            "Periode": {"NombreNonReglee": nombre, "NonReglee": _nombre(montant), "Reglee": _nombre(reglee)}}


def lire_apporteurs(cursor, p):
    """Commissions des apporteurs d'affaires sur les quittances émises de la période (payées ou à payer)."""
    if not _table(cursor, "lephare_commission_apporteur"):
        return {"Payees": 0.0, "APayer": 0.0}
    cursor.execute("""
        SELECT COALESCE(SUM(montant) FILTER (WHERE statut = 'PAYEE'), 0), COALESCE(SUM(montant) FILTER (WHERE statut = 'A_PAYER'), 0)
        FROM lephare_commission_apporteur WHERE statut <> 'ANNULEE' AND dateemission BETWEEN %(debut)s AND %(au)s
    """, p)
    payees, a_payer = cursor.fetchone()
    return {"Payees": _nombre(payees), "APayer": _nombre(a_payer)}


def lire_reste(cursor, p):
    """Commission de chaque quittance, situation au jour (reste à percevoir) : actes émis sur la période (exercice) et actes
    antérieurs dont la prime est passée par la caisse de LE PHARE (encaissée depuis le début des reversements, ou reversée).
    Encaissé net (décaissements déduits), reversé (bordereaux non annulés), dont payé à la compagnie (bordereau validé,
    « Direct » compris), commission payée par la compagnie et réclamations en cours : mêmes règles que l'écran des
    reversements et l'état des commissions (views_finance.SQL_COMMISSIONS)."""
    from .views_bordereaux import MODE_A_LA_COMPAGNIE  # import local : views_bordereaux est un gros module d'écrans

    p = {**_parametres(p), "debut_reversements": views_finance.debut_reversements(), "mode_compagnie": MODE_A_LA_COMPAGNIE}
    package_existe = _table(cursor, "lephare_oreole_package")
    oreole = ("EXISTS (SELECT 1 FROM lephare_oreole_package opk WHERE opk.iddevis_sante = c.iddevis)"
              if package_existe else "FALSE")
    # Package Oreole Santé (Santé, IA, AFA) : l'argent reste au cabinet quel que soit le mode (views_bordereaux.SQL_REGLEMENTS)
    package = ("EXISTS (SELECT 1 FROM lephare_oreole_package px WHERE c.iddevis IN (px.iddevis_sante, px.iddevis_ia, px.iddevis_afa))"
               if package_existe else "FALSE")
    reprise = ("EXISTS (SELECT 1 FROM lephare_reprise r WHERE r.idcontrat = c.idcontrat AND r.commission_percue)"
               if _table(cursor, "lephare_reprise") else "FALSE")
    # Lignes de reversement non annulées (pièce et bordereau) de la quittance q
    reversements = """FROM stddetailreversement d
            JOIN stdreversementcompagnie r ON r.idreversement = d.idreversement AND NOT COALESCE(r.pieceannulee, FALSE)
            LEFT JOIN lephare_bordereau_reversement b ON b.idreversement = r.idreversement
            JOIN stddetailencaissement de ON de.iddetailencaissement = d.iddetailencaissement
            WHERE de.numeroquittance = q.numeroquittance AND NOT COALESCE(b.annule, FALSE)"""
    return _lignes(cursor, f"""
        WITH ct AS (
            SELECT c.idquittance, c.dateemission::date >= %(debut)s AS exercice, SUM({SQL_CHIFFRE_AFFAIRES}) AS ca,
                   BOOL_OR({oreole}) AS oreole, BOOL_OR({reprise}) AS reprise_percue, BOOL_OR({package}) AS package
            FROM stdcontrat c
            WHERE {CONTRAT_VALIDE} AND c.dateemission::date <= %(au)s
              AND (c.dateemission::date >= %(debut)s OR c.idquittance IN (
                    SELECT qa.idquittance FROM stdquittance qa
                    JOIN stddetailencaissement de ON de.numeroquittance = qa.numeroquittance
                    JOIN stdencaissement e ON e.idencaissement = de.idencaissement
                    WHERE NOT COALESCE(e.piece_annulee, FALSE)
                      AND (e.dateencaissement::date >= %(debut_reversements)s OR COALESCE(de.montantreglement, 0) > 0)))
            GROUP BY 1, 2
        )
        SELECT ct.idquittance, q.numeroquittance, ct.exercice, ct.ca, ct.oreole, ct.reprise_percue,
               {_VALIDE.format('q.primettc')} AS primettc, COALESCE(enc.montant, 0) AS encaisse,
               COALESCE(enc.lephare, 0) AS encaisse_lephare, COALESCE(enc.direct, 0) AS encaisse_direct,
               COALESCE(rv.montant, 0) AS reverse, COALESCE(rv.paye, 0) AS reverse_paye,
               COALESCE(cm.payee, 0) AS payee, COALESCE(cm.reclamations, '{{}}') AS reclamations
        FROM ct
        LEFT JOIN stdquittance q ON q.idquittance = ct.idquittance
        LEFT JOIN LATERAL (
            SELECT SUM({_MONTANT_ENCAISSE}) AS montant,
                   SUM({_MONTANT_ENCAISSE}) FILTER (WHERE e.dateencaissement::date >= %(debut_reversements)s) AS lephare,
                   -- Règlement du client à l'ordre de la compagnie, ou espèces : transmis en direct, bordereau de
                   -- réclamation de commission (Nature RECLAMATION de l'écran des reversements, views_bordereaux)
                   SUM({_MONTANT_ENCAISSE}) FILTER (WHERE e.dateencaissement::date >= %(debut_reversements)s AND NOT ct.package
                       AND (e.idmodepaiement = %(mode_compagnie)s OR e.ordrereglement = 'COMPAGNIE'
                            OR UPPER(TRIM(COALESCE(m.abregereglement, ''))) = 'ESP')) AS direct
            FROM stddetailencaissement de
            JOIN stdencaissement e ON e.idencaissement = de.idencaissement
            LEFT JOIN stdmodeencaissement m ON m.idmodeencaissement = e.idmodepaiement
            WHERE de.numeroquittance = q.numeroquittance AND NOT COALESCE(e.piece_annulee, FALSE)) enc ON TRUE
        LEFT JOIN LATERAL (
            SELECT SUM(d.montantreverse) AS montant, SUM(d.montantreverse) FILTER (WHERE r.valide) AS paye
            {reversements}) rv ON TRUE
        LEFT JOIN LATERAL (
            SELECT SUM((SELECT COALESCE(SUM(dp.montant_commission_paye), 0) FROM std_detail_paiement_commission dp
                        WHERE dp.detail_reversement_id = d.iddetailreversement AND NOT dp.est_annule)) AS payee,
                   ARRAY_REMOVE(ARRAY_AGG(DISTINCT (
                       SELECT MAX(x.id) FROM std_detail_reclamation_commission dx
                       JOIN std_reclamation_commission x ON x.id = dx.reclamation_id
                       WHERE dx.detail_reversement_id = d.iddetailreversement AND x.statut <> 'ANNULEE')), NULL) AS reclamations
            {reversements} AND r.valide) cm ON TRUE
    """, p)


# ------------------------------------------------------------------ synthèse (sans base de données)
# Étapes du reste à percevoir, dans l'ordre du parcours de la prime (écran Reversements aux compagnies) : encaissement auprès du
# client, reversement à la compagnie (bordereau payé par le cabinet), réclamation de la commission, paiement par la compagnie ;
# en dernier, primes encaissées avant LE PHARE (reprise d'URANUS, avant views_finance.debut_reversements) et jamais reversées
# depuis : leur reversement et leur commission se suivaient dans URANUS, l'écran des reversements ne les propose pas
# Onglet « Quittances à reverser » : AReverser (prime encaissée par le cabinet, bordereau de reversement de prime à émettre) et
# ADirect (prime payée directement à la compagnie, bordereau de réclamation de commission « Direct » à émettre)
ETAPES_RESTE = ("AEncaisser", "AReverser", "ADirect", "BordereauxAPayer", "AReclamer", "Reclamees", "EncaisseesUranus")
# Étapes des actes antérieurs comptées à part (prime encaissée dans LE PHARE, suivie par l'écran des reversements)
ETAPES_ANTERIEURS = ("AReverser", "ADirect", "BordereauxAPayer", "AReclamer", "Reclamees")


def _etape(l):
    """(étape, déjà perçu, reste) de la commission d'une quittance lue par lire_reste."""
    ca = _nombre(l["ca"])
    if l["oreole"]:
        # Oreole Santé, part Santé : honoraires et frais courtiers gardés à l'encaissement, au prorata (lire_percu) ; le reste
        # attend l'encaissement de la cotisation
        ttc = _nombre(l["primettc"])
        part = min(max(_nombre(l["encaisse"]) / ttc, 0.0), 1.0) if ttc > 0 else 0.0
        return "AEncaisser", ca * part, ca * (1 - part)
    if l["reprise_percue"]:
        return None, ca, 0.0
    if _nombre(l["reverse_paye"]) > 0:
        # Prime payée à la compagnie (en tout ou en partie) : commission due en entier (views_finance.COMMISSION_DUE)
        percu = max(min(_nombre(l["payee"]), ca), 0.0)
        return ("Reclamees" if l["reclamations"] else "AReclamer"), percu, ca - percu
    if _nombre(l["reverse"]) > 0:
        return "BordereauxAPayer", 0.0, ca
    if _nombre(l["encaisse"]) > 0:
        lephare = _nombre(l["encaisse_lephare"])
        if lephare <= 0:
            return "EncaisseesUranus", 0.0, ca
        # Tout l'encaissé de LE PHARE est allé à la compagnie : réclamation directe ; sinon (ou en partie) reversement de prime
        return ("ADirect" if _nombre(l.get("encaisse_direct")) >= lephare - 0.5 else "AReverser"), 0.0, ca
    return "AEncaisser", 0.0, ca


def ventiler_reste(lignes, rafas=None):
    """Reste à percevoir de la période étape par étape (lignes de lire_reste), déjà perçu sur ses actes, commission RAFAS
    facturée non réglée, et actes antérieurs encore suivis par l'écran des reversements (prime encaissée), hors total."""
    etapes = {e: {"Nombre": 0, "Montant": 0.0} for e in ETAPES_RESTE}
    anterieurs = {e: {"Nombre": 0, "Montant": 0.0} for e in ETAPES_ANTERIEURS}
    reclamations, deja_percu = set(), 0.0
    for l in lignes:
        etape, percu, reste = _etape(l)
        if l["exercice"]:
            deja_percu += percu
            if etape:
                etapes[etape]["Montant"] += reste
                etapes[etape]["Nombre"] += int(abs(reste) >= 0.5)
                if etape == "Reclamees" and reste >= 0.5:
                    reclamations.update(l["reclamations"])
        elif etape in anterieurs and reste >= 0.5:
            anterieurs[etape]["Montant"] += reste
            anterieurs[etape]["Nombre"] += 1
    rafas = (rafas or {}).get("Periode") or {}
    resultat = {e: {"Nombre": v["Nombre"], "Montant": _franc(v["Montant"])} for e, v in etapes.items()}
    resultat["Reclamees"]["Bordereaux"] = len(reclamations)
    resultat["Rafas"] = {"Nombre": int(rafas.get("NombreNonReglee") or 0), "Montant": _franc(rafas.get("NonReglee"))}
    anterieurs = {e: {"Nombre": v["Nombre"], "Montant": _franc(v["Montant"])} for e, v in anterieurs.items()}
    return {
        # Somme des lignes affichées : chiffre d'affaires de la période = déjà perçu + total
        "Total": sum(v["Montant"] for v in resultat.values()),
        "DejaPercu": _franc(deja_percu + _nombre(rafas.get("Reglee"))),
        **resultat,
        "Anterieurs": {"Nombre": sum(v["Nombre"] for v in anterieurs.values()),
                       "Montant": sum(v["Montant"] for v in anterieurs.values()), **anterieurs},
    }


def _jour(valeur):
    return valeur if isinstance(valeur, date) else date.fromisoformat(str(valeur)[:10])


def assembler(p, acquis, percu, rafas, apporteurs, en_attente=None, reste=None):
    """Chiffre d'affaires de la période, comparé au même temps de l'exercice précédent, par mois, et perçu par branche et
    par compagnie. en_attente : commissions des primes reversées non payées (AReclamer, Reclamees), situation au jour ;
    reste : lignes de lire_reste, ventilées dans « ResteAPercevoir » (absent sans elles)."""
    annee, debut, au, au_n1 = p["debut"].year, p["debut"], p["au"], p["au_n1"]
    mois = {m: {"Mois": m, "Acquis": 0.0, "AcquisPrecedent": 0.0, "Percu": 0.0} for m in range(1, 13)}
    t = {"Commissions": 0.0, "Accessoires": 0.0, "Rafas": 0.0, "PrimeNette": 0.0, "Nombre": 0, "Precedent": 0.0}

    for l in acquis:
        ca = _nombre(l["commission"]) + _nombre(l["accessoires"])
        if l["annee"] == annee:
            t["Commissions"] += _nombre(l["commission"])
            t["Accessoires"] += _nombre(l["accessoires"])
            t["PrimeNette"] += _nombre(l["pn"])
            t["Nombre"] += l["nombre"]
            mois[l["mois"]]["Acquis"] += ca
        else:
            mois[l["mois"]]["AcquisPrecedent"] += ca
            if l["comparable"]:
                t["Precedent"] += ca

    percu_sources = {cle: 0.0 for cle in SOURCES_PERCU}
    percu_n1, par_produit, par_compagnie = 0.0, {}, {}

    def compter_percu(source, jour, montant, id_produit=None, id_compagnie=None):
        nonlocal percu_n1
        if debut <= jour <= au:
            percu_sources[source] += montant
            mois[jour.month]["Percu"] += montant
            if source != "Rafas":
                par_produit[id_produit] = par_produit.get(id_produit, 0.0) + montant
                par_compagnie[id_compagnie] = par_compagnie.get(id_compagnie, 0.0) + montant
        elif jour <= au_n1:
            percu_n1 += montant

    for l in percu:
        compter_percu(l["source"], _jour(l["jour"]), _nombre(l["montant"]), l["idproduit"], l["idcompagnie"])

    rafas_nombre = rafas_base = 0.0
    for l in rafas["Lignes"]:
        jour, montant = _jour(l["jour"]), _nombre(l["montant"])
        if l["sens"] == "regle":
            compter_percu("Rafas", jour, montant)
        elif jour.year == annee:
            t["Rafas"] += montant
            rafas_nombre += l["nombre"]
            rafas_base += _nombre(l["base"])
            mois[jour.month]["Acquis"] += montant
        else:
            mois[jour.month]["AcquisPrecedent"] += montant
            if jour <= au_n1:
                t["Precedent"] += montant

    total = t["Commissions"] + t["Accessoires"] + t["Rafas"]
    en_attente = en_attente or {}
    attente = {"AReclamer": _nombre(en_attente.get("AReclamer")), "Reclamees": _nombre(en_attente.get("Reclamees")),
               "Rafas": rafas["NonReglee"]}
    retro = apporteurs["Payees"] + apporteurs["APayer"]
    en_cours = annee == au.year and au.month < 12
    resultat = {
        "Total": _franc(total),
        "Commissions": _franc(t["Commissions"]), "Accessoires": _franc(t["Accessoires"]), "Rafas": _franc(t["Rafas"]),
        "Nombre": t["Nombre"], "RafasFactures": int(rafas_nombre), "RafasBase": _franc(rafas_base),
        "PrimeNette": _franc(t["PrimeNette"]),
        # Revenu du cabinet rapporté aux primes nettes des actes (RAFAS à part : pas de prime d'assurance)
        "TauxMoyen": _taux(t["Commissions"] + t["Accessoires"], t["PrimeNette"]),
        "Precedent": _franc(t["Precedent"]),
        "Percu": {"Total": _franc(sum(percu_sources.values())), **{cle: _franc(v) for cle, v in percu_sources.items()}},
        "PercuPrecedent": _franc(percu_n1),
        "EnAttente": {"Total": _franc(sum(attente.values())), **{cle: _franc(v) for cle, v in attente.items()}},
        "Apporteurs": {"Total": _franc(retro), "Payees": _franc(apporteurs["Payees"]), "APayer": _franc(apporteurs["APayer"])},
        "Net": _franc(total - retro),
        "ParMois": [{
            "Mois": m,
            # Mois à venir de l'exercice en cours : pas de chiffre (et non zéro)
            "ChiffreAffaires": _franc(v["Acquis"]) if not (en_cours and m > au.month) else None,
            "ChiffreAffairesPrecedent": _franc(v["AcquisPrecedent"]),
            "Percu": _franc(v["Percu"]) if not (en_cours and m > au.month) else None,
        } for m, v in mois.items()],
        "PercuParProduit": {k: _franc(v) for k, v in par_produit.items()},
        "PercuParCompagnie": {k: _franc(v) for k, v in par_compagnie.items()},
    }
    if reste is not None:
        resultat["ResteAPercevoir"] = ventiler_reste(reste, rafas)
    return resultat


def calculer(cursor, p, en_attente=None):
    """Chiffre d'affaires de la période p (lectures seules). en_attente n'est donné que pour le cadre « Reste à percevoir » :
    sa ventilation quittance par quittance (lire_reste) n'est lue qu'alors."""
    reste = lire_reste(cursor, p) if en_attente is not None else None
    return assembler(p, lire_acquis(cursor, p), lire_percu(cursor, p), lire_rafas(cursor, p), lire_apporteurs(cursor, p),
                     en_attente, reste)
