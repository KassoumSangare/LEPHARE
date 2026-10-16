"""
Pièces de production d'un contrat Dommages (compte rendu de la séance LE PHARE du 12-10-2026, ASSURANCE CAUTION :
« Ajouter aux pièces de production la quittance de prime ainsi que le document intitulé « GARANTIE DE LA
SOUMISSION » »). Depuis le 2026-10-15, les documents de la catégorie s'impriment aussi depuis le devis, à la place
de la facture proforma (GET /api/dommages/devis/<iddevis>/documents/).

GET /api/dommages/contrat/<idcontrat>/documents/ : ce qu'impriment la facture de prime (modèle « FACTURE DE PRIME
N° 000034/07/26 » d'OREOLE) et les documents de production de la catégorie (lephare_dommage_document, ex.
« GARANTIE DE SOUMISSION » de NSIA) :
  - Contrat : références (police, facture, acte, période, émission) et primes du contrat ;
  - Devis : le devis Dommages du contrat (compagnie, client, assuré, garanties, risque saisi) ;
  - Valeurs / Types : rubriques du risque saisies (valeur brute et type), pour les champs entre accolades ;
  - ReferenceFacture : référence de la catégorie imprimée sur la facture (« {numero_appel_offres} {beneficiaire} ») ;
  - OrdreCheque : « chèque à l'ordre de » de la compagnie (Compagnies partenaires > Documents imprimés) ;
  - Documents : documents actifs de la catégorie pour la compagnie du contrat dont la condition est remplie
    (ex. type de cautionnement contenant « SOUMISSION »), avec le logo / pied de page de la compagnie à l'impression.
Le remplacement des champs et la mise en page sont faits à l'impression (frontend/src/utils/exportUtils.js).
"""

import unicodedata

from django.db import connection
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from configuration_api.models import CompagnieDocument, DommageDocument

from .views_devis_dommages import AUTHENTIFICATION, ID_PRODUIT_DOMMAGES, _iso, _nombre, lire_dommages, risque_dommages


def _simplifie(texte):
    """Comparaison sans accents ni casse (« Caution de SOUMISSION » contient « soumission »)."""
    texte = unicodedata.normalize("NFD", str(texte or ""))
    return "".join(c for c in texte if unicodedata.category(c) != "Mn").casefold().strip()


def documents_applicables(id_tarif, id_compagnie, valeurs):
    """Documents actifs de la catégorie pour la compagnie, dont la condition sur le risque est remplie. Rubrique de
    la condition non saisie (devis ou contrat repris d'URANUS, sans risque saisi) : document proposé, ses champs
    manquants s'imprimant en pointillés à compléter ; une autre valeur saisie l'écarte."""
    retenus = []
    for d in DommageDocument.objects.filter(IdTarif=id_tarif, Actif=True).order_by("Ordre", "id"):
        if d.IdCompagnie and d.IdCompagnie != id_compagnie:
            continue
        valeur = valeurs.get(d.ConditionChamp) if d.ConditionChamp else None
        if d.ConditionChamp and str(valeur or "").strip() and _simplifie(d.ConditionValeur) not in _simplifie(valeur):
            continue
        retenus.append({
            "Id": d.id, "Titre": d.Titre, "IdCompagnie": d.IdCompagnie, "Corps": d.Corps,
            "Signataire": d.Signataire, "MentionSignature": d.MentionSignature,
        })
    return retenus


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def documents_contrat(request, pk):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.idcontrat, c.iddevis, c.idproduit, c.numeropolice, c.numeropolicecompagnie, c.numerofacture,
                   c.idavenant, c.numeroavenant, c.dateemission, c.dateeffet, c.dateexpiration, c.primenette,
                   c.accessoire, c.taxe, c.primettc, c.idcompagnie
            FROM stdcontrat c WHERE c.idcontrat = %s
            """,
            [pk],
        )
        c = cursor.fetchone()
        if not c:
            return Response({"error": "Contrat introuvable."}, status=status.HTTP_404_NOT_FOUND)
        if c[2] != ID_PRODUIT_DOMMAGES or not c[1]:
            return Response({"error": "Ce contrat n'est pas un contrat Dommages."}, status=status.HTTP_400_BAD_REQUEST)
        devis = lire_dommages(cursor, c[1])
        risque = risque_dommages(cursor, c[1]) if devis else None
    if not devis:
        return Response({"error": "Devis Dommages du contrat introuvable."}, status=status.HTTP_404_NOT_FOUND)

    id_compagnie = c[15] or devis["IdCompagnie"]
    valeurs = (devis.get("Saisie") or {}).get("Risque") or {}
    reglage_cie = CompagnieDocument.objects.filter(IdCompagnie=id_compagnie).first()
    numero_avenant = str(c[7] or "").strip().lstrip("0")
    return Response({
        "Contrat": {
            "IdContrat": c[0],
            "IdDevis": c[1],
            "NumeroPolice": (c[3] or "").strip(),
            "NumeroPoliceCompagnie": (c[4] or "").strip(),
            "NumeroFacture": (c[5] or "").strip(),
            # N° d'acte : 0 pour l'affaire nouvelle (modèle de facture OREOLE), numéro de l'avenant sinon
            "NumeroActe": "0" if c[6] == 1 or not numero_avenant else numero_avenant,
            "DateEmission": _iso(c[8]),
            "DateEffet": _iso(c[9]),
            "DateExpiration": _iso(c[10]),
            "PrimeNette": _nombre(c[11]),
            "Accessoire": _nombre(c[12]),
            "Taxe": _nombre(c[13]),
            "PrimeTtc": _nombre(c[14]),
            "IdCompagnie": id_compagnie,
        },
        "Devis": devis,
        "Valeurs": valeurs,
        "Types": (risque or {}).get("types") or {},
        "ReferenceFacture": (risque or {}).get("reference_facture") or "",
        "OrdreCheque": ((reglage_cie.OrdreCheque if reglage_cie else "") or "").strip() or devis.get("Compagnie") or "",
        "Documents": documents_applicables((risque or {}).get("idtarif"), id_compagnie, valeurs),
    })


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def documents_devis(request, pk):
    """GET /api/dommages/devis/<iddevis>/documents/ : documents de la catégorie imprimés depuis le devis à la place de
    la facture proforma (ex. « GARANTIE DE SOUMISSION » d'une caution de soumission), même réponse que pour un
    contrat. La partie Contrat reprend le devis : dates, primes, et pour le numéro de la garantie le numéro de police
    de la compagnie s'il est saisi, sinon le numéro du devis."""
    with connection.cursor() as cursor:
        devis = lire_dommages(cursor, pk)
        risque = risque_dommages(cursor, pk) if devis else None
    if not devis:
        return Response({"error": "Devis Dommages introuvable."}, status=status.HTTP_404_NOT_FOUND)

    id_compagnie = devis["IdCompagnie"]
    valeurs = (devis.get("Saisie") or {}).get("Risque") or {}
    reglage_cie = CompagnieDocument.objects.filter(IdCompagnie=id_compagnie).first()
    return Response({
        "Contrat": {
            "IdContrat": None,
            "IdDevis": devis["IdDevis"],
            "NumeroPolice": (devis.get("NumeroPoliceCompagnie") or "").strip() or (devis.get("NumeroDevis") or "").strip(),
            "NumeroPoliceCompagnie": (devis.get("NumeroPoliceCompagnie") or "").strip(),
            "NumeroFacture": "",
            "NumeroActe": "0",
            "DateEmission": devis.get("DateEmission"),
            "DateEffet": devis.get("DateEffet"),
            "DateExpiration": devis.get("DateExpiration"),
            "PrimeNette": devis.get("PrimeNette"),
            "Accessoire": devis.get("Accessoire"),
            "Taxe": devis.get("Taxe"),
            "PrimeTtc": devis.get("PrimeTtc"),
            "IdCompagnie": id_compagnie,
        },
        "Devis": devis,
        "Valeurs": valeurs,
        "Types": (risque or {}).get("types") or {},
        "ReferenceFacture": (risque or {}).get("reference_facture") or "",
        "OrdreCheque": ((reglage_cie.OrdreCheque if reglage_cie else "") or "").strip() or devis.get("Compagnie") or "",
        "Documents": documents_applicables((risque or {}).get("idtarif"), id_compagnie, valeurs),
    })
