"""Incorporation d'un véhicule dans une police Automobile flotte en cours."""

import logging

from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .renouvellement import AUTHENTIFICATION, ErreurRenouvellement, _contrat_base, _date, _iso, _lignes

MODULE_AUTO = "auto"
logger = logging.getLogger(__name__)


def _verifier_periode(date_effet, debut, expiration, jour):
    if not date_effet:
        raise ErreurRenouvellement("Saisissez la date d'incorporation.")
    if date_effet < jour or date_effet > expiration or date_effet < debut:
        raise ErreurRenouvellement(
            f"La date d'incorporation doit être comprise entre le {max(jour, debut):%d/%m/%Y} "
            f"et le {expiration:%d/%m/%Y}."
        )


def _verifier_periode_devis(code_avenant, effet_stocke, expiration_stockee, effet_demande, expiration_demandee):
    if code_avenant == "INC" and (
        effet_stocke != effet_demande or expiration_stockee != expiration_demandee
    ):
        raise ValueError("La période d'un devis d'incorporation ne peut pas être modifiée.")


def _contrat_flottant(cursor, id_contrat):
    base = _contrat_base(cursor, id_contrat)
    if base["idproduit"] != 1 or not base["flotte"]:
        raise ErreurRenouvellement("L'incorporation est réservée aux contrats Automobile flotte.")
    jour = timezone.localdate()
    if base["dateexpiration"] < jour or base["dateeffet"] > jour:
        raise ErreurRenouvellement("Le contrat doit être en cours de validité pour incorporer un véhicule.")
    return base


def _devis_en_cours(cursor, id_devis_base):
    return _lignes(cursor, """
        SELECT d.iddevis AS "IdDevis", d.numerodevis AS "NumeroDevis",
               d.dateeffet::date AS "DateEffet", d.dateexpiration::date AS "DateExpiration"
        FROM stddevis d
        JOIN stdavenant a ON a.idavenant = d.idavenant
        WHERE a.codeavenant = 'INC' AND d.idoldhist = %s
          AND NOT COALESCE(d.confirme, FALSE) AND NOT COALESCE(d.archive, FALSE)
        ORDER BY d.iddevis DESC
    """, [id_devis_base])


@api_view(["GET", "POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def incorporation(request, pk):
    try:
        if request.method == "GET":
            with connection.cursor() as cursor:
                base = _contrat_flottant(cursor, pk)
                devis = _devis_en_cours(cursor, base["iddevis"])
                for ligne in devis:
                    ligne["DateEffet"] = _iso(ligne["DateEffet"])
                    ligne["DateExpiration"] = _iso(ligne["DateExpiration"])
                return Response({
                    "Contrat": {
                        "IdContrat": base["idcontrat"], "NumeroPolice": base["numeropolice"],
                        "Client": base["client"], "Compagnie": base["compagnie"],
                        "DateEffet": _iso(base["dateeffet"]), "DateExpiration": _iso(base["dateexpiration"]),
                        "Produit": base["produit"],
                    },
                    "DevisEnCours": devis,
                })

        with transaction.atomic(), connection.cursor() as cursor:
            base = _contrat_flottant(cursor, pk)
            en_cours = _devis_en_cours(cursor, base["iddevis"])
            if en_cours:
                raise ErreurRenouvellement(
                    f"Un devis d'incorporation est déjà en cours ({en_cours[0]['NumeroDevis']}) : "
                    "terminez-le ou supprimez-le d'abord."
                )
            effet = _date(request.data.get("DateEffet"))
            _verifier_periode(effet, base["dateeffet"], base["dateexpiration"], timezone.localdate())
            cursor.execute("SELECT idavenant FROM stdavenant WHERE codeavenant = 'INC'")
            avenant = cursor.fetchone()
            if not avenant:
                raise ErreurRenouvellement("Le mouvement d'incorporation n'est pas configuré.")
            cursor.execute(
                "CALL sp_avenant_creation_devis_initial(%s, %s, %s, %s, %s, %s, '', 0, '')",
                [request.user.id, base["idcontrat"], avenant[0], timezone.localdate(), effet, base["dateexpiration"]],
            )
            id_devis, message = cursor.fetchone()
            if not id_devis:
                raise ErreurRenouvellement(message or "Le devis d'incorporation n'a pas pu être créé.")
            cursor.execute(
                """SELECT d.numerodevis, d.dateeffet::date, d.dateexpiration::date, d.flotte, a.codeavenant
                   FROM stddevis d JOIN stdavenant a ON a.idavenant = d.idavenant WHERE d.iddevis = %s""",
                [id_devis],
            )
            devis = cursor.fetchone()
            if not devis or devis[1] != effet or devis[2] != base["dateexpiration"] or not devis[3] or devis[4] != "INC":
                raise ErreurRenouvellement("L'échéance du contrat n'a pas été conservée : création du devis annulée.")
            numero = devis[0]
        return Response({
            "IdDevis": id_devis, "NumeroDevis": numero, "Module": MODULE_AUTO,
            "DateEffet": _iso(effet), "DateExpiration": _iso(base["dateexpiration"]), "Message": message,
        }, status=status.HTTP_201_CREATED)
    except (ErreurRenouvellement, ValueError) as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
    except DatabaseError:
        logger.exception("Erreur SQL lors de la préparation d'une incorporation pour le contrat %s.", pk)
        return Response(
            {"error": "Impossible de préparer l'incorporation pour le moment. Réessayez ou contactez votre administrateur."},
            status=status.HTTP_400_BAD_REQUEST,
        )
