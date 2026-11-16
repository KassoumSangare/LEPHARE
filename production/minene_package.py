"""
MINENE en package (demande du 2026-11-16 : « MINENE génère 3 devis liés, mais séparément : je veux que cela soit fait comme
en Oreole Santé »). MINENE réunit trois assurances indissociables : la Santé (saisie à l'écran Santé), l'Individuelle
Accidents (offre 66) et la RC chef de famille (offre 67), toutes deux tarifées par adhérent de la police Santé.

Avant : la Santé était confirmée seule, puis l'IA et la RC saisies chacune sur son écran depuis la police, confirmées et
encaissées à part. Désormais, comme en Oreole Santé (sante/oreole.py) :
- l'enregistrement du devis Santé MINENE crée aussitôt ses devis IA et RC (ou les met à jour), depuis ses adhérents, sans
  ressaisie : les trois devis apparaissent ensemble dans la liste ;
- le devis Santé (et chacun de ses devis liés) montre le package : Santé, IA, RC, leurs primes et le total ;
- la confirmation de l'un des trois, d'où qu'elle vienne (registre, fiche du devis, écran Santé), émet les trois polices
  dans une seule transaction : une erreur n'en émet aucune. Au renouvellement, les devis IA et RC déjà préparés sont
  confirmés, sinon les polices de l'an dernier sont renouvelées (même numéro) ;
- la caisse réunit les trois quittances sur une ligne : un règlement, que le serveur répartit entre elles, un reçu ;
- la fiche d'un contrat Santé, IA ou RC MINENE montre le package et émet ce qui manque.

La base (sp_creation_devis_ia, sp_creation_devis_risques_divers, sp_finalisation_devis) refuse une IA ou une RC MINENE
sans police Santé existante et la tarife d'après les adhérents de cette police. À l'enregistrement de la Santé, les devis IA
et RC sont donc écrits ici (comme Oreole écrit les siens) : ils portent le numéro du devis Santé en police connexe et des
primes provisoires calculées par les fonctions de la base (minene_connexes.forfait_adherent) ; à l'émission, la police
Santé remplace ce numéro et la base recalcule leurs primes, contrôlées contre le tarif avant la confirmation.

Seuls l'affaire nouvelle et le renouvellement font un package : une incorporation ou une modification de la Santé reste un
avenant de la seule police Santé. Le lien est celui qui existait : l'IA et la RC portent la police Santé (le numéro du devis
Santé tant qu'il est en devis) en police connexe, et leur date d'effet tombe dans la période de la Santé ; aucune table nouvelle.

GET  /api/minene/devis/<iddevis>/                package d'un devis Santé, IA ou RC MINENE (devis liés ou polices émises)
POST /api/minene/devis/<iddevis>/emission/       émet Santé, IA et RC ensemble
GET  /api/minene/contrat/<idcontrat>/             package d'un contrat Santé, IA ou RC MINENE
POST /api/minene/contrat/<idcontrat>/emission/   émet l'IA et la RC qui manquent à une police Santé déjà émise
GET  /api/minene/caisse/                          packages dont il reste à encaisser
POST /api/minene/devis/<iddevis>/encaissement/   règlement unique, réparti entre les quittances
"""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import DatabaseError, IntegrityError, connection, transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from configuration_api.parametrage import valeur_parametre
from core.date_parser import date_emission_du_jour

from .database import enregistrer_terme_devis, save_contract, save_quotation_risques_divers
from .iautils import unpack_ia_quotation_post_data
from .minene_connexes import AUTHENTIFICATION, CONNEXES, OFFRE_IA, OFFRE_RC, OFFRES_SANTE_MINENE, forfait_adherent
from .reste_encaissement import reste_a_encaisser

ID_PRODUIT_SANTE, ID_PRODUIT_IA, ID_PRODUIT_RC = 5, 2, 8
ID_COMPAGNIE_NSIA, ID_INTERMEDIAIRE = 1, 1
ID_AVENANT_AFN, ID_AVENANT_REN = 1, 2
ID_TARIF_IA, ID_TARIF_RC = 103, 104
ACTES_PACKAGE = ("AFN", "REN")
ZERO = Decimal(0)
# Produits liés : produit, offre, libellé
LIES = {"IA": (ID_PRODUIT_IA, OFFRE_IA, "Individuelle Accidents"), "RC": (ID_PRODUIT_RC, OFFRE_RC, "RC chef de famille")}

# Devis Santé portant une formule MINENE (au détail ou sur une couverture), alias d
SQL_MINENE = f"""(EXISTS (SELECT 1 FROM stddevisdetail dd WHERE dd.iddevis = d.iddevis AND dd.idoffre IN {OFFRES_SANTE_MINENE})
                  OR EXISTS (SELECT 1 FROM stdfiliale f WHERE f.iddevis = d.iddevis AND f.idoffresante IN {OFFRES_SANTE_MINENE}))"""


class ErreurMinene(Exception):
    pass


def _lignes(cursor, sql, params=None):
    cursor.execute(sql, params or [])
    colonnes = [c[0] for c in cursor.description]
    return [dict(zip(colonnes, l)) for l in cursor.fetchall()]


def _iso(valeur):
    return valeur.isoformat() if valeur else None


def _nombre(valeur):
    return float(valeur or 0)


def _parametre(cle, defaut):
    return Decimal(str(valeur_parametre(f"sante.minene.{cle}", defaut)))


# ------------------------------------------------------------------ lecture
def _sante(cursor, id_devis):
    """Devis Santé MINENE : en-tête, acte, client, nombre d'adhérents. None si ce n'est pas un devis Santé MINENE."""
    lignes = _lignes(cursor, f"""
        SELECT d.iddevis, d.numerodevis, d.idclient, d.dateeffet::date AS dateeffet, d.dateexpiration::date AS dateexpiration,
               d.idduree, d.idterme, COALESCE(d.confirme, FALSE) AS confirme, COALESCE(d.archive, FALSE) AS archive, a.codeavenant,
               d.idoldhist, d.primettc, TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client,
               (SELECT COUNT(*) FROM stdadherent x WHERE x.iddevis = d.iddevis) AS adherents
        FROM stddevis d JOIN stdavenant a ON a.idavenant = d.idavenant LEFT JOIN stdclient cl ON cl.idclient = d.idclient
        WHERE d.iddevis = %s AND d.idproduit = {ID_PRODUIT_SANTE} AND {SQL_MINENE}""", [id_devis])
    return lignes[0] if lignes else None


def _contrat_du_devis(cursor, id_devis):
    lignes = _lignes(cursor, """
        SELECT c.idcontrat, TRIM(c.numeropolice) AS numeropolice, c.idclient, c.dateeffet::date AS dateeffet, c.dateexpiration::date AS dateexpiration,
               c.idduree, c.idterme, c.idcompagnie, q.numeroquittance, q.primettc, COALESCE(q.mt_encaisse, 0) AS encaisse,
               co.raisonsociale AS compagnie
        FROM stdcontrat c LEFT JOIN stdquittance q ON q.idquittance = c.idquittance LEFT JOIN stdcompagnie co ON co.idcompagnie = c.idcompagnie
        WHERE c.iddevis = %s AND COALESCE(c.idcontratannulation, 0) = 0 ORDER BY c.idcontrat DESC LIMIT 1""", [id_devis])
    return lignes[0] if lignes else None


def _lie(cursor, produit, police, debut, fin):
    """IA ou RC de la période de la police Santé : la police émise d'abord, sinon le dernier devis en attente. None sinon."""
    id_produit, id_offre, _libelle = LIES[produit]
    lignes = _lignes(cursor, """
        SELECT d.iddevis, d.numerodevis, COALESCE(d.confirme, FALSE) AS confirme, d.primettc AS ttc_devis,
               ct.idcontrat, TRIM(ct.numeropolice) AS numeropolice, q.numeroquittance, q.primettc AS ttc_quittance,
               COALESCE(q.mt_encaisse, 0) AS encaisse, co.raisonsociale AS compagnie
        FROM stddevis d
        JOIN stdavenant a ON a.idavenant = d.idavenant
        LEFT JOIN LATERAL (SELECT x.idcontrat, x.numeropolice, x.idquittance FROM stdcontrat x
                           WHERE x.iddevis = d.iddevis AND COALESCE(x.idcontratannulation, 0) = 0 ORDER BY x.idcontrat DESC LIMIT 1) ct ON TRUE
        LEFT JOIN stdquittance q ON q.idquittance = ct.idquittance
        LEFT JOIN stdcompagnie co ON co.idcompagnie = d.idcompagnie
        WHERE d.idproduit = %s AND TRIM(COALESCE(d.numeropoliceconnexe, '')) = %s AND a.codeavenant IN ('AFN', 'REN')
          AND d.dateeffet::date BETWEEN %s AND %s AND NOT COALESCE(d.archive, FALSE)
          AND (ct.idcontrat IS NOT NULL OR NOT COALESCE(d.confirme, FALSE))
          AND COALESCE((SELECT MAX(dd.idoffre) FROM stddevisdetail dd WHERE dd.iddevis = d.iddevis), d.idoffre) = %s
        ORDER BY (ct.idcontrat IS NOT NULL) DESC, d.iddevis DESC LIMIT 1""", [id_produit, police, debut, fin, id_offre])
    return lignes[0] if lignes else None


def _lie_en_attente(cursor, produit, numero_devis):
    """IA ou RC créée à l'enregistrement du devis Santé encore en devis : elle porte le numéro de ce devis en police connexe."""
    id_produit, id_offre, _libelle = LIES[produit]
    lignes = _lignes(cursor, """
        SELECT d.iddevis, d.numerodevis, FALSE AS confirme, d.primettc AS ttc_devis, NULL::integer AS idcontrat, NULL::varchar AS numeropolice,
               NULL::varchar AS numeroquittance, NULL::numeric AS ttc_quittance, 0 AS encaisse, co.raisonsociale AS compagnie, TRUE AS au_devis
        FROM stddevis d LEFT JOIN stdcompagnie co ON co.idcompagnie = d.idcompagnie
        WHERE d.idproduit = %s AND TRIM(COALESCE(d.numeropoliceconnexe, '')) = %s AND NOT COALESCE(d.confirme, FALSE) AND NOT COALESCE(d.archive, FALSE)
          AND COALESCE((SELECT MAX(dd.idoffre) FROM stddevisdetail dd WHERE dd.iddevis = d.iddevis), d.idoffre) = %s
        ORDER BY d.iddevis DESC LIMIT 1""", [id_produit, (numero_devis or "").strip(), id_offre])
    return lignes[0] if lignes else None


def _police_precedente(cursor, sante):
    """Renouvellement : police Santé du contrat renouvelé (les devis IA et RC préparés par l'écran de renouvellement la portent) ;
    None pour une affaire nouvelle."""
    if sante["codeavenant"] != "REN" or not sante["idoldhist"]:
        return None
    precedent = _contrat_du_devis(cursor, sante["idoldhist"])
    return precedent["numeropolice"] if precedent else None


def _lie_du_devis(cursor, produit, sante, police):
    """IA ou RC du package d'un devis Santé : par la police (émise, ou devis de renouvellement), sinon par le numéro du devis Santé."""
    lie = _lie(cursor, produit, police, sante["dateeffet"], sante["dateexpiration"]) if police else None
    return lie or _lie_en_attente(cursor, produit, sante["numerodevis"])


def _sante_du_lie(cursor, id_devis):
    """Devis Santé MINENE non confirmé dont ce devis IA ou RC en attente fait partie (lien par le numéro du devis Santé, ou par la police
    pour un renouvellement) ; None sinon."""
    lignes = _lignes(cursor, f"""
        SELECT s.iddevis FROM stddevis x
        JOIN stddevis s ON s.idproduit = {ID_PRODUIT_SANTE} AND TRIM(s.numerodevis) = TRIM(COALESCE(x.numeropoliceconnexe, ''))
        WHERE x.iddevis = %s AND x.idproduit IN ({ID_PRODUIT_IA}, {ID_PRODUIT_RC}) AND NOT COALESCE(x.confirme, FALSE) AND NOT COALESCE(s.confirme, FALSE)
        UNION ALL
        SELECT s.iddevis FROM stddevis x
        JOIN stdcontrat p ON p.idproduit = {ID_PRODUIT_SANTE} AND TRIM(p.numeropolice) = TRIM(COALESCE(x.numeropoliceconnexe, ''))
        JOIN stddevis s ON s.idoldhist = p.iddevis AND s.idproduit = {ID_PRODUIT_SANTE} AND NOT COALESCE(s.confirme, FALSE) AND NOT COALESCE(s.archive, FALSE)
        JOIN stdavenant a ON a.idavenant = s.idavenant AND a.codeavenant = 'REN'
        WHERE x.iddevis = %s AND x.idproduit IN ({ID_PRODUIT_IA}, {ID_PRODUIT_RC}) AND NOT COALESCE(x.confirme, FALSE)
          AND x.dateeffet::date BETWEEN s.dateeffet::date AND s.dateexpiration::date
        LIMIT 1""", [id_devis, id_devis])
    if not lignes:
        return None
    sante = _sante(cursor, lignes[0]["iddevis"])
    return sante["iddevis"] if sante and sante["codeavenant"] in ACTES_PACKAGE else None


def devis_sante_du_devis(cursor, id_devis):
    """Devis Santé MINENE du package d'un devis Santé, IA ou RC (en devis ou déjà émis) ; None hors package."""
    sante = _sante(cursor, id_devis)
    if sante:
        return id_devis if sante["codeavenant"] in ACTES_PACKAGE else None
    lie = _sante_du_lie(cursor, id_devis)
    if lie:
        return lie
    contrat = _contrat_du_devis(cursor, id_devis)
    return devis_sante_du_contrat(cursor, contrat["idcontrat"]) if contrat else None


def devis_lies_en_attente(cursor, id_devis):
    """Devis IA et RC créés avec un devis Santé MINENE non confirmé (suppression du devis Santé : ils partent avec lui)."""
    cursor.execute(f"""
        SELECT x.iddevis FROM stddevis s
        JOIN stddevis x ON x.idproduit IN ({ID_PRODUIT_IA}, {ID_PRODUIT_RC}) AND TRIM(COALESCE(x.numeropoliceconnexe, '')) = TRIM(s.numerodevis)
        WHERE s.iddevis = %s AND s.idproduit = {ID_PRODUIT_SANTE} AND COALESCE(TRIM(s.numerodevis), '') <> '' AND NOT COALESCE(x.confirme, FALSE)
          AND NOT EXISTS (SELECT 1 FROM stdcontrat c WHERE c.iddevis = x.iddevis)""", [id_devis])
    return [ligne[0] for ligne in cursor.fetchall()]


# ------------------------------------------------------------------ IA et RC cochées ou décochées (migration production 0220)
TOUT_SOUSCRIT = {"IA": True, "RC": True}


def choix_modifiable(cursor):
    """La table des choix existe (migration production 0220) : sans elle, l'IA et la RC sont toujours souscrites."""
    cursor.execute("SELECT to_regclass('public.lephare_minene_package') IS NOT NULL")
    return bool(cursor.fetchone()[0])


def lire_choix(cursor, id_devis):
    """IA et RC souscrites avec le devis Santé (cases de l'écran Santé) ; toutes deux tant que rien n'est enregistré."""
    if not choix_modifiable(cursor):
        return dict(TOUT_SOUSCRIT)
    cursor.execute("SELECT ia, rc FROM lephare_minene_package WHERE iddevis_sante = %s", [id_devis])
    ligne = cursor.fetchone()
    return {"IA": bool(ligne[0]), "RC": bool(ligne[1])} if ligne else dict(TOUT_SOUSCRIT)


def _ecrire_choix(cursor, id_devis, choix, id_utilisateur):
    """Enregistre les cases ; renvoie un avertissement si elles ne peuvent l'être (migration 0220 absente : les deux restent souscrites)."""
    if not choix_modifiable(cursor):
        if not all(choix.values()):
            return ("Décocher l'IA ou la RC demande la migration production 0220 (python manage.py migrate production) : "
                    "elles restent souscrites.")
        return ""
    cursor.execute(
        """INSERT INTO lephare_minene_package (iddevis_sante, ia, rc, idoperateur) VALUES (%s, %s, %s, %s)
           ON CONFLICT (iddevis_sante) DO UPDATE SET ia = EXCLUDED.ia, rc = EXCLUDED.rc, idoperateur = EXCLUDED.idoperateur, datemodification = now()""",
        [id_devis, choix["IA"], choix["RC"], id_utilisateur],
    )
    return ""


def oublier_choix(cursor, id_devis):
    """Devis Santé supprimé : son choix d'IA et de RC aussi."""
    if choix_modifiable(cursor):
        cursor.execute("DELETE FROM lephare_minene_package WHERE iddevis_sante = %s", [id_devis])


def _archiver(cursor, id_devis):
    """Produit lié décoché avant la confirmation : son devis est archivé, jamais un contrat (comme Oreole Santé)."""
    cursor.execute("UPDATE stddevis SET archive = TRUE, datearchivage = now() WHERE iddevis = %s AND NOT COALESCE(confirme, FALSE)", [id_devis])


def _adherents_police(cursor, police, defaut):
    """Adhérents comptés par la base pour tarifer l'IA et la RC : ceux du dernier contrat Santé de la police (par date d'effet)."""
    if not police:
        return defaut
    cursor.execute(f"""SELECT (SELECT COUNT(*) FROM stdadherent a WHERE a.iddevis = c.iddevis) FROM stdcontrat c
                       WHERE c.idproduit = {ID_PRODUIT_SANTE} AND TRIM(c.numeropolice) = %s ORDER BY c.dateeffet DESC LIMIT 1""", [police])
    ligne = cursor.fetchone()
    return ligne[0] if ligne else defaut


def _annonce(cursor, produit, effet, adherents):
    """Primes que la base écrira pour l'IA ou la RC : forfait par adhérent (mêmes fonctions), TTC arrondie comme à l'enregistrement."""
    _taux, unitaire = forfait_adherent(cursor, produit.lower(), effet)
    nombre = max(int(adherents or 0), 1)
    cursor.execute("SELECT fn_lephare_arrondi_montant(%s, %s)", [unitaire["PrimeTtc"] * nombre, LIES[produit][0]])
    return {"Unitaire": unitaire["PrimeTtc"], "PrimeTtc": float(cursor.fetchone()[0] or 0), "FraisGestion": unitaire["FraisGestion"] * nombre}


def lire(cursor, id_devis):
    """Package d'un devis Santé MINENE : chaque produit, émis, en devis ou annoncé, et les totaux. None hors MINENE."""
    sante = _sante(cursor, id_devis)
    if not sante or sante["codeavenant"] not in ACTES_PACKAGE:
        return None
    contrat = _contrat_du_devis(cursor, id_devis) if sante["confirme"] else None
    # Police de la période : celle du contrat émis ; pour un renouvellement en devis, celle du contrat renouvelé (les devis IA et RC
    # préparés par l'écran de renouvellement apparaissent alors « en devis ») ; les devis IA et RC créés à l'enregistrement de la
    # Santé sont retrouvés par le numéro du devis Santé
    police = contrat["numeropolice"] if contrat else _police_precedente(cursor, sante)
    produits = {"Sante": {
        "IdDevis": sante["iddevis"], "NumeroDevis": sante["numerodevis"], "Confirme": sante["confirme"],
        "IdContrat": contrat["idcontrat"] if contrat else None, "NumeroPolice": contrat["numeropolice"] if contrat else None,
        "NumeroQuittance": contrat["numeroquittance"] if contrat else None, "Compagnie": contrat["compagnie"] if contrat else "NSIA ASSURANCES",
        "PrimeTtc": _nombre(contrat["primettc"] if contrat else sante["primettc"]), "Encaisse": _nombre(contrat["encaisse"] if contrat else 0),
        "Etat": "Emise" if contrat else "Devis",
    }}
    choix = lire_choix(cursor, id_devis)
    for produit, (_id_produit, _id_offre, libelle) in LIES.items():
        lie = _lie_du_devis(cursor, produit, sante, police)
        if lie and lie["idcontrat"]:
            produits[produit] = {
                "Libelle": libelle, "IdDevis": lie["iddevis"], "NumeroDevis": lie["numerodevis"], "IdContrat": lie["idcontrat"],
                "NumeroPolice": lie["numeropolice"], "NumeroQuittance": lie["numeroquittance"], "Compagnie": lie["compagnie"] or "",
                "PrimeTtc": _nombre(lie["ttc_quittance"]), "Encaisse": _nombre(lie["encaisse"]), "Etat": "Emise", "Inclus": True,
            }
            continue
        if not choix[produit]:
            # Case décochée à l'écran Santé : ni devis, ni police, rien à payer
            produits[produit] = {
                "Libelle": libelle, "IdDevis": None, "NumeroDevis": None, "IdContrat": None, "NumeroPolice": None, "NumeroQuittance": None,
                "Compagnie": "", "PrimeTtc": 0.0, "Encaisse": 0.0, "Etat": "Non souscrite", "Inclus": False, "AuDevisSante": False,
            }
            continue
        annonce = _annonce(cursor, produit, sante["dateeffet"], _adherents_police(cursor, contrat["numeropolice"] if contrat else None, sante["adherents"]))
        produits[produit] = {
            "Libelle": libelle, "IdDevis": lie["iddevis"] if lie else None, "NumeroDevis": lie["numerodevis"] if lie else None,
            "IdContrat": None, "NumeroPolice": None, "NumeroQuittance": None, "Compagnie": lie["compagnie"] if lie else "NSIA ASSURANCES",
            # Un devis en attente est recalculé au tarif à l'émission : la prime annoncée est celle qui sera émise
            "PrimeTtc": annonce["PrimeTtc"], "Encaisse": 0.0,
            "Unitaire": annonce["Unitaire"], "Etat": "Devis" if lie else "A emettre",
            # Créé avec le devis Santé (il en porte le numéro) : il se modifie depuis l'écran Santé
            "AuDevisSante": bool(lie and lie.get("au_devis")), "Inclus": True,
        }
    emis = [p for p in produits.values() if p["IdContrat"]]
    return {
        "Minene": True, "IdDevis": sante["iddevis"], "NumeroDevis": sante["numerodevis"], "Acte": sante["codeavenant"],
        "IdClient": sante["idclient"], "Client": sante["client"], "DateEffet": _iso(sante["dateeffet"]), "DateExpiration": _iso(sante["dateexpiration"]),
        "Adherents": sante["adherents"], "Confirme": sante["confirme"], "NumeroPolice": police,
        "Choix": choix, "ChoixModifiable": choix_modifiable(cursor),
        "Produits": produits,
        "Totaux": {
            "PrimeTtc": sum(p["PrimeTtc"] for p in produits.values()),
            "Encaisse": sum(p["Encaisse"] for p in emis),
            "ResteAEncaisser": float(sum((reste_a_encaisser(Decimal(str(p["PrimeTtc"])), Decimal(str(p["Encaisse"]))) for p in emis), ZERO)),
        },
    }


def devis_sante_du_contrat(cursor, id_contrat):
    """Devis Santé MINENE (affaire nouvelle ou renouvellement) du package d'un contrat Santé, IA ou RC MINENE ; None sinon."""
    lignes = _lignes(cursor, """
        SELECT c.iddevis, c.idproduit, TRIM(c.numeropolice) AS numeropolice, TRIM(COALESCE(c.numeropoliceconnexe, '')) AS connexe,
               c.dateeffet::date AS dateeffet, a.codeavenant
        FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant WHERE c.idcontrat = %s""", [id_contrat])
    if not lignes:
        return None
    c = lignes[0]
    if c["idproduit"] == ID_PRODUIT_SANTE:
        if c["codeavenant"] in ACTES_PACKAGE:
            return c["iddevis"] if _sante(cursor, c["iddevis"]) else None
        police, jour = c["numeropolice"], c["dateeffet"]
    elif c["idproduit"] in (ID_PRODUIT_IA, ID_PRODUIT_RC) and c["connexe"]:
        police, jour = c["connexe"], c["dateeffet"]
    else:
        return None
    # Période Santé (affaire nouvelle ou renouvellement) de cette police qui couvre la date d'effet du contrat ouvert
    sante = _lignes(cursor, f"""
        SELECT d.iddevis FROM stdcontrat x JOIN stdavenant a ON a.idavenant = x.idavenant JOIN stddevis d ON d.iddevis = x.iddevis
        WHERE x.idproduit = {ID_PRODUIT_SANTE} AND TRIM(x.numeropolice) = %s AND COALESCE(x.idcontratannulation, 0) = 0
          AND a.codeavenant IN ('AFN', 'REN') AND %s BETWEEN x.dateeffet::date AND x.dateexpiration::date AND {SQL_MINENE}
        ORDER BY x.dateeffet DESC, x.idcontrat DESC LIMIT 1""", [police, jour])
    return sante[0]["iddevis"] if sante else None


# ------------------------------------------------------------------ émission
def _confirmer(id_devis, libelle, police=None):
    """Confirme un devis dans la transaction en cours ; une erreur annule tout le package."""
    if police:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE stddevis SET numeropoliceconnexe = %s WHERE iddevis = %s", [police, id_devis])
    erreur, resultat = save_contract({"IdDevis": id_devis})
    ligne = (list(resultat) or [None])[0]
    if erreur or not ligne or not ligne.ObjectId:
        raise ErreurMinene(f"{libelle} : {(ligne.OutputMessage if ligne else '') or 'la confirmation a été refusée.'}")
    return ligne.ObjectId


def _client_adherent(cursor, adherent):
    """Fiche client d'un adhérent Santé, assuré de l'IA : par sa CNI (même nom), sinon par nom, prénoms et naissance, sinon créée."""
    from .import_assures import insert_new_assure

    nom, prenoms = (adherent["nom"] or "").strip(), (adherent["prenom"] or "").strip()
    # Clé d'unicité calculée comme le déclencheur trigger_generer_cle_unique (CNI en majuscules sans espaces, sinon nom, prénoms et
    # naissance) ; une fiche ancienne sans clé est reconnue par les mêmes champs : la base la lui calculera à sa prochaine mise à
    # jour (confirmation : solde du client), et une seconde fiche à la même CNI rendrait alors la confirmation impossible
    cni = re.sub(r"\s+", "", adherent["cni"] or "").upper()
    if cni:
        cursor.execute(
            """SELECT idclient, UPPER(TRIM(COALESCE(nom, ''))) FROM stdclient
               WHERE cle_unique = %s OR (COALESCE(TRIM(cle_unique), '') = '' AND UPPER(REGEXP_REPLACE(TRIM(COALESCE(cnipat, '')), '\\s+', '', 'g')) = %s)
               ORDER BY (cle_unique = %s) DESC NULLS LAST, idclient LIMIT 1""", [f"CNI-{cni}", cni, f"CNI-{cni}"])
        trouve = cursor.fetchone()
        if trouve and (not trouve[1] or trouve[1] == nom.upper()):
            return trouve[0]
        if trouve:
            cni = ""  # CNI d'une autre personne : fiche créée sans elle
    if adherent["datenaissance"]:
        cursor.execute(
            """SELECT idclient FROM stdclient
               WHERE cle_unique = %s OR (COALESCE(TRIM(cle_unique), '') = '' AND COALESCE(TRIM(cnipat), '') = ''
                     AND LOWER(TRIM(COALESCE(nom, ''))) = %s AND LOWER(TRIM(COALESCE(prenoms, ''))) = %s AND datenaissance::date = %s)
               ORDER BY idclient LIMIT 1""",
            [f"COMP-{nom.lower()}|{prenoms.lower()}|{adherent['datenaissance'].isoformat()}", nom.lower(), prenoms.lower(), adherent["datenaissance"]])
        trouve = cursor.fetchone()
        if trouve:
            return trouve[0]
    for cni_essai in dict.fromkeys([cni, ""]):
        try:
            with transaction.atomic():
                client = insert_new_assure({
                    "Nom": nom, "Prenoms": prenoms, "NumeroCNI": cni_essai, "DateNaissance": adherent["datenaissance"], "Sexe": adherent["sexe"] or "",
                    "NumeroTelephone": adherent["mobile1"] or "", "NumeroMobile": adherent["mobile1"] or "",
                    "AdressePostale": adherent["adresse"] or "", "AdresseGeographique": adherent["adresse"] or "",
                })
            return client.IdClient
        except IntegrityError:
            continue
    raise ErreurMinene(f"Adhérent {nom} {prenoms} : fiche client impossible à créer.".replace("  ", " "))


def _adherents_ia(cursor, id_devis_sante):
    """Adhérents actifs du devis Santé, assurés de l'IA, et leur fiche client (reprise ou créée)."""
    adherents = _lignes(cursor, """
        SELECT idadherent, nom, prenom, sexe, datenaissance::date AS datenaissance, cni, adresse, mobile1
        FROM stdadherent WHERE iddevis = %s AND COALESCE(actif, TRUE) ORDER BY idadherent""", [id_devis_sante])
    if not adherents:
        raise ErreurMinene("Individuelle Accidents : aucun adhérent actif sur la Santé.")
    return adherents, [_client_adherent(cursor, a) for a in adherents]


def _capitaux_ia():
    return _parametre("ia_capital_deces", 2000000), _parametre("ia_capital_ipt", 2000000), _parametre("ia_frais_medicaux", 100000)


def _capitaux_rc():
    return (_parametre("rc_dommages_corporels", 50000000), _parametre("rc_intoxications", 5000000),
            _parametre("rc_dommages_materiels", 10000000))


def _naissance_principal(adherent):
    return adherent["datenaissance"] or date(date.today().year - 18, date.today().month, 1)


def _creer_ia(cursor, sante, contrat, id_utilisateur):
    """IA MINENE de la police Santé, comme l'écran IA (CreerDevisIAMineneView) mais sans validation intermédiaire : souscripteur = client de la
    police, assurés = adhérents, ayants droit = leurs affiliés, capitaux des réglages MINENE. La base tarife par adhérent de la police."""
    adherents, clients = _adherents_ia(cursor, sante["iddevis"])
    deces, ipp, frais = _capitaux_ia()
    arguments = unpack_ia_quotation_post_data({
        "IdIntermediaire": ID_INTERMEDIAIRE, "IdCompagnie": ID_COMPAGNIE_NSIA, "IdProduit": ID_PRODUIT_IA, "IdOffre": OFFRE_IA, "IdAvenant": ID_AVENANT_AFN,
        "IdClient": contrat["idclient"], "IdAssure": clients[0], "IdProfession": 0, "Flotte": False, "Coassurance": False,
        "DateEffet": contrat["dateeffet"], "DateExpiration": contrat["dateexpiration"], "IdTarif": ID_TARIF_IA,
        "CapitalDeces": deces, "CapitalIpp": ipp, "FraisTraitement": frais, "TauxReduction": 0, "CodeActivite": "01",
        "DateNaissance": _naissance_principal(adherents[0]), "IdDuree": contrat["idduree"], "NumeroPoliceConnexe": contrat["numeropolice"],
    })
    cursor.execute(f"CALL sp_creation_devis_ia({', '.join(['%s'] * len(arguments))});", arguments)
    id_devis, _id_detail, message = cursor.fetchone()
    if not id_devis:
        raise ErreurMinene(f"Individuelle Accidents : {message or 'devis refusé par la base.'}")
    _completer_ia(cursor, id_devis, contrat, adherents, clients)
    enregistrer_terme_devis(id_devis, contrat["idterme"])
    return id_devis


def _completer_ia(cursor, id_devis, periode, adherents, clients):
    """Devis IA MINENE dont l'assuré principal est écrit : les autres adhérents (lignes sans prime, la base multipliant celle de l'assuré
    principal par le nombre d'adhérents) et les ayants droit (affiliés Santé)."""
    from .views import _build_lien_qualite_map

    deces, ipp, frais = _capitaux_ia()
    cursor.execute("SELECT idoffre, idtarif FROM stddevisdetail WHERE iddevis = %s AND idoffre <> 0 ORDER BY iddevisdetail LIMIT 1", [id_devis])
    offre_tarif = cursor.fetchone() or (OFFRE_IA, ID_TARIF_IA)
    deja = {clients[0]}
    for adherent, id_client in zip(adherents[1:], clients[1:]):
        if id_client in deja:
            continue
        deja.add(id_client)
        # Ligne sans offre : ni garantie ni prime (la base multiplie la prime d'une ligne par le nombre d'adhérents)
        try:
            with transaction.atomic(), connection.cursor() as c:
                c.execute("CALL sp_enregistrement_assure_ia(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);",
                          [ID_COMPAGNIE_NSIA, ID_PRODUIT_IA, 0, id_client, 12, periode["dateeffet"], periode["dateexpiration"], offre_tarif[1],
                           deces, ipp, frais, 0, "01", adherent["datenaissance"] or date(1970, 1, 1), adherent["adresse"] or "", id_devis, 0, 0, 0, 0, ""])
                c.fetchone()
        except DatabaseError as erreur:
            message = str(erreur).splitlines()[0]
            if "déjà" not in message.lower():
                raise ErreurMinene(f"Individuelle Accidents, {adherent['nom']} : {message}") from erreur
    cursor.execute("UPDATE stddevisdetail SET idoffre = %s, idtarif = %s WHERE iddevis = %s AND idoffre = 0", [offre_tarif[0], offre_tarif[1], id_devis])

    # Ayants droit IA = affiliés Santé (conjoint, enfants), une seule fois par assuré
    qualites = _build_lien_qualite_map()
    for adherent, id_client in zip(adherents, clients):
        for affilie in _lignes(cursor, """SELECT lien, nom, prenom FROM stdaffilie WHERE idadherent = %s AND COALESCE(actif, TRUE)
                                         ORDER BY idaffilie""", [adherent["idadherent"]]):
            qualite = qualites.get(affilie["lien"])
            if not qualite:
                continue
            cursor.execute("""SELECT 1 FROM stdayantdroitia WHERE idassure = %s AND UPPER(TRIM(COALESCE(nomayantdroit, ''))) = UPPER(TRIM(%s))
                                AND UPPER(TRIM(COALESCE(prenomsayantdroit, ''))) = UPPER(TRIM(%s))""", [id_client, affilie["nom"] or "", affilie["prenom"] or ""])
            if cursor.fetchone():
                continue
            cursor.execute("CALL sp_saisie_ayant_droit_ia(%s, %s, %s, %s, %s, %s, %s);", [id_client, qualite, affilie["nom"] or "", affilie["prenom"] or "", 0, 0, ""])
            cursor.fetchone()


def _creer_rc(contrat, id_utilisateur, id_devis=0, id_avenant=ID_AVENANT_AFN):
    """RC chef de famille MINENE de la police Santé, comme l'écran RC : capitaux des réglages, primes de la base. id_devis : devis RC existant
    (renouvellement) recalculé par la même procédure, comme le fait l'écran RC à l'enregistrement."""
    from .serializers import EnregistrementDevisRisqquesDiversSerializer

    corporel, intoxications, materiel = _capitaux_rc()
    donnees = {
        "IdIntermediaire": ID_INTERMEDIAIRE, "IdCompagnie": ID_COMPAGNIE_NSIA, "NumeroPoliceCompagnie": "", "IdProduit": ID_PRODUIT_RC, "IdOffre": OFFRE_RC,
        "IdAvenant": id_avenant, "IdClient": contrat["idclient"], "IdAssure": contrat["idclient"], "Flotte": False, "Coassurance": False,
        "DateEffet": _iso(contrat["dateeffet"]), "DateExpiration": _iso(contrat["dateexpiration"]), "DateEmission": _iso(date_emission_du_jour()),
        "IdTarif": ID_TARIF_RC, "TauxReduction": 0, "TelephoneAssure": "", "AdresseGeographique": "", "NumeroPoliceConnexe": contrat["numeropolice"],
        "PrimeNette": 0, "Accessoire": 0, "Taxe": 0, "PrimeTTC": 0, "IdDevis": id_devis, "IdDuree": contrat["idduree"] or 4, "ListeGarantie": [],
        "Activite": "", "IdDomaineActivite": 0, "Localisation": "", "NombreParticipants": 0, "TauxPrime": 0,
        "CapitalDommageCorporel": corporel, "CapitalIntoxicationAlimentaire": intoxications, "CapitalDommageMateriel": materiel,
    }
    serialiseur = EnregistrementDevisRisqquesDiversSerializer(data=donnees)
    if not serialiseur.is_valid():
        raise ErreurMinene(f"RC chef de famille : données refusées ({serialiseur.errors}).")
    erreur, resultat = save_quotation_risques_divers(id_utilisateur, serialiseur.validated_data)
    ligne = (list(resultat) or [None])[0]
    if erreur or not ligne or not ligne.ObjectId:
        raise ErreurMinene(f"RC chef de famille : {(ligne.OutputMessage if ligne else '') or 'devis refusé par la base.'}")
    enregistrer_terme_devis(ligne.ObjectId, contrat["idterme"])
    return ligne.ObjectId


def _renouveler(cursor, produit, contrat, id_utilisateur):
    """Renouvellement : la police IA ou RC de l'an dernier est renouvelée (même numéro) pour la période de la Santé. None si elle n'existe pas."""
    id_produit, id_offre, libelle = LIES[produit]
    precedents = _lignes(cursor, """
        SELECT x.idcontrat FROM stdcontrat x JOIN stdavenant a ON a.idavenant = x.idavenant
        WHERE x.idproduit = %s AND TRIM(COALESCE(x.numeropoliceconnexe, '')) = %s AND COALESCE(x.idcontratannulation, 0) = 0
          AND a.codeavenant IN ('AFN', 'REN') AND x.dateeffet::date < %s
          AND EXISTS (SELECT 1 FROM stddevisdetail dd WHERE dd.iddevis = x.iddevis AND dd.idoffre = %s)
        ORDER BY x.dateeffet DESC, x.idcontrat DESC LIMIT 1""", [id_produit, contrat["numeropolice"], contrat["dateeffet"], id_offre])
    if not precedents:
        return None
    try:
        with transaction.atomic(), connection.cursor() as c:
            c.execute("CALL sp_avenant_creation_devis_initial(%s, %s, %s, %s, %s, %s, '', 0, '')",
                      [id_utilisateur, precedents[0]["idcontrat"], ID_AVENANT_REN, date_emission_du_jour(), contrat["dateeffet"], contrat["dateexpiration"]])
            id_devis, message = c.fetchone()
    except DatabaseError as erreur:
        raise ErreurMinene(f"{libelle} : {str(erreur).splitlines()[0].split(' : ')[0][:300]}") from erreur
    if not id_devis:
        raise ErreurMinene(f"{libelle} : {message or 'le renouvellement a été refusé.'}")
    # Police connexe : sp_avenant_initiation ne la recopie pas (voir renouvellement.py)
    cursor.execute("UPDATE stddevis SET numeropoliceconnexe = %s WHERE iddevis = %s", [contrat["numeropolice"], id_devis])
    # Le devis renouvelé sort à 0 F (l'écran le recalcule à l'enregistrement) : primes recalculées sur les adhérents de la police Santé.
    # IA : finalisation de la base ; RC : sa procédure de création, la finalisation ne multipliant pas la RC MINENE par les adhérents
    if produit == "IA":
        cursor.execute("SELECT idclient, COALESCE(idassure, idclient), COALESCE(flotte, FALSE) FROM stddevis WHERE iddevis = %s", [id_devis])
        id_client, id_assure, flotte = cursor.fetchone()
        cursor.execute("CALL sp_finalisation_devis(%s, %s, %s, %s, '')", [id_devis, id_client, id_assure, flotte])
        cursor.fetchone()
        enregistrer_terme_devis(id_devis, contrat["idterme"])
    else:
        _creer_rc(contrat, id_utilisateur, id_devis=id_devis, id_avenant=ID_AVENANT_REN)
    cursor.execute("SELECT primettc FROM stddevis WHERE iddevis = %s", [id_devis])
    if not (cursor.fetchone()[0] or 0):
        raise ErreurMinene(f"{libelle} : le devis de renouvellement reste à 0 F.")
    return id_devis


def _recalculer(cursor, produit, id_devis, contrat, id_utilisateur):
    """Devis IA ou RC déjà en attente : primes recalculées sur la composition actuelle de la police Santé, comme à l'enregistrement de son écran
    (RC : sa procédure de création ; IA : la finalisation, sauf prime imposée), puis contrôlées contre le tarif MINENE avant la confirmation."""
    cursor.execute("SELECT idavenant, COALESCE(primeimposee, FALSE), idclient, COALESCE(idassure, idclient), COALESCE(flotte, FALSE) FROM stddevis WHERE iddevis = %s",
                   [id_devis])
    id_avenant, imposee, id_client, id_assure, flotte = cursor.fetchone()
    if produit == "RC":
        _creer_rc(contrat, id_utilisateur, id_devis=id_devis, id_avenant=id_avenant)
    elif not imposee:
        cursor.execute("CALL sp_finalisation_devis(%s, %s, %s, %s, '')", [id_devis, id_client, id_assure, flotte])
        cursor.fetchone()
    _controler_tarif(cursor, produit, id_devis, contrat)


def _controler_tarif(cursor, produit, id_devis, contrat):
    """La prime du devis IA ou RC doit être celle du tarif MINENE pour les adhérents de la police : sinon rien n'est émis."""
    attendu = _annonce(cursor, produit, contrat["dateeffet"], _adherents_police(cursor, contrat["numeropolice"], 1))["PrimeTtc"]
    cursor.execute("SELECT numerodevis, primettc FROM stddevis WHERE iddevis = %s", [id_devis])
    numero, ttc = cursor.fetchone()
    if abs(float(ttc or 0) - attendu) > 5:
        raise ErreurMinene(f"{LIES[produit][2]} : le devis {numero} vaut {float(ttc or 0):,.0f} F au lieu de {attendu:,.0f} F (tarif MINENE). "
                           "Réenregistrez-le à son écran ou supprimez-le, puis émettez de nouveau.".replace(",", " "))


# ------------------------------------------------------------------ devis IA et RC écrits à l'enregistrement de la Santé
def _nouvel_entete(cursor, produit, periode, id_assure, id_utilisateur):
    """En-tête d'un devis IA ou RC d'affaire nouvelle, numéroté comme par sp_creation_devis_ia / sp_creation_devis_risques_divers."""
    id_produit, id_offre, _libelle = LIES[produit]
    cursor.execute("SELECT codecategorie FROM stdtarif WHERE idtarif = %s", [ID_TARIF_IA if produit == "IA" else ID_TARIF_RC])
    categorie = (cursor.fetchone() or [""])[0]
    cursor.execute("CALL sp_numeroter_avenant(%s, %s, NULL, '')", [ID_AVENANT_AFN, ID_INTERMEDIAIRE])
    numero_avenant = cursor.fetchone()[0]
    cursor.execute("CALL sp_generer_numero_devis(%s, %s, %s, '', '')", [ID_INTERMEDIAIRE, ID_COMPAGNIE_NSIA, categorie])
    numero_devis, message = cursor.fetchone()
    if not numero_devis:
        raise ErreurMinene(f"{LIES[produit][2]} : {message or 'numéro de devis non attribué.'}")
    cursor.execute(
        """INSERT INTO stddevis (idoperateur, idoffre, idintermediaire, idcompagnie, idproduit, idclient, idassure, idavenant, numeroavenant, numerodevis,
               flotte, idaperiteur, coassurance, periode, dateemission, dateeffet, dateexpiration, confirme, accessoirecompagnie, accessoireintermediaire,
               idduree, numeropoliceconnexe, primeimposee)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, FALSE, fn_calcul_periode_contrat(%s::date - %s::date), %s, %s, %s, FALSE, 0, 0,
               COALESCE(%s, fn_calcul_id_duree_contrat(%s::date - %s::date)), %s, FALSE)
           RETURNING iddevis""",
        [id_utilisateur, id_offre, ID_INTERMEDIAIRE, ID_COMPAGNIE_NSIA, id_produit, periode["idclient"], id_assure, ID_AVENANT_AFN, numero_avenant,
         numero_devis, ID_COMPAGNIE_NSIA, periode["dateexpiration"], periode["dateeffet"], date_emission_du_jour(), periode["dateeffet"],
         periode["dateexpiration"], periode["idduree"], periode["dateexpiration"], periode["dateeffet"], periode["numeropolice"]],
    )
    return cursor.fetchone()[0]


def _maj_entete(cursor, id_devis, periode, id_assure, id_utilisateur):
    """Devis IA ou RC du package réenregistré avec la Santé : souscripteur, période et durée de la Santé."""
    cursor.execute(
        """UPDATE stddevis SET idoperateur = %s, idclient = %s, idassure = %s, dateemission = %s, dateeffet = %s, dateexpiration = %s,
               periode = fn_calcul_periode_contrat(%s::date - %s::date), idduree = COALESCE(%s, fn_calcul_id_duree_contrat(%s::date - %s::date)),
               numeropoliceconnexe = %s
           WHERE iddevis = %s AND NOT COALESCE(confirme, FALSE)""",
        [id_utilisateur, periode["idclient"], id_assure, date_emission_du_jour(), periode["dateeffet"], periode["dateexpiration"],
         periode["dateexpiration"], periode["dateeffet"], periode["idduree"], periode["dateexpiration"], periode["dateeffet"],
         periode["numeropolice"], id_devis],
    )


def _ecrire_ia(cursor, sante, periode, id_devis, id_utilisateur):
    """Devis IA du package : assurés = adhérents de la Santé (réécrits seulement s'ils ont changé), capitaux des réglages MINENE.
    Écrit comme sp_creation_devis_ia, sans son contrôle de la police Santé, qui n'existe pas encore."""
    adherents, clients = _adherents_ia(cursor, sante["iddevis"])
    if id_devis:
        _maj_entete(cursor, id_devis, periode, clients[0], id_utilisateur)
        cursor.execute("SELECT TRIM(matricule) FROM stddevisdetail WHERE iddevis = %s", [id_devis])
        if sorted(l[0] for l in cursor.fetchall()) == sorted({str(c).zfill(20) for c in clients}):
            return id_devis
        cursor.execute("DELETE FROM stddevisdetgarantie WHERE iddevisdet IN (SELECT iddevisdetail FROM stddevisdetail WHERE iddevis = %s)", [id_devis])
        cursor.execute("DELETE FROM stddevisdetail WHERE iddevis = %s", [id_devis])
    else:
        id_devis = _nouvel_entete(cursor, "IA", periode, clients[0], id_utilisateur)
    deces, ipp, frais = _capitaux_ia()
    principal = adherents[0]
    try:
        with transaction.atomic(), connection.cursor() as c:
            c.execute("CALL sp_enregistrement_assure_ia(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);",
                      [ID_COMPAGNIE_NSIA, ID_PRODUIT_IA, OFFRE_IA, clients[0], 0, periode["dateeffet"], periode["dateexpiration"], ID_TARIF_IA,
                       deces, ipp, frais, 0, "01", _naissance_principal(principal), principal["adresse"] or "", id_devis, 0, 0, 0, 0, ""])
            c.fetchone()
    except DatabaseError as erreur:
        raise ErreurMinene(f"Individuelle Accidents, {principal['nom']} : {str(erreur).splitlines()[0]}") from erreur
    _completer_ia(cursor, id_devis, periode, adherents, clients)
    return id_devis


def _ecrire_rc(cursor, periode, id_devis, id_utilisateur):
    """Devis RC du package, écrit comme sp_creation_devis_risques_divers (sans son contrôle de la police Santé) : une ligne aux capitaux des
    réglages MINENE, garanties et franchise de fn_garantie_offre_risques_divers, taxes par garantie."""
    corporel, intoxications, materiel = _capitaux_rc()
    if id_devis:
        _maj_entete(cursor, id_devis, periode, periode["idclient"], id_utilisateur)
    else:
        id_devis = _nouvel_entete(cursor, "RC", periode, periode["idclient"], id_utilisateur)
    cursor.execute("SELECT iddevisdetail FROM stddevisdetail WHERE iddevis = %s ORDER BY iddevisdetail", [id_devis])
    details = [l[0] for l in cursor.fetchall()]
    if len(details) == 1:
        id_detail = details[0]
        cursor.execute("UPDATE stddevisdetail SET valeurneuve = %s, valeurvenale = %s, valeuraccessoire = %s WHERE iddevisdetail = %s",
                       [corporel, intoxications, materiel, id_detail])
    else:
        for table, colonne in (("stddevisdetgarantie", "iddevisdet"), ("stdcomplementdevisdetailrc", "iddevisdetail")):
            cursor.execute(f"DELETE FROM {table} WHERE {colonne} IN (SELECT iddevisdetail FROM stddevisdetail WHERE iddevis = %s)", [id_devis])
        cursor.execute("DELETE FROM stddevisdetail WHERE iddevis = %s", [id_devis])
        cursor.execute(
            """INSERT INTO stddevisdetail (iddevis, idoffre, idtarif, vehicule, idusage, codeusage, reference, idcarrosserie, puissancefiscale, nombreplace,
                   chargeutile, valeurneuve, valeurvenale, valeuraccessoire, remorque, conducteur, adressecnd, datemec, datemutation, nummoteur, numchassis,
                   typevehicule, idmarque, matricule, carteverte, essence, numpccnd, tauxreduction, primeimposee, observation)
               VALUES (%s, %s, %s, 1, 0, '000', '000', 0, 0, 0, 0, %s, %s, %s, FALSE, '', '', '1900-01-01', '1900-01-01', '', '', '', 0, '', FALSE, 0, '', 0,
                   FALSE, '')
               RETURNING iddevisdetail""",
            [id_devis, OFFRE_RC, ID_TARIF_RC, corporel, intoxications, materiel],
        )
        id_detail = cursor.fetchone()[0]
        cursor.execute("""INSERT INTO stdcomplementdevisdetailrc (tauxprime, assietteprime, nombreparticipants, iddomaineactivite, idactivite, localisation,
                              datedebut, iddevisdetail) VALUES (0, 0, 0, 0, 0, '', NULL, %s)""", [id_detail])
    cursor.execute("DELETE FROM stddevisdetgarantie WHERE iddevisdet = %s", [id_detail])
    cursor.execute(
        """INSERT INTO stddevisdetgarantie (iddevisdet, idgarantie, acquise, taxe, capital, tauxfranchise, minfranchise, maxfranchise, primeannuelle,
               primenette, old_acquise, old_primenette, franchise, textefranchise)
           SELECT %s, g.idsousgarantie, g.acquise, 0, g.capital, g.tauxfranchise, g.franchiseminimum, g.franchisemaximum, g.primeannuelle, g.primenette,
                  '0', 0, g.montantfranchise, g.franchisetexte
           FROM fn_garantie_offre_risques_divers(%s, %s, 0, %s, %s, %s, 0, 0, %s, %s, %s, %s) AS g
           WHERE g.idgarantie <> 0 ORDER BY g.idgarantie""",
        [id_detail, ID_COMPAGNIE_NSIA, OFFRE_RC, corporel, intoxications, materiel, periode["dateeffet"], periode["dateexpiration"], ID_PRODUIT_RC, id_devis],
    )
    cursor.execute(
        """UPDATE stddevisdetgarantie AS g SET taxe = ROUND((g.primenette * t.tauxtaxe) / 100, 4) FROM stdtauxtaxegarantieproduit AS t
           WHERE g.iddevisdet = %s AND g.idgarantie = t.idgarantie AND t.idproduit = %s AND %s BETWEEN t.debutvalidite AND t.finvalidite""",
        [id_detail, ID_PRODUIT_RC, periode["dateeffet"]],
    )
    cursor.execute(
        """UPDATE stddevisdetail AS d SET primeannuelle = m.primeannuelle, primenette = m.primenette, taxeenregistrement = ROUND(m.taxe, 0)
           FROM (SELECT SUM(primeannuelle) AS primeannuelle, SUM(primenette) AS primenette, SUM(taxe) AS taxe FROM stddevisdetgarantie WHERE iddevisdet = %s) AS m
           WHERE d.iddevisdetail = %s""",
        [id_detail, id_detail],
    )
    return id_devis


def _ecrire_primes_annoncees(cursor, produit, id_devis, effet, adherents):
    """Primes d'un devis IA ou RC du package tant que la police Santé n'existe pas : celles que la base écrira à l'émission
    (sp_finalisation_devis, sp_creation_devis_risques_divers) : forfait d'un adhérent, accessoire et taxe du barème, frais de gestion MINENE,
    multipliés par le nombre d'adhérents ; commission au taux du produit. La base les recalcule à l'émission."""
    id_produit, id_offre, prime_base = CONNEXES[produit.lower()]
    cursor.execute(
        f"""UPDATE stddevis AS d SET primeannuelle = v.prime, primenette = v.prime * %s, accessoirecompagnie = v.compagnie * %s,
                accessoireintermediaire = v.intermediaire * %s, accessoire = (v.compagnie + v.intermediaire) * %s,
                taxe = ROUND((v.prime + v.compagnie + v.intermediaire) * v.taux / 100, 0) * %s, accessoiregestionnaire = v.frais * %s,
                commissionintermediaire = ROUND(v.prime * %s * COALESCE(v.commission, 0) / 100, 0), fga = 0, cedeao = 0, primeimposee = FALSE
            FROM (SELECT {prime_base} AS prime, a.accessoire_compagnie AS compagnie, a.accessoire_intermediaire AS intermediaire,
                         fn_get_taux_taxe(%s, %s, %s, %s) AS taux, fn_get_frais_gestion_minene(%s) AS frais, fn_get_taux_commission(%s, %s, %s) AS commission
                  FROM fn_get_accessoire({prime_base}, %s, %s, %s, %s) AS a) AS v
            WHERE d.iddevis = %s""",
        [*[max(int(adherents or 0), 1)] * 7, ID_COMPAGNIE_NSIA, id_produit, id_offre, effet, id_produit, id_produit, ID_COMPAGNIE_NSIA,
         date_emission_du_jour(), id_produit, id_offre, ID_COMPAGNIE_NSIA, effet, id_devis],
    )
    cursor.execute("UPDATE stddevis SET primettc = ROUND(primenette + accessoire + taxe + COALESCE(accessoiregestionnaire, 0), 0) WHERE iddevis = %s",
                   [id_devis])


def preparer(id_devis, id_utilisateur, choix=None):
    """Enregistrement d'un devis Santé MINENE (affaire nouvelle ou renouvellement), comme en Oreole Santé : ses devis IA et RC sont créés ou mis
    à jour aussitôt, depuis ses adhérents, sans ressaisie. choix : {"IA": bool, "RC": bool}, cases de l'écran Santé (None : choix enregistré
    gardé) ; un produit décoché voit son devis lié archivé. Renvoie le package ; None hors MINENE ou pour un devis déjà confirmé."""
    with transaction.atomic(), connection.cursor() as cursor:
        sante = _sante(cursor, id_devis)
        if not sante or sante["codeavenant"] not in ACTES_PACKAGE or sante["confirme"] or sante["archive"]:
            return None
        avertissement = _ecrire_choix(cursor, id_devis, {**TOUT_SOUSCRIT, **choix}, id_utilisateur) if choix is not None else ""
        choix = lire_choix(cursor, id_devis)
        police = _police_precedente(cursor, sante)
        numero_sante = (sante["numerodevis"] or "").strip()
        # Produit décoché : son devis en attente (créé avec la Santé, ou préparé par l'écran de renouvellement) est archivé
        for produit in (p for p in LIES if not choix[p]):
            prepare = _lie(cursor, produit, police, sante["dateeffet"], sante["dateexpiration"]) if police else None
            for lie in (prepare, _lie_en_attente(cursor, produit, numero_sante) if numero_sante else None):
                if lie and not lie["idcontrat"]:
                    _archiver(cursor, lie["iddevis"])
        if not sante["adherents"] or not (sante["primettc"] or 0) or not numero_sante:
            return {**(lire(cursor, id_devis) or {}), "Avertissement": avertissement}
        # Tant que la Santé est en devis, son numéro tient lieu de police connexe
        periode = {"numeropolice": numero_sante, "idclient": sante["idclient"], "dateeffet": sante["dateeffet"],
                   "dateexpiration": sante["dateexpiration"], "idduree": sante["idduree"], "idterme": sante["idterme"]}
        for produit in (p for p in LIES if choix[p]):
            prepare = _lie(cursor, produit, police, sante["dateeffet"], sante["dateexpiration"]) if police else None
            if prepare and prepare["idcontrat"]:
                continue
            if prepare:
                # Renouvellement préparé par son écran (lié par la police) : composition gardée, primes reprises ci-dessous
                id_lie = prepare["iddevis"]
            else:
                attente = _lie_en_attente(cursor, produit, periode["numeropolice"])
                id_lie = attente["iddevis"] if attente else None
                if not id_lie and police:
                    # Renouvellement : la police IA ou RC de l'an dernier est renouvelée (même numéro à l'émission)
                    id_lie = _renouveler(cursor, produit, {**periode, "numeropolice": police}, id_utilisateur)
                elif produit == "IA":
                    id_lie = _ecrire_ia(cursor, sante, periode, id_lie, id_utilisateur)
                else:
                    id_lie = _ecrire_rc(cursor, periode, id_lie, id_utilisateur)
                if not id_lie:
                    id_lie = _ecrire_ia(cursor, sante, periode, None, id_utilisateur) if produit == "IA" else _ecrire_rc(cursor, periode, None, id_utilisateur)
            cursor.execute("SELECT COALESCE(primeimposee, FALSE) FROM stddevis WHERE iddevis = %s", [id_lie])
            if not cursor.fetchone()[0]:
                _ecrire_primes_annoncees(cursor, produit, id_lie, sante["dateeffet"], sante["adherents"])
            enregistrer_terme_devis(id_lie, sante["idterme"])
        return {**(lire(cursor, id_devis) or {}), "Avertissement": avertissement}


def emettre(id_devis, id_utilisateur):
    """Confirme le devis Santé MINENE s'il ne l'est pas, puis émet l'IA et la RC de sa période qui manquent, dans une seule transaction."""
    with transaction.atomic(), connection.cursor() as cursor:
        sante = _sante(cursor, id_devis)
        if not sante:
            raise ErreurMinene(f"Le devis n° {id_devis} n'est pas un devis Santé MINENE.")
        if sante["codeavenant"] not in ACTES_PACKAGE:
            raise ErreurMinene("Seuls l'affaire nouvelle et le renouvellement émettent le package MINENE.")
        if sante["archive"] and not sante["confirme"]:
            raise ErreurMinene("Devis archivé : il ne peut plus être confirmé.")
        if not sante["adherents"]:
            raise ErreurMinene("Aucun adhérent sur le devis Santé : l'IA et la RC sont tarifées par adhérent.")
        if not sante["confirme"] and not (sante["primettc"] or 0):
            raise ErreurMinene("Le devis Santé est à 0 F : enregistrez-le d'abord à l'écran Santé pour calculer ses primes.")
        emis = []
        if not sante["confirme"]:
            _confirmer(id_devis, "Santé")
            emis.append("Santé")
        contrat = _contrat_du_devis(cursor, id_devis)
        if not contrat:
            raise ErreurMinene("Contrat Santé introuvable : la confirmation a été annulée.")
        choix = lire_choix(cursor, id_devis)
        for produit, (_id_produit, _id_offre, libelle) in LIES.items():
            if not choix[produit]:
                continue  # décochée à l'écran Santé : ni créée, ni renouvelée, ni émise
            lie = _lie_du_devis(cursor, produit, sante, contrat["numeropolice"])
            if lie and lie["idcontrat"]:
                continue
            if lie:
                id_lie = lie["iddevis"]
                # Devis créé à l'enregistrement de la Santé : la police Santé remplace le numéro du devis avant que la base le recalcule
                cursor.execute("UPDATE stddevis SET numeropoliceconnexe = %s WHERE iddevis = %s", [contrat["numeropolice"], id_lie])
                _recalculer(cursor, produit, id_lie, contrat, id_utilisateur)
            else:
                id_lie = _renouveler(cursor, produit, contrat, id_utilisateur) if sante["codeavenant"] == "REN" else None
                if not id_lie:
                    id_lie = _creer_ia(cursor, sante, contrat, id_utilisateur) if produit == "IA" else _creer_rc(contrat, id_utilisateur)
                _controler_tarif(cursor, produit, id_lie, contrat)
            _confirmer(id_lie, libelle, contrat["numeropolice"])
            emis.append(produit)
        resultat = lire(cursor, id_devis)
        if resultat is None:
            raise ErreurMinene("Package MINENE illisible après l'émission.")
        resultat["Emis"] = emis
        return resultat


def confirmation_depuis_registre(id_devis, id_utilisateur):
    """Confirmation d'un devis (POST /api/confirmationdevis) : le devis Santé MINENE d'affaire nouvelle ou de renouvellement, ou l'un de ses
    devis IA et RC en attente, émet tout le package, comme en Oreole Santé. Renvoie (identifiant du contrat du devis confirmé, message) ;
    None si le devis n'est pas concerné (confirmation habituelle)."""
    with connection.cursor() as cursor:
        sante = _sante(cursor, id_devis)
        if not sante:
            id_sante = _sante_du_lie(cursor, id_devis)
            sante = _sante(cursor, id_sante) if id_sante else None
    if not sante or sante["codeavenant"] not in ACTES_PACKAGE or sante["confirme"]:
        return None
    resultat = emettre(sante["iddevis"], id_utilisateur)
    libelles = {"Santé": "Santé", "IA": "Individuelle Accidents", "RC": "RC chef de famille"}
    produit = next((p for p in resultat["Produits"].values() if p.get("IdDevis") == id_devis), resultat["Produits"]["Sante"])
    return produit["IdContrat"], f"MINENE émis : {', '.join(libelles[e] for e in resultat['Emis'])}."


# ------------------------------------------------------------------ caisse
def quittances_des_packages(cursor, id_devis=None, verrou=False):
    """Quittances émises de chaque package MINENE (Santé d'abord), au format de la caisse Oreole Santé ; un package sans IA ni RC émise n'y
    figure pas (sa quittance Santé reste une ligne ordinaire)."""
    lignes = _lignes(cursor, f"""
        WITH sante AS (
            SELECT c.idcontrat, c.iddevis, TRIM(c.numeropolice) AS police, c.dateeffet::date AS effet, c.dateexpiration::date AS echeance
            FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant JOIN stddevis d ON d.iddevis = c.iddevis
            WHERE c.idproduit = {ID_PRODUIT_SANTE} AND COALESCE(c.idcontratannulation, 0) = 0 AND a.codeavenant IN ('AFN', 'REN') AND {SQL_MINENE}
              {"AND c.iddevis = %s" if id_devis else ""}
        )
        SELECT s.iddevis AS iddevis_sante, v.produit, x.idcontrat, x.numeropolice, q.numeroquittance, q.dateemission::date AS dateemission, q.primettc,
               COALESCE(q.mt_encaisse, 0) AS encaisse, co.raisonsociale AS compagnie, x.idcompagnie,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client,
               (SELECT MAX(de.idencaissement) FROM stddetailencaissement de JOIN stdencaissement e ON e.idencaissement = de.idencaissement
                WHERE de.numeroquittance = q.numeroquittance AND NOT COALESCE(e.piece_annulee, FALSE)) AS dernierencaissement
        FROM sante s
        CROSS JOIN LATERAL (VALUES (1, 'Sante', {ID_PRODUIT_SANTE}, 0), (2, 'IA', {ID_PRODUIT_IA}, {OFFRE_IA}), (3, 'RC', {ID_PRODUIT_RC}, {OFFRE_RC}))
            AS v(ordre, produit, idproduit, idoffre)
        JOIN LATERAL (
            SELECT x.idcontrat, x.numeropolice, x.idquittance, x.idcompagnie FROM stdcontrat x JOIN stdavenant ax ON ax.idavenant = x.idavenant
            WHERE COALESCE(x.idcontratannulation, 0) = 0 AND (
                  (v.ordre = 1 AND x.idcontrat = s.idcontrat)
               OR (v.ordre > 1 AND x.idproduit = v.idproduit AND TRIM(COALESCE(x.numeropoliceconnexe, '')) = s.police AND ax.codeavenant IN ('AFN', 'REN')
                   AND x.dateeffet::date BETWEEN s.effet AND s.echeance
                   AND EXISTS (SELECT 1 FROM stddevisdetail dd WHERE dd.iddevis = x.iddevis AND dd.idoffre = v.idoffre)))
            ORDER BY x.idcontrat DESC LIMIT 1) x ON TRUE
        JOIN stdquittance q ON q.idquittance = x.idquittance
        LEFT JOIN stdcompagnie co ON co.idcompagnie = x.idcompagnie
        LEFT JOIN stdclient cl ON cl.idclient = q.idclient
        ORDER BY s.iddevis DESC, v.ordre {"FOR UPDATE OF q" if verrou else ""}""", [id_devis] if id_devis else [])
    groupes = {}
    for l in lignes:
        groupe = groupes.setdefault(l["iddevis_sante"], {
            "IdDevis": l["iddevis_sante"], "Branche": "MINENE", "Client": l["client"], "NumeroPolice": l["numeropolice"],
            "NumeroQuittance": l["numeroquittance"], "DateEmission": _iso(l["dateemission"]), "DernierEncaissement": None, "Quittances": [],
        })
        if l["dernierencaissement"]:
            groupe["DernierEncaissement"] = max(groupe["DernierEncaissement"] or 0, l["dernierencaissement"])
        groupe["Quittances"].append({
            "Produit": l["produit"], "IdContrat": l["idcontrat"], "NumeroPolice": l["numeropolice"], "NumeroQuittance": l["numeroquittance"],
            "Compagnie": l["compagnie"] or "", "IdCompagnie": l["idcompagnie"],
            "PrimeTtc": Decimal(str(l["primettc"] or 0)), "Encaisse": Decimal(str(l["encaisse"] or 0)),
        })
    return [g for g in groupes.values() if len(g["Quittances"]) > 1]


def packages_a_encaisser():
    with connection.cursor() as cursor:
        groupes = quittances_des_packages(cursor)
    resultat = []
    for groupe in groupes:
        restes = [reste_a_encaisser(q["PrimeTtc"], q["Encaisse"]) for q in groupe["Quittances"]]
        if not any(restes):
            continue
        resultat.append({
            **groupe,
            "Quittances": [{**q, "PrimeTtc": _nombre(q["PrimeTtc"]), "Encaisse": _nombre(q["Encaisse"]), "Reste": _nombre(reste)}
                           for q, reste in zip(groupe["Quittances"], restes)],
            "PrimeTtc": _nombre(sum((q["PrimeTtc"] for q in groupe["Quittances"]), ZERO)),
            "Encaisse": _nombre(sum((q["Encaisse"] for q in groupe["Quittances"]), ZERO)),
            "Reste": _nombre(sum(restes, ZERO)),
        })
    return {"Packages": resultat}


# ------------------------------------------------------------------ vues
def _reponse(fonction, *args, code=status.HTTP_200_OK):
    try:
        return Response(fonction(*args), status=code)
    except ErreurMinene as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)


def _lire_devis(id_devis):
    with connection.cursor() as cursor:
        id_sante = devis_sante_du_devis(cursor, id_devis)
        return (lire(cursor, id_sante) if id_sante else None) or {"Minene": False}


def _emettre_devis(id_devis, id_utilisateur):
    with connection.cursor() as cursor:
        id_sante = devis_sante_du_devis(cursor, id_devis)
    if not id_sante:
        raise ErreurMinene(f"Le devis n° {id_devis} n'appartient pas à un package MINENE.")
    return emettre(id_sante, id_utilisateur)


def _lire_contrat(id_contrat):
    with connection.cursor() as cursor:
        id_devis = devis_sante_du_contrat(cursor, id_contrat)
        return (lire(cursor, id_devis) if id_devis else None) or {"Minene": False}


def _emettre_contrat(id_contrat, id_utilisateur):
    with connection.cursor() as cursor:
        id_devis = devis_sante_du_contrat(cursor, id_contrat)
    if not id_devis:
        raise ErreurMinene("Ce contrat n'appartient pas à un package MINENE (affaire nouvelle ou renouvellement de la Santé).")
    return emettre(id_devis, id_utilisateur)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def devis(request, iddevis):
    return _reponse(_lire_devis, iddevis)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def emission_devis(request, iddevis):
    return _reponse(_emettre_devis, iddevis, request.user.id)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def contrat(request, idcontrat):
    return _reponse(_lire_contrat, idcontrat)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def emission_contrat(request, idcontrat):
    return _reponse(_emettre_contrat, idcontrat, request.user.id)


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def caisse(request):
    return _reponse(packages_a_encaisser)


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def encaissement(request, iddevis):
    """Règlement unique du package : mêmes champs et mêmes contrôles que la caisse, le serveur répartit le montant entre les quittances."""
    from sante.oreole import ErreurOreole, ventiler_reglement

    from .views import enregistrer_encaissement

    try:
        montant = Decimal(str(request.data.get("montant_total") or 0))
    except InvalidOperation:
        return Response({"erreur": "Montant du règlement illisible."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            groupes = quittances_des_packages(cursor, iddevis, verrou=True)
            if not groupes:
                raise ErreurMinene("Aucune quittance MINENE émise pour ce devis.")
            quittances = groupes[0]["Quittances"]
            # Un chèque à l'ordre d'une compagnie ne règle que ses quittances : refusé si le package réunit plusieurs compagnies
            if len({q["IdCompagnie"] for q in quittances}) > 1:
                cursor.execute("""SELECT LOWER(TRIM(libellemodepaiement)), UPPER(TRIM(COALESCE(abregereglement, ''))) FROM stdmodeencaissement
                                  WHERE idmodeencaissement = %s""", [int(request.data.get("mode_encaissement") or 0)])
                libelle_mode, abrege_mode = cursor.fetchone() or ("", "")
                if abrege_mode != "ESP" and (str(request.data.get("ordre_reglement") or "").strip().upper() == "COMPAGNIE" or libelle_mode == "a la compagnie"):
                    raise ErreurMinene("Ce package MINENE réunit plusieurs compagnies : il se règle à l'ordre d'OREOLE, qui reverse la part de chacune.")
            donnees = {**request.data, "montant_total": str(montant), "liste_quittance": ventiler_reglement(quittances, montant)}
            return enregistrer_encaissement(request.user, donnees)
    except (ErreurMinene, ErreurOreole) as erreur:
        return Response({"erreur": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
