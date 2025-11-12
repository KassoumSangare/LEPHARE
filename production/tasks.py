from celery import shared_task
from django.core.management import call_command
from messaging.sms import NerhySMSAPIClient
from .database import get_contract_info_for_sms, get_encaissement_info_for_sms
from collections import defaultdict
from uranus.utils.formatting import convertir_decimal_avec_separateurs
from django.conf import settings


def send_sms(to, message):
    smsapiclient = NerhySMSAPIClient()
    smsapiclient.send_message(to, message)


@shared_task
def envoyer_avis_echeance():
    if not settings.NERHY_SMS_ENABLED:
        return
    call_command(
        "avis_echeance",
    )


@shared_task
def send_sms_enregistrement_contrat(id_contrat):
    if not settings.NERHY_SMS_ENABLED:
        return
    info = get_contract_info_for_sms(id_contrat)
    recipients = []
    if info and info.get("numero_mobile", ""):
        recipients.append("225{}".format(info["numero_mobile"]))
        msg = (
            "Votre police n° "
            + info["numero_police"]
            + " a été enregistrée avec succès.\n"
        )
        msg += (
            "La prime TTC s'élève à "
            + convertir_decimal_avec_separateurs(info["prime_ttc"])
            + " FCFA."
        )
        send_sms(recipients, msg)


@shared_task
def send_sms_encaissement_contrat(id_encaissement):
    if not settings.NERHY_SMS_ENABLED:
        return
    encaissement_info_list = get_encaissement_info_for_sms(id_encaissement)
    if len(encaissement_info_list) == 1:
        enc_info = encaissement_info_list[0]
        if enc_info.get("mobileclient", ""):
            recipients = ["225{}".format(enc_info["mobileclient"])]
            msg = "Encaissement de {} FCFA réalisé le {} avec succès pour votre police n° {}. Solde: {}".format(
                convertir_decimal_avec_separateurs(enc_info["montantencaissement"]),
                enc_info["dateencaissement"],
                enc_info["numeropolice"],
                convertir_decimal_avec_separateurs(enc_info["solde"]),
            )
            send_sms(recipients, msg)
    elif len(encaissement_info_list) > 1:
        grouped_by_idclient = defaultdict(list)
        for dct in encaissement_info_list:
            grouped_by_idclient[dct["idclient"]].append(dct)
        for value in grouped_by_idclient.values():
            if len(value) >= 1:
                recipients = ["225{}".format(value[0]["mobileclient"])]
                msg = "Encaissement du {}:\n".format(value[0]["dateencaissement"])
                for enc_info in value:
                    msg += (
                        "- Police n° {}, montant encaissé: {}, solde: {} FCFA\n".format(
                            enc_info["numeropolice"],
                            convertir_decimal_avec_separateurs(
                                enc_info["montantencaissement"]
                            ),
                            convertir_decimal_avec_separateurs(enc_info["solde"]),
                        )
                    )
                if msg[-1] == "\n":
                    msg = msg[:-1]
                send_sms(recipients, msg)
