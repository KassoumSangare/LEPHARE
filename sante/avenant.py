"""
Santé : avenant de modification en cours de contrat, sous la même police (CR OREOLE du 26-10-2026 : « passer de FAMILLE
à FAMILLE PLUS suite à l'agrandissement de la famille en cours de contrat »).

- GET  /api/devissante/avenant/<idcontrat>/ : préparation (n'écrit rien) — contrat de la période, composition en vigueur
  (familles, formule, personnes), formules possibles pour chaque famille (même offre commerciale), avenants déjà émis sur
  la période, avenant en cours de saisie.
- POST /api/devissante/avenant/<idcontrat>/ {DateEffet, IdAdherent, IdOffre} : devis d'avenant MOD
  (sp_avenant_creation_devis_initial v6, composition en vigueur recopiée au nom de l'opérateur) puis, pour la famille
  choisie, couverture de la nouvelle formule (créée au besoin avec le collège, la zone et les dates de la sienne) et
  famille rattachée à cette couverture. Le devis s'ouvre dans l'écran Santé (ajout du nouveau membre…), où
  sp_creation_devis_sante v9 le tarife : écart entre la prime annuelle de la nouvelle composition et celle de la
  composition précédente, au prorata des jours restants jusqu'à l'échéance, sans ristourne ; supplément d'accessoire du
  barème. La confirmation (sp_confirmation_devis) émet l'avenant et sa quittance sous la police du contrat.
"""

from datetime import date

from django.db import DatabaseError, connection, transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from production.renouvellement import AUTHENTIFICATION, ErreurRenouvellement, _contrat_base, _date, _iso, _lignes

ID_PRODUIT_SANTE = 5
CODES_PERIODE = ("AFN", "REN", "RPP", "TRP", "MOD")

# Dernier contrat de la période (affaire nouvelle ou renouvellement, puis avenants de modification), même règle que
# sp_creation_devis_sante v9 et sp_avenant_creation_devis_initial v6
SQL_DERNIER_CONTRAT = f"""
    SELECT c.iddevis
    FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant
    WHERE c.numeropolice = %(police)s AND a.codeavenant IN {CODES_PERIODE}
      AND COALESCE(c.idcontratannulation, 0) = 0 AND c.dateeffet::date BETWEEN %(effet)s AND %(expiration)s
      AND c.iddevis <> %(exclu)s {{familles}}
    ORDER BY c.dateeffet DESC, c.idcontrat DESC
    LIMIT 1
"""


def _dernier_devis(cursor, police, effet, expiration, exclu=0, avec_familles=False):
    cursor.execute(
        SQL_DERNIER_CONTRAT.format(familles="AND EXISTS (SELECT 1 FROM stdadherent ad WHERE ad.iddevis = c.iddevis)" if avec_familles else ""),
        {"police": police, "effet": effet, "expiration": expiration, "exclu": exclu},
    )
    ligne = cursor.fetchone()
    return ligne[0] if ligne else None


def _annuelle(cursor, id_devis):
    """Prime nette annuelle d'une composition : garanties du devis (prime annuelle), à défaut l'en-tête (contrat repris
    d'URANUS sans détail)."""
    cursor.execute(
        """SELECT COUNT(*), COALESCE(SUM(g.primeannuelle), 0) FROM stddevisdetgarantie g
           JOIN stddevisdetail dd ON dd.iddevisdetail = g.iddevisdet WHERE dd.iddevis = %s""", [id_devis])
    nombre, total = cursor.fetchone()
    if nombre:
        return float(total)
    cursor.execute("SELECT COALESCE(NULLIF(primeannuelle, 0), primenette, 0) FROM stddevis WHERE iddevis = %s", [id_devis])
    return float((cursor.fetchone() or [0])[0] or 0)


def detail_avenant_modification(cursor, id_devis):
    """Devis d'avenant MOD Santé : police, période du contrat, jours restants, prime annuelle de la nouvelle composition
    (après enregistrement) et de la précédente ; None pour un autre devis."""
    cursor.execute(
        """SELECT d.idoldhist, a.codeavenant, d.dateeffet::date, d.dateexpiration::date, COALESCE(d.primeannuelle, 0), d.idproduit
           FROM stddevis d JOIN stdavenant a ON a.idavenant = d.idavenant WHERE d.iddevis = %s""", [id_devis])
    ligne = cursor.fetchone()
    if not ligne or ligne[1] != "MOD" or ligne[5] != ID_PRODUIT_SANTE:
        return None
    id_base, _, effet, expiration, annuelle, _ = ligne
    cursor.execute(
        """SELECT b.dateeffet::date, b.dateexpiration::date, c.numeropolice, c.idcontrat
           FROM stddevis b LEFT JOIN LATERAL (SELECT numeropolice, idcontrat FROM stdcontrat WHERE iddevis = b.iddevis
                                              ORDER BY idcontrat DESC LIMIT 1) c ON TRUE
           WHERE b.iddevis = %s""", [id_base])
    base = cursor.fetchone()
    if not base or not base[0]:
        return None
    effet_base, expiration_base, police, id_contrat = base
    precedent = _dernier_devis(cursor, police, effet_base, expiration_base, exclu=id_devis) or id_base
    jours = (expiration - effet).days + 1 if effet and expiration else 0
    jours_periode = (expiration_base - effet_base).days + 1
    # Prime annuelle d'avant la modification : référence tarifée à la création de l'avenant, à défaut le dernier contrat
    cursor.execute(
        """SELECT COUNT(*) FILTER (WHERE idgarantie <> 0), COALESCE(SUM(montant) FILTER (WHERE idgarantie <> 0), 0)
           FROM lephare_avenant_sante_reference WHERE iddevis = %s""", [id_devis])
    nombre_reference, total_reference = cursor.fetchone()
    annuelle_precedente = float(total_reference) if nombre_reference else _annuelle(cursor, precedent)
    return {
        "NumeroPolice": police, "IdContrat": id_contrat, "DateEffetContrat": _iso(effet_base),
        "DateExpirationContrat": _iso(expiration_base), "DateEffet": _iso(effet), "DateExpiration": _iso(expiration),
        "Jours": jours, "JoursPeriode": jours_periode,
        "Prorata": round(min(max(jours / jours_periode, 0), 1), 6) if jours_periode > 0 else 0,
        "PrimeAnnuelle": float(annuelle), "PrimeAnnuellePrecedente": annuelle_precedente,
        "EcartAnnuel": float(annuelle) - annuelle_precedente,
    }


SQL_CREATION = "CALL sp_creation_devis_sante(" + ", ".join(["%s"] * 26) + ")"


def _tarifer(cursor, user_id, id_devis, reference=False):
    """sp_creation_devis_sante sur le devis d'avenant avec ses propres données (offre, primes, taux, dates). reference :
    composition d'avant la modification tarifée en primes annuelles (lephare.avenant_reference), gardées par garantie
    (idgarantie 0 : accessoire) dans lephare_avenant_sante_reference."""
    cursor.execute(
        """SELECT d.idintermediaire, d.idcompagnie, d.idproduit, dd.idoffre, d.idavenant, d.idclient, d.idassure,
                  d.dateeffet::date, d.dateexpiration::date, dd.idtarif, COALESCE(c.primefamille, 0), COALESCE(c.primeaffilie, 0),
                  COALESCE(c.primeglobale, 0), COALESCE(c.montantsurprime, 0), COALESCE(c.montantaccessoiremanuel, 0),
                  COALESCE(c.tauxreductioncommerciale, 0), COALESCE(c.idtypecontrat, 1), COALESCE(c.gestionnairesante, ''),
                  COALESCE(d.idduree, 1), COALESCE(d.numeropolicecompagnie, '')
           FROM stddevis d JOIN stddevisdetail dd ON dd.iddevis = d.iddevis
           LEFT JOIN stdcomplementdevisdetailsante c ON c.iddevisdetail = dd.iddevisdetail
           WHERE d.iddevis = %s ORDER BY dd.iddevisdetail LIMIT 1""", [id_devis])
    ligne = cursor.fetchone()
    if not ligne:
        raise ErreurRenouvellement("Composition du contrat sans détail de primes (contrat repris d'URANUS) : avenant impossible.")
    (intermediaire, compagnie, produit, offre, avenant, client, assure, effet, expiration, tarif, famille, affilie, globale,
     surprime, accessoire, taux, type_contrat, gestionnaire, duree, police_compagnie) = ligne
    try:
        # Point de sauvegarde : un refus de la base n'interrompt pas la transaction de la vue
        with transaction.atomic():
            cursor.execute("SELECT set_config('lephare.avenant_reference', %s, true)", ["on" if reference else ""])
            cursor.execute(SQL_CREATION, [
                intermediaire, compagnie, produit, offre, avenant, client, assure, False, False, effet, expiration, date.today(),
                tarif, famille, affilie, globale, surprime, accessoire, taux, type_contrat, gestionnaire, duree, police_compagnie,
                user_id, id_devis, ""])
            cursor.execute("SELECT set_config('lephare.avenant_reference', '', true)")
    except DatabaseError as erreur:
        raise ErreurRenouvellement("Composition du contrat non tarifable : "
                                   + str(erreur).splitlines()[0].split(" : ")[0][:250]) from erreur
    if reference:
        cursor.execute("DELETE FROM lephare_avenant_sante_reference WHERE iddevis = %s", [id_devis])
        cursor.execute(
            """INSERT INTO lephare_avenant_sante_reference (iddevis, idgarantie, montant, datecreation)
               SELECT %(devis)s, g.idgarantie, SUM(g.primeannuelle), NOW()
               FROM stddevisdetgarantie g JOIN stddevisdetail dd ON dd.iddevisdetail = g.iddevisdet
               WHERE dd.iddevis = %(devis)s GROUP BY g.idgarantie
               UNION ALL
               SELECT %(devis)s, 0, COALESCE(accessoire, 0), NOW() FROM stddevis WHERE iddevis = %(devis)s""",
            {"devis": id_devis})


def _base_sante(cursor, id_contrat):
    base = _contrat_base(cursor, id_contrat)
    if base["idproduit"] != ID_PRODUIT_SANTE:
        raise ErreurRenouvellement("Ce contrat n'est pas un contrat Santé.")
    return base


def _familles(cursor, id_devis, date_effet):
    """Familles en vigueur d'un devis (mêmes filtre et ordre que la recopie de sp_avenant_creation_devis_initial v6)."""
    return _lignes(cursor, """
        SELECT a.idadherent AS "IdAdherent", TRIM(COALESCE(a.nom, '') || ' ' || COALESCE(a.prenom, '')) AS "Adherent",
               a.idfiliale AS "IdFiliale", f.idoffresante AS "IdOffre", o.libelleoffre AS "Formule", sf.option AS "Option",
               o.idtarif AS "IdTarif", f.idcollege AS "IdCollege", f.idzonecouverture AS "IdZone",
               (SELECT COUNT(*) FROM stdaffilie x WHERE x.idadherent = a.idadherent AND COALESCE(x.actif, TRUE)
                  AND (x.datesortie IS NULL OR x.datesortie > %(effet)s)) AS "Personnes",
               sf.personnesmax AS "PersonnesMax"
        FROM stdadherent a
        LEFT JOIN stdfiliale f ON f.idfiliale = a.idfiliale
        LEFT JOIN stdoffre o ON o.idoffre = f.idoffresante
        LEFT JOIN lephare_sante_formule sf ON sf.idoffre = f.idoffresante
        WHERE a.iddevis = %(devis)s AND COALESCE(a.actif, TRUE) AND (a.datesortie IS NULL OR a.datesortie > %(effet)s)
        ORDER BY a.idadherent
    """, {"devis": id_devis, "effet": date_effet})


def _formules(cursor, id_tarif):
    """Formules de la même offre commerciale (tarif) : options MINENE avec leur nombre de personnes, ou offres du tarif."""
    return _lignes(cursor, """
        SELECT o.idoffre AS "IdOffre", o.libelleoffre AS "Formule", sf.option AS "Option",
               sf.personnesmin AS "PersonnesMin", sf.personnesmax AS "PersonnesMax"
        FROM stdoffre o LEFT JOIN lephare_sante_formule sf ON sf.idoffre = o.idoffre
        WHERE o.idtarif = %s AND COALESCE(o.actif, TRUE)
        ORDER BY sf.personnesmax NULLS LAST, o.libelleoffre
    """, [id_tarif])


def _avenants(cursor, base):
    return _lignes(cursor, """
        SELECT c.idcontrat AS "IdContrat", c.iddevis AS "IdDevis", c.dateeffet::date AS "DateEffet",
               c.primenette AS "PrimeNette", c.primettc AS "PrimeTtc", d.numerodevis AS "NumeroDevis"
        FROM stdcontrat c JOIN stdavenant a ON a.idavenant = c.idavenant JOIN stddevis d ON d.iddevis = c.iddevis
        WHERE c.numeropolice = %s AND a.codeavenant = 'MOD' AND COALESCE(c.idcontratannulation, 0) = 0
          AND c.dateeffet::date BETWEEN %s AND %s
        ORDER BY c.dateeffet, c.idcontrat
    """, [base["numeropolice"], base["dateeffet"], base["dateexpiration"]])


def _en_cours(cursor, base):
    return _lignes(cursor, """
        SELECT d.iddevis AS "IdDevis", d.numerodevis AS "NumeroDevis", d.dateeffet::date AS "DateEffet", d.primettc AS "PrimeTtc"
        FROM stddevis d JOIN stdavenant a ON a.idavenant = d.idavenant
        WHERE a.codeavenant = 'MOD' AND d.idproduit = %s AND d.idoldhist = %s
          AND NOT COALESCE(d.confirme, FALSE) AND NOT COALESCE(d.archive, FALSE)
        ORDER BY d.iddevis DESC
    """, [ID_PRODUIT_SANTE, base["iddevis"]])


def _numeriques(lignes):
    for ligne in lignes:
        for cle, valeur in list(ligne.items()):
            if isinstance(valeur, date):
                ligne[cle] = _iso(valeur)
            elif valeur is not None and cle.startswith("Prime"):
                ligne[cle] = float(valeur)
    return lignes


@api_view(["GET", "POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def avenant_sante(request, idcontrat):
    try:
        if request.method == "GET":
            with connection.cursor() as cursor:
                base = _base_sante(cursor, idcontrat)
                effet = _date(request.query_params.get("date_effet")) or max(min(date.today(), base["dateexpiration"]), base["dateeffet"])
                composition = _dernier_devis(cursor, base["numeropolice"], base["dateeffet"], base["dateexpiration"], avec_familles=True)
                familles = _familles(cursor, composition, effet) if composition else []
                formules = {}
                for f in familles:
                    if f["IdTarif"] and f["IdTarif"] not in formules:
                        formules[f["IdTarif"]] = _formules(cursor, f["IdTarif"])
                    f["Formules"] = formules.get(f["IdTarif"], [])
                avenants = _numeriques(_avenants(cursor, base))
                return Response({
                    "Contrat": {
                        "IdContrat": base["idcontrat"], "IdDevis": base["iddevis"], "NumeroPolice": base["numeropolice"],
                        "Client": base["client"], "Compagnie": base["compagnie"], "Avenant": base["codeavenant"],
                        "DateEffet": _iso(base["dateeffet"]), "DateExpiration": _iso(base["dateexpiration"]),
                        "PrimeTtc": float(base["primettc"] or 0),
                    },
                    "DateEffet": _iso(effet),
                    "Composition": composition,
                    "Familles": familles,
                    "Avenants": avenants,
                    "EnCours": _numeriques(_en_cours(cursor, base)),
                })

        donnees = request.data
        id_adherent = int(donnees.get("IdAdherent") or 0)
        id_offre = int(donnees.get("IdOffre") or 0)
        with transaction.atomic(), connection.cursor() as cursor:
            base = _base_sante(cursor, idcontrat)
            encours = _en_cours(cursor, base)
            if encours:
                raise ErreurRenouvellement(f"Un avenant est déjà en cours de saisie sur cette police (devis {encours[0]['NumeroDevis']}) : "
                                           "terminez-le ou supprimez-le d'abord.")
            effet = _date(donnees.get("DateEffet"))
            if not effet:
                raise ErreurRenouvellement("Saisissez la date d'effet de l'avenant.")
            if not base["dateeffet"] <= effet <= base["dateexpiration"]:
                raise ErreurRenouvellement(f"La date d'effet doit être comprise dans la période du contrat, du "
                                           f"{base['dateeffet']:%d/%m/%Y} au {base['dateexpiration']:%d/%m/%Y}.")
            dernier = max([a["DateEffet"] for a in _avenants(cursor, base)] or [base["dateeffet"]])
            if effet < dernier:
                raise ErreurRenouvellement(f"Un avenant a déjà pris effet le {dernier:%d/%m/%Y} : la date d'effet ne peut pas être antérieure.")
            composition = _dernier_devis(cursor, base["numeropolice"], base["dateeffet"], base["dateexpiration"], avec_familles=True)
            if not composition:
                raise ErreurRenouvellement("Aucune famille enregistrée pour ce contrat (contrat repris d'URANUS) : saisissez le "
                                           "changement par un nouveau devis.")
            anciennes = _familles(cursor, composition, effet)
            choisie = next((f for f in anciennes if f["IdAdherent"] == id_adherent), None)
            if id_adherent and not choisie:
                raise ErreurRenouvellement("Famille introuvable dans la composition du contrat.")
            if choisie and id_offre and id_offre not in {o["IdOffre"] for o in _formules(cursor, choisie["IdTarif"])}:
                raise ErreurRenouvellement("Formule d'une autre offre commerciale que celle de la famille.")

            cursor.execute("SELECT idavenant FROM stdavenant WHERE codeavenant = 'MOD'")
            id_avenant = cursor.fetchone()[0]
            cursor.execute(
                "CALL sp_avenant_creation_devis_initial(%s, %s, %s, %s, %s, %s, '', 0, '')",
                [request.user.id, base["idcontrat"], id_avenant, date.today(), effet, base["dateexpiration"]],
            )
            id_devis, message = cursor.fetchone()
            if not id_devis:
                raise ErreurRenouvellement(message or "Devis d'avenant refusé par la base.")
            # Référence : composition recopiée tarifée avant toute modification (même calcul, mêmes conditions)
            _tarifer(cursor, request.user.id, id_devis, reference=True)

            formule = ""
            if choisie and id_offre and id_offre != choisie["IdOffre"]:
                # Famille recopiée de même rang ; couverture de la nouvelle formule (même collège et zone) créée au besoin
                cursor.execute("SELECT idadherent FROM stdadherent WHERE iddevis = %s ORDER BY idadherent", [id_devis])
                nouvelles = [l[0] for l in cursor.fetchall()]
                if len(nouvelles) != len(anciennes):
                    raise ErreurRenouvellement("Familles de l'avenant différentes de celles du contrat : changement de formule impossible.")
                nouvelle = dict(zip([f["IdAdherent"] for f in anciennes], nouvelles))[id_adherent]
                cursor.execute(
                    """SELECT idfiliale FROM stdfiliale WHERE iddevis = %s AND idoffresante = %s
                       AND idcollege IS NOT DISTINCT FROM %s AND idzonecouverture IS NOT DISTINCT FROM %s LIMIT 1""",
                    [id_devis, id_offre, choisie["IdCollege"], choisie["IdZone"]])
                existante = cursor.fetchone()
                if existante:
                    id_filiale = existante[0]
                else:
                    cursor.execute(
                        "CALL sp_saisie_filiale_sante(%s, %s, %s, %s, %s, %s, 'S', %s, 0, %s, '')",
                        [choisie["IdCollege"], id_offre, choisie["IdZone"], effet, base["dateexpiration"], date.today(),
                         request.user.id, id_devis])
                    id_filiale = cursor.fetchone()[0]
                cursor.execute("UPDATE stdadherent SET idfiliale = %s WHERE idadherent = %s", [id_filiale, nouvelle])
                cursor.execute("SELECT libelleoffre FROM stdoffre WHERE idoffre = %s", [id_offre])
                formule = (cursor.fetchone() or [""])[0]
            # Montants de l'avenant dès sa création (écart au prorata), jamais une prime annuelle entière
            _tarifer(cursor, request.user.id, id_devis)
            cursor.execute("SELECT numerodevis FROM stddevis WHERE iddevis = %s", [id_devis])
            numero = cursor.fetchone()[0]
        return Response({
            "IdDevis": id_devis, "NumeroDevis": numero, "Module": "sante", "DateEffet": _iso(effet),
            "Famille": choisie["Adherent"] if choisie else "", "Formule": formule, "Message": message,
        }, status=status.HTTP_201_CREATED)
    except (ErreurRenouvellement, ValueError) as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
    except DatabaseError as erreur:
        return Response({"error": str(erreur).splitlines()[0].split(" : ")[0][:300]}, status=status.HTTP_400_BAD_REQUEST)
