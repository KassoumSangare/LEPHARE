"""
IA et RC chef de famille MINENE rattachées à la police Santé MINENE (compte rendu de la séance du 12-10-2026 :
« leur mode de saisie doit être rattaché à la police santé MINENE »).

GET /api/minene/<idcontrat>/connexes/ : police Santé MINENE du contrat (client, période, nombre d'adhérents)
et devis / contrats IA (offre 66) et RC (offre 67) qui la portent en police connexe. L'écran du contrat Santé
propose d'après cela « Créer l'IA MINENE » / « Créer la RC MINENE », qui ouvrent les écrans IA et RC déjà
renseignés (police connexe, client, dates) ; la base tarife pour chaque adhérent de la police.

GET /api/minene/ia/apercu/?police=<police Santé>&effet=AAAA-MM-JJ : avant l'enregistrement d'une IA MINENE, les
adhérents de la police Santé qui deviendront les assurés (avec leurs ayants droit) et les primes que la base
calculera, par les mêmes fonctions que sp_finalisation_devis (offre 66) : par adhérent, prime forfaitaire
(fn_get_prime_base_minene_ia), accessoire du barème (fn_get_accessoire), taxe sur prime + accessoire
(fn_get_taux_taxe), frais de gestion MINENE (fn_get_frais_gestion_minene) ; total = unitaire × nombre d'adhérents
du contrat Santé (même décompte que sp_finalisation_devis). N'écrit rien.
"""

from datetime import date, datetime

from django.db import connection
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from institutionnel.authentication import KnoxOrDemoTokenAuthentication

AUTHENTIFICATION = [KnoxOrDemoTokenAuthentication, BasicAuthentication]
OFFRES_SANTE_MINENE = (17, 18, 19, 20, 21, 22, 175, 176, 181)
OFFRE_IA, OFFRE_RC = 66, 67
ID_COMPAGNIE_MINENE, ID_PRODUIT_IA = 1, 2


def _lignes(cursor, sql, params):
    cursor.execute(sql, params)
    colonnes = [c[0] for c in cursor.description]
    return [dict(zip(colonnes, l)) for l in cursor.fetchall()]


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def connexes(request, pk):
    with connection.cursor() as cursor:
        contrats = _lignes(cursor, f"""
            SELECT c.idcontrat, c.iddevis, c.numeropolice, c.idproduit, c.idclient, c.dateeffet::date AS dateeffet,
                   c.dateexpiration::date AS dateexpiration,
                   TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client,
                   EXISTS (SELECT 1 FROM stddevisdetail dd WHERE dd.iddevis = c.iddevis AND dd.idoffre IN {OFFRES_SANTE_MINENE})
                   OR EXISTS (SELECT 1 FROM stdfiliale f WHERE f.iddevis = c.iddevis AND f.idoffresante IN {OFFRES_SANTE_MINENE}) AS minene,
                   (SELECT COUNT(*) FROM stdadherent a WHERE a.iddevis = c.iddevis) AS adherents
            FROM stdcontrat c LEFT JOIN stdclient cl ON cl.idclient = c.idclient
            WHERE c.idcontrat = %s
        """, [pk])
        if not contrats:
            return Response({"error": "Contrat introuvable."}, status=status.HTTP_404_NOT_FOUND)
        c = contrats[0]
        if c["idproduit"] != 5 or not c["minene"]:
            return Response({"Minene": False})
        lies = _lignes(cursor, """
            SELECT d.iddevis, d.numerodevis, COALESCE(d.confirme, FALSE) AS confirme, d.primettc,
                   COALESCE((SELECT MAX(dd.idoffre) FROM stddevisdetail dd WHERE dd.iddevis = d.iddevis), d.idoffre) AS idoffre,
                   ct.idcontrat, ct.numeropolice, d.dateeffet::date AS dateeffet
            FROM stddevis d
            LEFT JOIN stdcontrat ct ON ct.iddevis = d.iddevis AND COALESCE(ct.idcontratannulation, 0) = 0
            WHERE TRIM(d.numeropoliceconnexe) = %s AND d.idproduit IN (2, 8)
            ORDER BY d.iddevis DESC
        """, [c["numeropolice"].strip()])

    def resume(offre):
        return [{
            "IdDevis": l["iddevis"], "NumeroDevis": l["numerodevis"], "Confirme": l["confirme"],
            "IdContrat": l["idcontrat"], "NumeroPolice": l["numeropolice"], "PrimeTtc": float(l["primettc"] or 0),
            "DateEffet": l["dateeffet"].isoformat() if l["dateeffet"] else None,
        } for l in lies if l["idoffre"] == offre]

    return Response({
        "Minene": True,
        "NumeroPolice": c["numeropolice"], "IdClient": c["idclient"], "Client": c["client"],
        "DateEffet": c["dateeffet"].isoformat(), "DateExpiration": c["dateexpiration"].isoformat(),
        "Adherents": c["adherents"],
        "IA": resume(OFFRE_IA),
        "RC": resume(OFFRE_RC),
    })


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def apercu_ia(request):
    police = str(request.query_params.get("police") or "").strip()
    if not police:
        return Response({"error": "Numéro de police Santé MINENE à renseigner."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        effet = datetime.strptime(str(request.query_params.get("effet") or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        effet = date.today()
    with connection.cursor() as cursor:
        contrats = _lignes(cursor, """
            SELECT c.iddevis, c.numeropolice, TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')) AS client
            FROM stdcontrat c LEFT JOIN stdclient cl ON cl.idclient = c.idclient
            WHERE c.idproduit = 5 AND TRIM(c.numeropolice) = %s
            ORDER BY c.dateeffet DESC LIMIT 1
        """, [police])
        if not contrats:
            return Response({"error": f"Aucun contrat Santé pour la police {police}."}, status=status.HTTP_404_NOT_FOUND)
        c = contrats[0]
        adherents = _lignes(cursor, """
            SELECT a.idadherent, TRIM(COALESCE(a.nom, '') || ' ' || COALESCE(a.prenom, '')) AS nom,
                   a.datenaissance::date AS datenaissance, COALESCE(a.actif, TRUE) AS actif,
                   (SELECT COUNT(*) FROM stdaffilie x WHERE x.idadherent = a.idadherent AND x.lien <> 'A'
                      AND COALESCE(x.actif, TRUE)) AS ayants
            FROM stdadherent a WHERE a.iddevis = %s ORDER BY a.idadherent
        """, [c["iddevis"]])
        cursor.execute("""
            SELECT fn_get_prime_base_minene_ia(), a.*, fn_get_taux_taxe(%s, %s, %s, %s), fn_get_frais_gestion_minene(%s)
            FROM fn_get_accessoire(fn_get_prime_base_minene_ia(), %s, %s, %s, %s) AS a
        """, [ID_COMPAGNIE_MINENE, ID_PRODUIT_IA, OFFRE_IA, effet, ID_PRODUIT_IA,
              ID_PRODUIT_IA, OFFRE_IA, ID_COMPAGNIE_MINENE, effet])
        ligne = cursor.fetchone()
        prime_unitaire = float(ligne[0] or 0) + float(ligne[1] or 0) + float(ligne[2] or 0) + float(ligne[5] or 0)
        prime_unitaire += round((float(ligne[0] or 0) + float(ligne[1] or 0) + float(ligne[2] or 0)) * float(ligne[4] or 0) / 100)
        # TTC du devis = somme des adhérents, arrondie à l'enregistrement (fn_lephare_arrondi_montant)
        cursor.execute("SELECT fn_lephare_arrondi_montant(%s, %s)", [prime_unitaire * len(adherents), ID_PRODUIT_IA])
        ttc_arrondie = float(cursor.fetchone()[0] or 0)
    prime = float(ligne[0] or 0)
    accessoire = float(ligne[1] or 0) + float(ligne[2] or 0)
    taux = float(ligne[4] or 0)
    frais = float(ligne[5] or 0)
    taxe = round((prime + accessoire) * taux / 100)
    unitaire = {"PrimeNette": prime, "Accessoire": accessoire, "FraisGestion": frais, "Taxe": taxe,
                "PrimeTtc": prime + accessoire + taxe + frais}
    nombre = len(adherents)
    return Response({
        "Police": c["numeropolice"], "Client": c["client"], "Nombre": nombre,
        "Adherents": [{
            "IdAdherent": a["idadherent"], "Nom": a["nom"], "Actif": a["actif"], "AyantsDroit": a["ayants"],
            "DateNaissance": a["datenaissance"].isoformat() if a["datenaissance"] else None,
        } for a in adherents],
        "TauxTaxe": taux, "Unitaire": unitaire,
        "Totaux": {**{k: v * nombre for k, v in unitaire.items()}, "PrimeTtc": ttc_arrondie},
    })
