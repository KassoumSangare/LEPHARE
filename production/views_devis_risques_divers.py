"""
Devis « risques divers » (RC, Multirisque Professionnelle) et Tous Dommages : lecture de tout
ce qui a été saisi sur la ligne du devis, pour le bouton « Modifier ».

sp_creation_devis_risques_divers range les capitaux et l'activité sur stddevisdetail
(ValeurNeuve = dommages corporels, ValeurVenale = intoxication alimentaire,
ValeurAccessoire = dommages matériels, Observation = activité) et, pour la RC,
le taux, l'assiette, les participants, le domaine d'activité, la localisation et la
date de début dans stdcomplementdevisdetailrc. Pour Tous Dommages (sp_creation_devis_tousrisquesinfo),
les mêmes colonnes portent les capitaux matériel informatique / frais de reconstitution /
frais supplémentaires, le taux et le montant de prime sont dans stdcomplementdevisdetaildommage
et le capital cautionnement n'est gardé que sur la garantie « CAUTION ».
Aucune API ne les renvoyait ensemble.
"""

from django.db import connection
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response

from institutionnel.authentication import KnoxOrDemoTokenAuthentication


def _nombre(valeur):
    return float(valeur) if valeur is not None else 0


@api_view(["GET"])
@authentication_classes([KnoxOrDemoTokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def lire_devis_risques_divers(request, iddevis):
    """GET /api/devisrisquesdivers/<iddevis>/"""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT d.idproduit, dd.iddevisdetail, dd.idtarif, dd.idoffre, dd.tauxreduction,
                   dd.valeurneuve, dd.valeurvenale, dd.valeuraccessoire, dd.observation,
                   rc.tauxprime, rc.assietteprime, rc.nombreparticipants, rc.iddomaineactivite,
                   rc.localisation, rc.datedebut, dm.tauxprime, dm.montantprime,
                   (SELECT MAX(g.capital) FROM stddevisdetgarantie g
                      JOIN stdsousgarantie sg ON sg.idsousgarantie = g.idgarantie
                     WHERE g.iddevisdet = dd.iddevisdetail
                       AND UPPER(TRIM(sg.libellesousgarantie)) = 'CAUTION') AS capital_caution
            FROM stddevis d
            JOIN stddevisdetail dd ON dd.iddevis = d.iddevis
            LEFT JOIN stdcomplementdevisdetailrc rc ON rc.iddevisdetail = dd.iddevisdetail
            LEFT JOIN stdcomplementdevisdetaildommage dm ON dm.iddevisdetail = dd.iddevisdetail
            WHERE d.iddevis = %s
            ORDER BY dd.iddevisdetail
            LIMIT 1
            """,
            [iddevis],
        )
        ligne = cursor.fetchone()
    if not ligne:
        return Response(
            {"error": f"Devis {iddevis} introuvable ou sans ligne."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {
            "IdProduit": ligne[0],
            "IdDevisDetail": ligne[1],
            "IdTarif": ligne[2],
            "IdOffre": ligne[3],
            "TauxReduction": _nombre(ligne[4]),
            "CapitalDommageCorporel": _nombre(ligne[5]),
            "CapitalIntoxicationAlimentaire": _nombre(ligne[6]),
            "CapitalDommageMateriel": _nombre(ligne[7]),
            "Activite": ligne[8] or "",
            "TauxPrime": _nombre(ligne[9]),
            "AssiettePrime": _nombre(ligne[10]),
            "NombreParticipants": int(ligne[11] or 0),
            "IdDomaineActivite": ligne[12] or 0,
            "Localisation": ligne[13] or "",
            "DateDebut": ligne[14].isoformat() if ligne[14] else "",
            # Tous Dommages
            "TauxPrimeDommage": _nombre(ligne[15]),
            "MontantPrime": _nombre(ligne[16]),
            "CapitalCautionnement": _nombre(ligne[17]),
        }
    )
