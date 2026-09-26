"""
Devis Individuelle Accidents : enregistrement complet (création ou « Modifier »).

Un seul appel enregistre, dans une transaction (tout ou rien), l'en-tête du devis,
chaque assuré (une ligne de devis par assuré), ses ayants droit, les lignes
retirées et, pour un groupe, les totaux du devis. Ce sont les procédures
d'URANUS : sp_creation_devis_ia (appelée une fois par assuré),
fn_saisie_ayant_droit_ia et sp_finalisation_devis.

En modification, une ligne marquée « Recalculer: false » n'est pas renvoyée à
sp_creation_devis_ia : ses primes, imposées ou non, restent telles quelles.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response

from institutionnel.authentication import KnoxOrDemoTokenAuthentication

from .import_assures import insert_new_assure
from .models import Devis, DevisDetail, DevisDetGarantie

ID_INTERMEDIAIRE = 1
ID_PRODUIT_IA = 2
ID_AVENANT_AFFAIRE_NOUVELLE = 1


class ErreurDevisIa(Exception):
    """Erreur de saisie à afficher telle quelle à l'utilisateur."""


def _date(valeur, champ):
    if isinstance(valeur, date):
        return valeur
    texte = str(valeur or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(texte, fmt).date()
        except ValueError:
            continue
    raise ErreurDevisIa(f"{champ} : date invalide ({valeur!r}).")


def _montant(valeur):
    try:
        return Decimal(str(valeur if valeur not in (None, "") else 0))
    except InvalidOperation:
        raise ErreurDevisIa(f"Montant invalide : {valeur!r}.")


def _code_activite(id_profession):
    """Classe de risque de la profession IA (comme URANUS : code_classe_assure)."""
    from configuration_api.models import ProfessionIa

    profession = ProfessionIa.objects.filter(pk=id_profession).first()
    return (getattr(profession, "code_classe_assure", "") or "01") if profession else "01"


def _libelle_profession(id_profession):
    from configuration_api.models import ProfessionIa

    profession = ProfessionIa.objects.filter(pk=id_profession).first()
    return getattr(profession, "libelle_profession", "") if profession else ""


def _message(exc):
    texte = str(exc)
    return texte.split("\n")[0] if "\n" in texte else texte


def _enregistrer(data):
    assures = data.get("Assures") or []
    if not assures:
        raise ErreurDevisIa("Ajoutez au moins un assuré.")

    flotte = bool(data.get("Flotte"))
    if not flotte and len(assures) > 1:
        raise ErreurDevisIa(
            "Cette catégorie est individuelle : un seul assuré par devis. "
            "Choisissez une catégorie « groupe » pour assurer plusieurs personnes."
        )

    id_devis = int(data.get("IdDevis") or 0)
    id_client = int(data.get("IdClient") or 0)
    if not id_client:
        raise ErreurDevisIa("Choisissez le souscripteur.")

    id_compagnie = int(data["IdCompagnie"])
    id_offre = int(data["IdOffre"])
    id_tarif = int(data["IdTarif"])
    id_duree = int(data.get("IdDuree") or 0)
    date_effet = _date(data.get("DateEffet"), "Date d'effet")
    date_expiration = _date(data.get("DateExpiration"), "Date d'expiration")
    date_emission = _date(data.get("DateEmission"), "Date d'émission")
    taux_reduction = _montant(data.get("TauxReduction"))
    numero_police_compagnie = str(data.get("NumeroPoliceCompagnie") or "")
    numero_police_connexe = str(data.get("NumeroPoliceConnexe") or "")

    id_avenant = ID_AVENANT_AFFAIRE_NOUVELLE
    lignes_retirees = set()
    if id_devis:
        devis = Devis.objects.select_for_update().filter(pk=id_devis).first()
        if not devis:
            raise ErreurDevisIa(f"Devis {id_devis} introuvable.")
        if devis.confirme:
            raise ErreurDevisIa(
                "Ce devis est confirmé (déjà en contrat) : il ne peut plus être modifié."
            )
        if devis.produit_id != ID_PRODUIT_IA:
            raise ErreurDevisIa("Ce devis n'est pas un devis Individuelle Accidents.")
        id_avenant = devis.avenant_id or ID_AVENANT_AFFAIRE_NOUVELLE

        existantes = set(
            DevisDetail.objects.filter(iddevis_id=id_devis).values_list(
                "iddevisdetail", flat=True
            )
        )
        gardees = {int(a.get("IdDevisDetail") or 0) for a in assures} - {0}
        inconnues = gardees - existantes
        if inconnues:
            raise ErreurDevisIa(
                f"Assuré(s) introuvable(s) dans ce devis : lignes {sorted(inconnues)}."
            )
        lignes_retirees = existantes - gardees
        if lignes_retirees:
            DevisDetGarantie.objects.filter(IdDevisDet_id__in=lignes_retirees).delete()
            DevisDetail.objects.filter(iddevisdetail__in=lignes_retirees).delete()

    lignes_calculees = 0
    with connection.cursor() as cursor:
        for rang, assure in enumerate(assures, start=1):
            libelle = f"Assuré n° {rang}"
            id_profession = int(assure.get("IdProfession") or 0)
            date_naissance = _date(assure.get("DateNaissance"), f"{libelle} : date de naissance")

            # Assuré saisi par son nom : fiche client créée comme à l'import URANUS
            id_assure = int(assure.get("IdAssure") or 0)
            if not id_assure:
                nom = str(assure.get("Nom") or "").strip().upper()
                if not nom:
                    raise ErreurDevisIa(f"{libelle} : le nom est obligatoire.")
                client = insert_new_assure(
                    {
                        "Nom": nom,
                        "Prenoms": str(assure.get("Prenoms") or "").strip().upper(),
                        "DateNaissance": date_naissance,
                        "LieuNaissance": str(assure.get("LieuNaissance") or ""),
                        "AdresseGeographique": str(assure.get("AdresseGeographique") or ""),
                        "NumeroMobile": str(assure.get("Telephone") or ""),
                        "Fonction": _libelle_profession(id_profession),
                        "Sexe": str(assure.get("Sexe") or ""),
                    }
                )
                id_assure = client.IdClient
            libelle = f"{libelle} ({assure.get('Nom') or id_assure})"

            # Ayants droit : la liste saisie remplace celle de l'assuré
            ayants = assure.get("AyantsDroit")
            if ayants is not None and assure.get("AyantsDroitModifies", True):
                total = sum(_montant(a.get("Part")) for a in ayants)
                if total > 100:
                    raise ErreurDevisIa(
                        f"{libelle} : le total des parts des ayants droit dépasse 100 % ({total} %)."
                    )
                cursor.execute("DELETE FROM stdayantdroitia WHERE idassure = %s", [id_assure])
                for ayant in ayants:
                    nom_ayant = str(ayant.get("Nom") or "").strip().upper()
                    if not nom_ayant:
                        raise ErreurDevisIa(f"{libelle} : chaque ayant droit doit avoir un nom.")
                    cursor.execute(
                        "SELECT fn_saisie_ayant_droit_ia(%s, %s, %s, %s, %s)",
                        [
                            id_assure,
                            int(ayant.get("IdQualiteAyantDroit") or 0),
                            nom_ayant,
                            str(ayant.get("Prenoms") or "").strip().upper(),
                            _montant(ayant.get("Part")),
                        ],
                    )

            id_devis_detail = int(assure.get("IdDevisDetail") or 0)
            if id_devis and id_devis_detail and not assure.get("Recalculer", True):
                continue  # ligne inchangée : primes conservées

            try:
                cursor.execute(
                    "CALL sp_creation_devis_ia(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
                    (
                        ID_INTERMEDIAIRE,
                        id_compagnie,
                        ID_PRODUIT_IA,
                        id_offre,
                        id_avenant,
                        id_client,
                        id_assure,
                        id_profession,
                        flotte,
                        False,
                        date_effet,
                        date_expiration,
                        date_emission,
                        id_tarif,
                        _montant(assure.get("CapitalDeces")),
                        _montant(assure.get("CapitalIpp")),
                        _montant(assure.get("FraisTraitement")),
                        taux_reduction,
                        _code_activite(id_profession),
                        date_naissance,
                        str(assure.get("AdresseGeographique") or ""),
                        numero_police_connexe,
                        numero_police_compagnie,
                        id_duree,
                        Decimal("0"),
                        Decimal("0"),
                        Decimal("0"),
                        id_devis,
                        id_devis_detail,
                        "",
                    ),
                )
            except Exception as exc:
                raise ErreurDevisIa(f"{libelle} : {_message(exc)}")
            ligne = cursor.fetchone()
            id_devis = ligne[0]
            lignes_calculees += 1

        # Groupe : totaux du devis recalculés si une ligne a changé
        if flotte and (lignes_calculees or lignes_retirees):
            cursor.execute(
                "CALL sp_finalisation_devis(%s, %s, %s, %s, %s);",
                [id_devis, id_client, id_client, True, ""],
            )

    devis = Devis.objects.get(pk=id_devis)
    return {
        "devis_id": devis.iddevis,
        "numero_devis": devis.numerodevis or "",
        "lignes_recalculees": lignes_calculees,
        "lignes_retirees": len(lignes_retirees),
        "totaux": {
            "prime_nette": float(devis.primenette or 0),
            "taxe": float(devis.taxe or 0),
            "accessoire": float(devis.accessoire or 0),
            "prime_ttc": float(devis.primettc or 0),
        },
    }


@api_view(["POST"])
@authentication_classes([KnoxOrDemoTokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def enregistrer_devis_ia_complet(request):
    """
    POST /api/devisia/enregistrement/

    {
      "IdDevis": 0,                      // id du devis à modifier, 0 pour créer
      "IdCompagnie": 1, "IdTarif": 78, "IdOffre": 7, "Flotte": true,
      "IdClient": 2312,                  // souscripteur
      "DateEffet": "2026-01-01", "DateExpiration": "2026-12-31", "DateEmission": "2026-04-29",
      "IdDuree": 4, "TauxReduction": 0, "NumeroPoliceCompagnie": "",
      "Assures": [
        {"IdDevisDetail": 0, "IdAssure": 0, "Nom": "DAN", "Prenoms": "ALAIN",
         "DateNaissance": "1984-02-16", "IdProfession": 12, "AdresseGeographique": "",
         "CapitalDeces": 5000000, "CapitalIpp": 10000000, "FraisTraitement": 0,
         "Recalculer": true, "AyantsDroitModifies": true,
         "AyantsDroit": [{"IdQualiteAyantDroit": 1, "Nom": "...", "Prenoms": "...", "Part": 50}]}
      ]
    }
    """
    try:
        with transaction.atomic():
            resultat = _enregistrer(request.data)
    except ErreurDevisIa as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except KeyError as exc:
        return Response(
            {"error": f"Champ obligatoire manquant : {exc.args[0]}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as exc:
        return Response({"error": _message(exc)}, status=status.HTTP_400_BAD_REQUEST)
    code = status.HTTP_200_OK if int(request.data.get("IdDevis") or 0) else status.HTTP_201_CREATED
    return Response(resultat, status=code)
