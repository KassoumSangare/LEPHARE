from django.db import connection
import re
from itertools import chain
from datetime import datetime
from decimal import Decimal
from .models import BordereauEmissionResultSet, EtatCimaE1Emissions, EtatCimaE2Arrieres


def get_bordereau_recap_emission(input_data):
    msg = ""
    res = BordereauEmissionResultSet.objects.none()
    date_debut = datetime.strptime(input_data["date_debut"], "%d-%m-%Y").date()
    date_fin = datetime.strptime(input_data["date_fin"], "%d-%m-%Y").date()
    type_etat = int(input_data["type_etat"])
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
                    numero_police=row[0],
                    numero_quittance=row[1],
                    numero_avenant=row[2],
                    date_emission=row[3],
                    date_effet=row[4],
                    date_expiration=row[5],
                    prime_nette=row[6],
                    accessoire=row[7],
                    taxe=row[8],
                    prime_ttc=row[9],
                    id_client=row[10],
                    nom_client=row[11],
                    id_produit=row[12],
                    libelle_produit=row[13],
                    id_compagnie=row[14],
                    nom_compagnie=row[15],
                    accessoire_intermediaire=row[16],
                    commission_intermediaire=row[17],
                    id_offre=row[18],
                    libelle_offre=row[19],
                    montant_encaissement=row[20],
                    montant_arriere=row[21],
                )
                emission_list.append(be)
                print(be)
    except Exception as error:
        print(error)
        msg = str(error)
    else:
        if len(emission_list) > 0:
            res = list(chain(res, emission_list))
    finally:
        if connection:
            cursor.close()
            connection.close()

    return (msg, res)


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
                print(emission)
    except Exception as error:
        print(error)
        msg = str(error)
    else:
        if len(emission_list) > 0:
            res = list(chain(res, emission_list))

    finally:
        if connection:
            cursor.close()
            connection.close()
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
                print(arriere)
    except Exception as error:
        print(error)
        msg = str(error)
    else:
        if len(arriere_list) > 0:
            res = list(chain(res, arriere_list))

    finally:
        if connection:
            cursor.close()
            connection.close()
    return (msg, res)
