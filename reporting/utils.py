from django.db import connection
import re
from itertools import chain
from datetime import datetime, date
from decimal import Decimal
from .models import BordereauEmissionResultSet, EtatCimaE1Emissions, EtatCimaE2Arrieres


def parse_date(date_val):
    if not date_val:
        return date.today()
    if isinstance(date_val, date) and not isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, datetime):
        return date_val.date()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(date_val).strip(), fmt).date()
        except ValueError:
            pass
    return date.today()


def get_bordereau_recap_emission(input_data):
    msg = ""
    res = BordereauEmissionResultSet.objects.none()
    date_debut = parse_date(input_data.get("date_debut"))
    date_fin = parse_date(input_data.get("date_fin"))
    type_etat = int(input_data.get("type_etat", 1))
    emission_list = []
    try:
        with connection.cursor() as cursor:
            cursor.callproc(
                "fn_bordereau_recap_emission",
                [
                    date_debut,
                    date_fin,
                    type_etat,
                ],
            )
            result = cursor.fetchall()
            for row in result:
                be = BordereauEmissionResultSet(
                    numero_police=row[0] or "",
                    numero_quittance=row[1] or "",
                    numero_avenant=row[2] or "",
                    date_emission=row[3],
                    date_effet=row[4],
                    date_expiration=row[5],
                    prime_nette=row[6] or Decimal("0"),
                    accessoire=row[7] or Decimal("0"),
                    taxe=row[8] or Decimal("0"),
                    prime_ttc=row[9] or Decimal("0"),
                    id_client=row[10] or 0,
                    nom_client=row[11] or "Client",
                    id_produit=row[12] or 0,
                    libelle_produit=row[13] or "Branche",
                    id_compagnie=row[14] or 0,
                    nom_compagnie=row[15] or "Compagnie",
                    accessoire_intermediaire=row[16] or Decimal("0"),
                    commission_intermediaire=row[17] or Decimal("0"),
                    id_offre=row[18] or 0,
                    libelle_offre=row[19] or "",
                    montant_encaissement=row[20] or Decimal("0"),
                    montant_arriere=row[21] or Decimal("0"),
                )
                emission_list.append(be)
    except Exception as error:
        print("fn_bordereau_recap_emission error:", error)
        msg = str(error)
    else:
        if len(emission_list) > 0:
            res = list(chain(res, emission_list))
    return (msg, res)


def get_etat_decisionnel_contenu(code_etat, libelle_etat, date_debut, date_fin, type_etat=None):
    """
    Retourne la liste des enregistrements pour un état décisionnel donné
    en exécutant la fonction PostgreSQL fn_bordereau_recap_emission (ou CIMA).
    """
    d_debut = parse_date(date_debut)
    d_fin = parse_date(date_fin)
    code = (code_etat or "").upper().strip()
    lib = (libelle_etat or "").upper().strip()

    # Si c'est un état CIMA E1 ou E2
    if code in ("E01", "E1") or "CIMA E1" in lib:
        exercice = d_fin.year
        msg, items = get_emissions_encaissements_commissions(exercice)
        if not msg:
            from .serializers import EtatCimaE1Serializer
            return ("", EtatCimaE1Serializer(items, many=True).data)
        return (msg, [])

    if code in ("E02", "E2") or "CIMA E2" in lib:
        exercice = d_fin.year
        msg, items = get_arrieres_encaissements_annulations(exercice)
        if not msg:
            from .serializers import EtatCimaE2Serializer
            return ("", EtatCimaE2Serializer(items, many=True).data)
        return (msg, [])

    # États de type bordereau ou récap (C01-C08, D01-D08)
    if type_etat is None:
        if code.startswith("C") or "RECAP" in lib:
            type_etat = 2
        else:
            type_etat = 1

    try:
        with connection.cursor() as cursor:
            cursor.callproc(
                "fn_bordereau_recap_emission",
                [
                    d_debut,
                    d_fin,
                    int(type_etat),
                ],
            )
            rows = cursor.fetchall()
            dossiers = []
            for r in rows:
                dossiers.append({
                    "numero_police": r[0] or "-",
                    "numero_quittance": r[1] or "-",
                    "numero_avenant": r[2] or "-",
                    "date_emission": r[3].strftime("%Y-%m-%d") if r[3] else None,
                    "date_effet": r[4].strftime("%Y-%m-%d") if r[4] else None,
                    "date_expiration": r[5].strftime("%Y-%m-%d") if r[5] else None,
                    "prime_nette": float(r[6] or 0),
                    "accessoire": float(r[7] or 0),
                    "taxe": float(r[8] or 0),
                    "prime_ttc": float(r[9] or 0),
                    "id_client": r[10],
                    "nom_client": r[11] or "Client Inconnu",
                    "id_produit": r[12],
                    "libelle_produit": r[13] or "Branche",
                    "id_compagnie": r[14],
                    "nom_compagnie": r[15] or "Compagnie",
                    "accessoire_intermediaire": float(r[16] or 0),
                    "commission_intermediaire": float(r[17] or 0),
                    "id_offre": r[18],
                    "libelle_offre": r[19] or "",
                    "montant_encaissement": float(r[20] or 0),
                    "montant_arriere": float(r[21] or 0),
                    # Alias pour compatibilité
                    "numero_devis": r[1] or r[0] or "-",
                    "produit": r[13] or "Branche",
                    "statut": "Émis",
                })
            return ("", dossiers)
    except Exception as error:
        print("Erreur get_etat_decisionnel_contenu Postgres callproc:", error)
        # Fallback ORM si indisponible
        try:
            from production.models import Devis
            qs = Devis.objects.select_related("client", "produit").filter(
                dateemission__date__gte=d_debut, dateemission__date__lte=d_fin
            ).order_by("-dateemission")
            dossiers = []
            for d in qs[:300]:
                nom_client = f"{d.client.Nom} {d.client.Prenoms or ''}".strip() if d.client else (d.nomassure or "Client")
                produit_libelle = getattr(d.produit, "libelle_produit", "") if d.produit else "Automobile"
                dossiers.append({
                    "numero_police": d.numerodevis or f"DEV-{d.iddevis}",
                    "numero_quittance": f"QUI-{d.iddevis}",
                    "numero_avenant": "0000001",
                    "date_emission": d.dateemission.strftime("%Y-%m-%d") if d.dateemission else None,
                    "date_effet": d.dateeffet.strftime("%Y-%m-%d") if d.dateeffet else None,
                    "date_expiration": None,
                    "prime_nette": float(d.primenette or 0),
                    "accessoire": float(d.accessoire or 0),
                    "taxe": float(d.taxe or 0),
                    "prime_ttc": float(d.primettc or 0),
                    "id_client": d.client_id or 1,
                    "nom_client": nom_client,
                    "id_produit": d.produit_id or 1,
                    "libelle_produit": produit_libelle,
                    "id_compagnie": 1,
                    "nom_compagnie": "NSIA ASSURANCES",
                    "accessoire_intermediaire": 0,
                    "commission_intermediaire": float(getattr(d, "commissionintermediaire", 0) or 0),
                    "id_offre": 0,
                    "libelle_offre": "",
                    "montant_encaissement": 0,
                    "montant_arriere": float(d.primettc or 0),
                    "numero_devis": d.numerodevis or f"DEV-{d.iddevis}",
                    "produit": produit_libelle,
                    "statut": "Émis",
                })
            return ("", dossiers)
        except Exception as ex:
            return (str(ex), [])


def get_emissions_encaissements_commissions(exercice_comptable):
    msg = ""
    res = EtatCimaE1Emissions.objects.none()
    emission_list = []
    try:
        with connection.cursor() as cursor:
            cursor.callproc(
                "fn_etat_cima_emis_enca_comm",
                [exercice_comptable],
            )
            rows = cursor.fetchall()
            for row in rows:
                emission = EtatCimaE1Emissions(
                    libelle=row[0],
                    assurance_des_personnes=row[1],
                    automobile_responsabilite_civile=row[2],
                    automobile_autres_risques=row[3],
                    incendie_et_multirisque=row[4],
                    autres_dommages_aux_biens=row[5],
                    responsabilite_civile=row[6],
                    transport_terrestre=row[7],
                    transport_maritime=row[8],
                    corps=row[9],
                    vie=row[10],
                    capitalisation=row[11],
                    ensemble=row[12],
                )
                emission_list.append(emission)
    except Exception as error:
        print("fn_etat_cima_emis_enca_comm error:", error)
        msg = str(error)
    else:
        if len(emission_list) > 0:
            res = list(chain(res, emission_list))
    return (msg, res)


def get_arrieres_encaissements_annulations(exercice_comptable):
    msg = ""
    res = EtatCimaE2Arrieres.objects.none()
    arriere_list = []
    try:
        with connection.cursor() as cursor:
            cursor.callproc(
                "fn_etat_cima_arri_enca_annu",
                [
                    exercice_comptable,
                ],
            )
            rows = cursor.fetchall()
            for row in rows:
                arriere = EtatCimaE2Arrieres(
                    exercice_inventaire=row[0],
                    libelle=row[1],
                    annee_souscription_moins_deux=row[2],
                    annee_souscription_moins_un=row[3],
                    annee_souscription=row[4],
                    total=row[5],
                )
                arriere_list.append(arriere)
    except Exception as error:
        print("fn_etat_cima_arri_enca_annu error:", error)
        msg = str(error)
    else:
        if len(arriere_list) > 0:
            res = list(chain(res, arriere_list))
    return (msg, res)
