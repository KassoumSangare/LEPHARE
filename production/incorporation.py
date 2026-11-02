"""Incorporation d'un véhicule dans une police Automobile flotte en cours.

Le devis d'incorporation (avenant INC) garde l'échéance du contrat principal ; sa date d'effet est la date
d'incorporation. Prime du véhicule : prime annuelle au prorata des jours couverts jusqu'à l'échéance
(jours / 365 ou 366), ou, pour une affaire à tarif forfaitaire, prime annuelle entière sans prorata et prime
nette du fichier Excel reprise telle quelle par l'écran Auto. Le mode est gardé dans lephare_incorporation et
transmis aux moteurs NSIA par le réglage de session lephare.incorporation (fn_calcul_taux_prime_fractionnee v3).
"""

import logging
import re
from contextlib import contextmanager

from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .renouvellement import AUTHENTIFICATION, ErreurRenouvellement, _contrat_base, _date, _iso, _lignes

MODULE_AUTO = "auto"
MODE_PRORATA = "prorata"
MODE_FORFAIT = "forfait"
logger = logging.getLogger(__name__)

# En-tête recopié du contrat par sp_avenant_creation_devis_initial : primes de toute la flotte quand elles étaient
# imposées ; le devis d'incorporation ne porte que les véhicules ajoutés, tarifés à leur enregistrement
SQL_ENTETE_A_ZERO = """
    UPDATE stddevis SET primeannuelle = 0, primenette = 0, accessoire = 0, taxe = 0, fga = 0, cedeao = 0, primettc = 0,
           accessoirecompagnie = 0, accessoiregestionnaire = 0, accessoireintermediaire = 0, commissionaperiteur = 0,
           commissiongestionnaire = 0, commissionintermediaire = 0, primeimposee = false, primeimposeedate = NULL
    WHERE iddevis = %s
"""


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
               d.dateeffet::date AS "DateEffet", d.dateexpiration::date AS "DateExpiration",
               COALESCE(i.forfaitaire, FALSE) AS "Forfaitaire"
        FROM stddevis d
        JOIN stdavenant a ON a.idavenant = d.idavenant
        LEFT JOIN lephare_incorporation i ON i.iddevis = d.iddevis
        WHERE a.codeavenant = 'INC' AND d.idoldhist = %s
          AND NOT COALESCE(d.confirme, FALSE) AND NOT COALESCE(d.archive, FALSE)
        ORDER BY d.iddevis DESC
    """, [id_devis_base])


def _devis_incorporation(cursor, id_devis):
    """Devis d'incorporation Automobile (None pour tout autre devis) : période, mode et police du contrat."""
    lignes = _lignes(cursor, """
        SELECT d.iddevis, d.dateeffet::date AS dateeffet, d.dateexpiration::date AS dateexpiration, d.idoldhist,
               COALESCE(i.forfaitaire, FALSE) AS forfaitaire,
               (SELECT c.numeropolice FROM stdcontrat c WHERE c.iddevis = d.idoldhist ORDER BY c.idcontrat DESC LIMIT 1) AS police,
               (SELECT c.idcontrat FROM stdcontrat c WHERE c.iddevis = d.idoldhist ORDER BY c.idcontrat DESC LIMIT 1) AS idcontrat
        FROM stddevis d
        JOIN stdavenant a ON a.idavenant = d.idavenant
        LEFT JOIN lephare_incorporation i ON i.iddevis = d.iddevis
        WHERE d.iddevis = %s AND a.codeavenant = 'INC' AND d.idproduit = 1
    """, [id_devis])
    return lignes[0] if lignes else None


def mode_incorporation(cursor, id_devis):
    """« prorata » ou « forfait » pour un devis d'incorporation Automobile, None sinon."""
    if not id_devis:
        return None
    devis = _devis_incorporation(cursor, id_devis)
    if not devis:
        return None
    return MODE_FORFAIT if devis["forfaitaire"] else MODE_PRORATA


@contextmanager
def tarification_incorporation(mode):
    """Moteurs Automobile appelés dans ce bloc : prorata au jour (incorporation) ou prime annuelle entière (affaire
    forfaitaire). Réglage de session remis à vide en sortie (les appelants ferment parfois la connexion)."""
    if mode not in (MODE_PRORATA, MODE_FORFAIT):
        yield
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('lephare.incorporation', %s, false)", [mode])
    try:
        yield
    finally:
        if connection.connection is not None:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('lephare.incorporation', '', false)")
            except DatabaseError:
                # Transaction en échec : le réglage disparaît avec elle ou avec la connexion fermée par l'appelant
                logger.warning("Réglage lephare.incorporation non remis à vide.")


def _cle_immatriculation(matricule):
    return re.sub(r"[\s-]+", "", str(matricule or "")).upper()


def controler_vehicule_incorpore(cursor, id_devis, matricule):
    """Un véhicule déjà assuré dans la flotte (période en cours, incorporations comprises) ne s'incorpore pas."""
    devis = _devis_incorporation(cursor, id_devis)
    if not devis or not devis["police"]:
        return
    cle = _cle_immatriculation(matricule)
    cursor.execute("SELECT matricule FROM fn_liste_objets_assures(%s)", [devis["police"]])
    if cle and any(_cle_immatriculation(m) == cle for (m,) in cursor.fetchall()):
        raise ValueError(f"Le véhicule {matricule} est déjà assuré dans la flotte {devis['police']} : il ne peut pas être incorporé.")


def _duree_annuelle(cursor, effet):
    cursor.execute("SELECT fn_get_duree_annuelle_contrat(%s)", [effet])
    return int(cursor.fetchone()[0] or 365)


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

        forfaitaire = request.data.get("Forfaitaire") in (True, "true", "1", 1)
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
            cursor.execute(SQL_ENTETE_A_ZERO, [id_devis])
            cursor.execute(
                "INSERT INTO lephare_incorporation (iddevis, idcontrat, forfaitaire, idutilisateur) VALUES (%s, %s, %s, %s)",
                [id_devis, base["idcontrat"], forfaitaire, request.user.id],
            )
        return Response({
            "IdDevis": id_devis, "NumeroDevis": numero, "Module": MODULE_AUTO,
            "DateEffet": _iso(effet), "DateExpiration": _iso(base["dateexpiration"]), "Forfaitaire": forfaitaire,
            "Message": message,
        }, status=status.HTTP_201_CREATED)
    except (ErreurRenouvellement, ValueError) as erreur:
        return Response({"error": str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
    except DatabaseError:
        logger.exception("Erreur SQL lors de la préparation d'une incorporation pour le contrat %s.", pk)
        return Response(
            {"error": "Impossible de préparer l'incorporation pour le moment. Réessayez ou contactez votre administrateur."},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def devis_incorporation(request, iddevis):
    """GET /api/incorporation/devis/<iddevis>/ : période et mode de tarification d'un devis d'incorporation, pour
    l'écran Auto ({"Incorporation": false} pour tout autre devis)."""
    with connection.cursor() as cursor:
        devis = _devis_incorporation(cursor, iddevis)
        if not devis:
            return Response({"Incorporation": False})
        jours = (devis["dateexpiration"] - devis["dateeffet"]).days + 1
        annee = _duree_annuelle(cursor, devis["dateeffet"])
    return Response({
        "Incorporation": True, "IdDevis": devis["iddevis"], "IdContrat": devis["idcontrat"], "NumeroPolice": devis["police"] or "",
        "DateEffet": _iso(devis["dateeffet"]), "DateExpiration": _iso(devis["dateexpiration"]),
        "Forfaitaire": devis["forfaitaire"], "Mode": MODE_FORFAIT if devis["forfaitaire"] else MODE_PRORATA,
        "JoursCouverts": jours, "JoursAnnee": annee, "Prorata": round(min(1, jours / annee), 6),
    })
