"""
Renouvellement d'un contrat depuis LE PHARE (compte rendu de la séance du 12-10-2026) : page de préparation
puis devis de renouvellement, sous la même police (sp_confirmation_devis reprend le numéro de police pour un
avenant REN).

- GET  /api/renouvellement/<idcontrat>/ : préparation (n'écrit rien) — nouvelle période, objets assurés de la
  période en cours (incorporations et modifications comprises, retraits écartés : fn_liste_objets_assures),
  pour l'Automobile valeur vénale recalculée selon l'âge (tableau de dépréciation), objets retirés en cours de
  période, devis de renouvellement déjà ouvert.
- POST /api/renouvellement/<idcontrat>/ {DateEffet, DateExpiration, Exclure: [matricules], ValeursVenales:
  {matricule: valeur}} : sp_avenant_initiation (avenant REN, sp_avenant_renouvellement), puis retrait des
  objets exclus et valeurs vénales choisies.
- Santé : les objets sont les familles (adhérents et leurs affiliés, clé « ADH-<idadherent> »), reconduites avec
  leur couverture par sp_avenant_creation_devis_initial v5 ; une famille décochée est retirée du devis. Contrat
  repris d'URANUS sans adhérent en base : ligne du contrat, les familles se saisissent dans le devis. Le devis s'ouvre ensuite dans son écran de saisie, où il est
  retarifé à l'enregistrement (ajouts, garanties) puis confirmé en contrat.
"""

from datetime import date, datetime, timedelta

from django.db import DatabaseError, connection, transaction
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from institutionnel.authentication import KnoxOrDemoTokenAuthentication

AUTHENTIFICATION = [KnoxOrDemoTokenAuthentication, BasicAuthentication]
CODES_BASE = ("AFN", "REN", "RPP", "TRP")
# Écran de saisie qui rouvre le devis, par produit
MODULES = {1: "auto", 2: "ia", 3: "voyage", 4: "mrh", 5: "sante", 7: "mrp", 8: "rc", 9: "tous-dommages"}
ID_PRODUIT_SANTE = 5
PREFIXE_FAMILLE = "ADH-"


class ErreurRenouvellement(Exception):
    """Renouvellement refusé : message affiché tel quel."""


def _lignes(cursor, sql, params=None):
    cursor.execute(sql, params or [])
    colonnes = [c[0] for c in cursor.description]
    return [dict(zip(colonnes, l)) for l in cursor.fetchall()]


def _date(valeur):
    if not valeur:
        return None
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, date):
        return valeur
    texte = str(valeur).strip()[:10]
    for format_ in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texte, format_).date()
        except ValueError:
            continue
    raise ErreurRenouvellement(f"Date illisible : {valeur}.")


def _iso(valeur):
    return valeur.isoformat() if isinstance(valeur, (date, datetime)) else valeur


def _contrat_base(cursor, id_contrat):
    """Contrat de base de la période en cours (affaire nouvelle ou dernier renouvellement) de la police."""
    lignes = _lignes(cursor, "SELECT numeropolice, COALESCE(idcontratannulation, 0) AS annule FROM stdcontrat WHERE idcontrat = %s", [id_contrat])
    if not lignes:
        raise ErreurRenouvellement("Contrat introuvable.")
    if lignes[0]["annule"]:
        raise ErreurRenouvellement("Contrat annulé ou résilié : il ne peut pas être renouvelé.")
    police = lignes[0]["numeropolice"]
    base = _lignes(cursor, f"""
        SELECT c.idcontrat, c.iddevis, c.numeropolice, c.idproduit, c.idcompagnie, c.idclient, c.idassure, c.flotte,
               c.dateeffet::date AS dateeffet, c.dateexpiration::date AS dateexpiration, c.idduree, c.primettc,
               a.codeavenant, p.libelleproduit AS produit, co.raisonsociale AS compagnie,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client
        FROM stdcontrat AS c
        JOIN stdavenant AS a ON a.idavenant = c.idavenant
        LEFT JOIN stdproduit AS p ON p.idproduit = c.idproduit
        LEFT JOIN stdcompagnie AS co ON co.idcompagnie = c.idcompagnie
        LEFT JOIN stdclient AS cl ON cl.idclient = c.idclient
        WHERE c.numeropolice = %s AND a.codeavenant IN {CODES_BASE} AND COALESCE(c.idcontratannulation, 0) = 0
        ORDER BY c.dateeffet DESC, c.idcontrat DESC
        LIMIT 1
    """, [police])
    if not base:
        raise ErreurRenouvellement("Aucune affaire nouvelle ni renouvellement en vigueur pour cette police.")
    if any(l["annule"] for l in _lignes(cursor, f"""
            SELECT 1 AS annule FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
            WHERE c.numeropolice = %s AND a.codeavenant = 'RES' AND c.dateeffet >= %s""", [police, base[0]["dateeffet"]])):
        raise ErreurRenouvellement("Police résiliée : elle ne peut pas être renouvelée.")
    return base[0]


def _periode(cursor, base, date_effet=None, date_expiration=None):
    """Nouvelle période : lendemain de l'échéance et même durée (fn_get_nouvelle_periode_couverture)."""
    if date_effet:
        effet = _date(date_effet)
        if date_expiration:
            return effet, _date(date_expiration)
        # Même durée que la période qui s'achève
        return effet, effet + (base["dateexpiration"] - base["dateeffet"])
    cursor.execute(
        "SELECT date_effet, date_expiration FROM fn_get_nouvelle_periode_couverture(%s, %s, %s)",
        [base["idduree"], base["dateeffet"], base["dateexpiration"]],
    )
    ligne = cursor.fetchone()
    if ligne and ligne[0]:
        return ligne[0], ligne[1]
    return base["dateexpiration"] + timedelta(days=1), base["dateexpiration"] + (base["dateexpiration"] - base["dateeffet"]) + timedelta(days=1)


def _familles_sante(cursor, iddevis, date_effet):
    """Familles Santé d'un devis reconduites au renouvellement (même filtre que sp_avenant_creation_devis_initial v5 :
    adhérents actifs, non sortis avant la nouvelle date d'effet), dans l'ordre de leur recopie."""
    return _lignes(cursor, """
        SELECT a.idadherent, TRIM(COALESCE(a.nom, '') || ' ' || COALESCE(a.prenom, '')) AS assure,
               a.datenaissance::date AS datenaissance, a.dateadhesion::date AS dateadhesion,
               COALESCE(NULLIF(TRIM(a.matricule), ''), '') AS matricule, f.nom_filiale,
               (SELECT COUNT(*) FROM stdaffilie x WHERE x.idadherent = a.idadherent AND COALESCE(x.actif, TRUE)
                  AND (x.datesortie IS NULL OR x.datesortie > %s)) AS personnes
        FROM stdadherent a LEFT JOIN stdfiliale f ON f.idfiliale = a.idfiliale
        WHERE a.iddevis = %s AND COALESCE(a.actif, TRUE) AND (a.datesortie IS NULL OR a.datesortie > %s)
        ORDER BY a.idadherent
    """, [date_effet, iddevis, date_effet])


def _objets(cursor, base, date_effet):
    """Objets assurés de la période (véhicules, assurés) avec, en Automobile, la valeur vénale du tableau."""
    if base["idproduit"] == ID_PRODUIT_SANTE:
        familles = _familles_sante(cursor, base["iddevis"], date_effet)
        if familles:
            return [{
                "Matricule": f"{PREFIXE_FAMILLE}{f['idadherent']}", "Famille": True, "NumeroAdherent": f["matricule"],
                "Assure": f["assure"], "DateNaissance": _iso(f["datenaissance"]), "Personnes": f["personnes"],
                "Categorie": f["nom_filiale"] or "", "Avenant": base["codeavenant"], "Depuis": _iso(f["dateadhesion"]),
            } for f in familles]
    lignes = _lignes(cursor, """
        SELECT L.matricule, L.idcontrat, L.idcontratdetail, a.codeavenant, c.dateeffet::date AS depuis,
               cd.idtarif, t.codecategorie, t.libelle AS categorie, cd.idoffre, o.libelleoffre AS offre,
               cd.idmarque, m.libellemarque AS marque, cd.modelevehicule, cd.idgenrevehicule, g.libellegenre AS genre,
               cd.idtypevehicule, cd.idcarrosserie, cd.chargeutile, cd.nombreplace, cd.puissancefiscale,
               cd.datemec::date AS datemec, cd.valeurneuve, cd.valeurvenale, cd.primenette, cd.idassure,
               TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS assure, cl.datenaissance::date AS datenaissance
        FROM fn_liste_objets_assures(%s) AS L
        JOIN stdcontratdetail AS cd ON cd.idcontratdetail = L.idcontratdetail
        JOIN stdcontrat AS c ON c.idcontrat = L.idcontrat
        JOIN stdavenant AS a ON a.idavenant = c.idavenant
        LEFT JOIN stdtarif AS t ON t.idtarif = cd.idtarif
        LEFT JOIN stdoffre AS o ON o.idoffre = cd.idoffre
        LEFT JOIN stdmarque AS m ON m.idmarque = cd.idmarque
        LEFT JOIN stdgenrevehicule AS g ON g.idgenre = cd.idgenrevehicule
        -- Assuré : en IA le matricule est le numéro du client assuré (sur 20 chiffres)
        LEFT JOIN stdclient AS cl ON cl.idclient = CASE WHEN c.idproduit = 2 AND L.matricule ~ '^0*[0-9]{1,18}$' THEN LTRIM(L.matricule, '0')::bigint
                                                        ELSE cd.idassure END
    """, [base["numeropolice"]])
    objets = []
    for l in lignes:
        objet = {
            "Matricule": l["matricule"], "Avenant": l["codeavenant"], "Depuis": _iso(l["depuis"]),
            "Categorie": f"{l['codecategorie'] or ''} {l['categorie'] or ''}".strip(), "Offre": l["offre"],
            "PrimeNette": float(l["primenette"] or 0),
        }
        if base["idproduit"] == 1:
            cursor.execute(
                "SELECT classe, age_mois, taux, valeur_venale, explication FROM fn_lephare_depreciation(%s, %s, %s, %s, %s, %s, %s, %s)",
                [l["idgenrevehicule"], l["idtypevehicule"], l["idcarrosserie"], l["codecategorie"], l["chargeutile"] or 0,
                 l["valeurneuve"] or 0, l["datemec"], date_effet],
            )
            dv = cursor.fetchone()
            objet.update({
                "Marque": l["marque"], "Modele": l["modelevehicule"], "Genre": l["genre"], "Places": l["nombreplace"],
                "DateMec": _iso(l["datemec"]), "ValeurNeuve": float(l["valeurneuve"] or 0),
                "ValeurVenaleContrat": float(l["valeurvenale"] or 0),
                "ValeurVenaleTableau": None if dv[3] is None else float(dv[3]),
                "Explication": dv[4], "AgeMois": dv[1], "IdOffre": l["idoffre"], "CodeCategorie": l["codecategorie"],
            })
        else:
            objet.update({"Assure": l["assure"], "DateNaissance": _iso(l["datenaissance"])})
        objets.append(objet)
    return objets


def _retraits(cursor, base):
    return [
        {"Matricule": l["matricule"], "Avenant": l["codeavenant"], "Date": _iso(l["dateeffet"])}
        for l in _lignes(cursor, """
            SELECT DISTINCT TRIM(cd.matricule) AS matricule, a.codeavenant, c.dateeffet::date AS dateeffet
            FROM stdcontratdetail cd JOIN stdcontrat c ON c.idcontrat = cd.idcontrat JOIN stdavenant a ON a.idavenant = c.idavenant
            WHERE c.numeropolice = %s AND a.codeavenant IN ('RET', 'ANL', 'ANP') AND c.dateeffet >= %s
            ORDER BY 3 DESC
        """, [base["numeropolice"], base["dateeffet"]])
    ]


def _devis_en_cours(cursor, base):
    return _lignes(cursor, """
        SELECT d.iddevis AS "IdDevis", d.numerodevis AS "NumeroDevis", d.dateeffet::date AS "DateEffet", d.primettc AS "PrimeTtc"
        FROM stddevis d JOIN stdavenant a ON a.idavenant = d.idavenant
        WHERE a.codeavenant = 'REN' AND NOT COALESCE(d.confirme, FALSE) AND d.idoldhist = %s
        ORDER BY d.iddevis DESC
    """, [base["iddevis"]])


@api_view(["GET", "POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def renouvellement(request, pk):
    try:
        if request.method == "GET":
            with connection.cursor() as cursor:
                base = _contrat_base(cursor, pk)
                effet, expiration = _periode(cursor, base, request.query_params.get("date_effet"), request.query_params.get("date_expiration"))
                encours = _devis_en_cours(cursor, base)
                for d in encours:
                    d["DateEffet"], d["PrimeTtc"] = _iso(d["DateEffet"]), float(d["PrimeTtc"] or 0)
                return Response({
                    "Contrat": {
                        "IdContrat": base["idcontrat"], "IdDevis": base["iddevis"], "NumeroPolice": base["numeropolice"],
                        "IdProduit": base["idproduit"], "Produit": base["produit"], "Compagnie": base["compagnie"],
                        "Client": base["client"], "Flotte": bool(base["flotte"]), "DateEffet": _iso(base["dateeffet"]),
                        "DateExpiration": _iso(base["dateexpiration"]), "PrimeTtc": float(base["primettc"] or 0),
                        "Avenant": base["codeavenant"], "Module": MODULES.get(base["idproduit"]),
                    },
                    "Periode": {"DateEffet": _iso(effet), "DateExpiration": _iso(expiration)},
                    "Objets": _objets(cursor, base, effet),
                    "Retraits": _retraits(cursor, base),
                    "DevisEnCours": encours,
                })

        donnees = request.data
        exclure = {str(m).strip() for m in (donnees.get("Exclure") or []) if str(m).strip()}
        valeurs = {str(k).strip(): v for k, v in (donnees.get("ValeursVenales") or {}).items()}
        with transaction.atomic(), connection.cursor() as cursor:
            base = _contrat_base(cursor, pk)
            effet, expiration = _periode(cursor, base, donnees.get("DateEffet"), donnees.get("DateExpiration"))
            if effet <= base["dateexpiration"]:
                raise ErreurRenouvellement("La nouvelle période doit commencer après l'échéance du contrat.")
            if expiration < effet:
                raise ErreurRenouvellement("La date d'expiration doit suivre la date d'effet.")
            objets = {o["Matricule"] for o in _objets(cursor, base, effet)}
            if objets and exclure >= objets:
                raise ErreurRenouvellement("Tous les objets assurés sont retirés : rien à renouveler.")
            cursor.execute("SELECT idavenant FROM stdavenant WHERE codeavenant = 'REN'")
            id_avenant = cursor.fetchone()[0]
            cursor.execute(
                "CALL sp_avenant_initiation(%s, %s, %s, %s, %s, %s, '', 0, '')",
                [request.user.id, base["idcontrat"], id_avenant, date.today(), effet, expiration],
            )
            id_devis, message = cursor.fetchone()
            if not id_devis:
                raise ErreurRenouvellement(message or "Devis de renouvellement refusé par la base.")
            # Objets retirés à la préparation : ôtés du devis de renouvellement (encore jamais tarifé)
            retires = []
            # Santé : familles décochées retirées (adhérent et affiliés) ; les familles sont recopiées dans l'ordre
            familles_exclues = {m for m in exclure if m.startswith(PREFIXE_FAMILLE)}
            if base["idproduit"] == ID_PRODUIT_SANTE and familles_exclues:
                anciennes = [f["idadherent"] for f in _familles_sante(cursor, base["iddevis"], effet)]
                cursor.execute("SELECT idadherent FROM stdadherent WHERE iddevis = %s ORDER BY idadherent", [id_devis])
                nouvelles = [l[0] for l in cursor.fetchall()]
                if len(anciennes) != len(nouvelles):
                    raise ErreurRenouvellement("Familles du devis de renouvellement différentes de celles du contrat : retrait impossible.")
                correspondance = dict(zip(anciennes, nouvelles))
                for cle in sorted(familles_exclues):
                    try:
                        nouvelle = correspondance[int(cle[len(PREFIXE_FAMILLE):])]
                    except (KeyError, ValueError) as erreur:
                        raise ErreurRenouvellement(f"Famille inconnue : {cle}.") from erreur
                    cursor.execute("DELETE FROM stdaffilie WHERE idadherent = %s", [nouvelle])
                    cursor.execute("DELETE FROM stdadherent WHERE idadherent = %s", [nouvelle])
                    retires.append(cle)
                exclure = exclure - familles_exclues
            for matricule in exclure:
                cursor.execute(
                    "SELECT iddevisdetail FROM stddevisdetail WHERE iddevis = %s AND TRIM(matricule) = %s", [id_devis, matricule]
                )
                for (id_detail,) in cursor.fetchall():
                    for table, colonne in (("stddevisdetgarantie", "iddevisdet"), ("stdcomplementdevisdetailauto", "iddevisdetail"),
                                           ("stdcomplementdevisdetailvoyage", "iddevisdetail"), ("stdcomplementdevisdetaildommage", "iddevisdetail"),
                                           ("stdcomplementdevisdetailsante", "iddevisdetail"), ("stdcomplementdevisdetailrc", "iddevisdetail")):
                        cursor.execute(f"DELETE FROM {table} WHERE {colonne} = %s", [id_detail])
                    cursor.execute("DELETE FROM stddevisdetail WHERE iddevisdetail = %s", [id_detail])
                    retires.append(matricule)
            # Valeurs vénales choisies à la préparation (Automobile)
            for matricule, valeur in valeurs.items():
                try:
                    montant = round(float(str(valeur).replace(" ", "").replace(",", ".")))
                except ValueError as erreur:
                    raise ErreurRenouvellement(f"Valeur vénale illisible pour {matricule}.") from erreur
                if montant < 0:
                    raise ErreurRenouvellement(f"Valeur vénale négative pour {matricule}.")
                cursor.execute(
                    "UPDATE stddevisdetail SET valeurvenale = %s WHERE iddevis = %s AND TRIM(matricule) = %s",
                    [montant, id_devis, matricule],
                )
            # Santé MINENE : sp_creation_devis_sante applique au renouvellement le taux d'ajustement de l'an dernier à la
            # prime de base, puis le taux saisi ; le taux recopié du contrat est remis à 0 pour ne pas l'appliquer deux
            # fois (0 : même tarif que l'an dernier, le producteur saisit l'ajustement de l'année selon le S/P)
            if base["idproduit"] == ID_PRODUIT_SANTE:
                cursor.execute(
                    """
                    UPDATE stdcomplementdevisdetailsante AS cs SET tauxreductioncommerciale = 0
                    FROM stddevisdetail AS dd
                    WHERE dd.iddevisdetail = cs.iddevisdetail AND dd.iddevis = %s AND fn_offre_automatisee_minene_sante(dd.idoffre)
                    """,
                    [id_devis],
                )
            # Automobile : le devis de renouvellement est retarifé au barème (âge, valeurs vénales) ; les primes
            # imposées du contrat ne sont pas reconduites (le producteur peut en imposer de nouvelles)
            if base["idproduit"] == 1:
                cursor.execute("UPDATE stddevis SET primeimposee = FALSE WHERE iddevis = %s", [id_devis])
                cursor.execute("UPDATE stddevisdetail SET primeimposee = FALSE WHERE iddevis = %s", [id_devis])
            cursor.execute("SELECT numerodevis FROM stddevis WHERE iddevis = %s", [id_devis])
            numero = cursor.fetchone()[0]
        return Response({
            "IdDevis": id_devis, "NumeroDevis": numero, "Module": MODULES.get(base["idproduit"]),
            "Retires": sorted(set(retires)), "Message": message,
            "DateEffet": _iso(effet), "DateExpiration": _iso(expiration),
        }, status=status.HTTP_201_CREATED)
    except ErreurRenouvellement as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
    except DatabaseError as erreur:
        # Message de la procédure (« Cet avenant a été déjà renouvellé »…), sans la trace PL/pgSQL
        return Response({"error": str(erreur).splitlines()[0].split(" : ")[0][:300]}, status=status.HTTP_400_BAD_REQUEST)
