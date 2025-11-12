import requests
import json
from django.conf import settings
from .exceptions import ArolitecClientTypeError, MissingArgumentError
import logging
import sys

import smpplib.gsm
import smpplib.client
import smpplib.consts


arolitec_send_message_error = {
    "501": "Paramètre « user » manquant",
    "502": "Paramètre « password » manquant",
    "503": "Paramètre « sender » manquant",
    "504": "Paramètre « receiver » manquant",
    "505": "Paramètre « content » manquant",
    "506": "Login/Mot de passe erroné",
    "611": "Paramètre « numericsender » invalide",
}
arolitec_send_message_successfull_response_fields = (
    "success",
    "id",
    "receiver",
    "cost",
    "climsgid",
)
arolitec_send_message_failed_response_fields = ("success", "error")


class NerhySMPPClient(object):
    def __init__(
        self, server=None, port=None, system_id=None, password=None, sender=None
    ):
        if server is None:
            self._server = "app.nerhysms.com"
        else:
            self._server = server

        if port is None:
            self._port = 2775
        else:
            self._port = port

        if system_id is None:
            self._system_id = "522fe39971"
        else:
            self._system_id = system_id

        if password is None:
            self._password = "c3xrpIZ6"
        else:
            self._password = password
        if sender is None:
            self._sender = "IVOIREDEV"
        else:
            self._sender = sender

    def send_message(self, sender, receiver, message):
        logging.basicConfig(level="DEBUG")

        # Two parts, GSM default / UCS2, SMS with UDH
        parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(message)

        client = smpplib.client.Client(self._server, self._port)

        # Print when obtain message_id
        client.set_message_sent_handler(
            lambda pdu: sys.stdout.write(
                "sent {} {}\n".format(pdu.sequence, pdu.message_id)
            )
        )

        client.set_message_received_handler(lambda pdu: self.handle_deliver_sm(pdu))

        client.connect()
        client.bind_transceiver(
            system_id=self._system_id, password=self._password, system_type="smpp"
        )

        for part in parts:
            pdu = client.send_message(
                source_addr_ton=smpplib.consts.SMPP_TON_ALNUM,
                source_addr_npi=smpplib.consts.SMPP_NPI_UNK,
                # Make sure it is a byte string, not unicode:
                source_addr=sender,
                dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
                dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                # Make sure these two params are byte strings, not unicode:
                destination_addr=receiver,
                short_message=part,
                data_coding=encoding_flag,
                esm_class=msg_type_flag,
                registered_delivery=True,
            )
            print(pdu.sequence)

        # t = Thread(target=client.listen)
        # t.start()
        client.listen()

    def handle_deliver_sm(self, pdu):
        sys.stdout.write("delivered {}\n".format(pdu.receipted_message_id))
        return 0  # cmd status for deliver_sm_resp


class NerhySMSAPIClient(object):
    def __init__(self, token=None, sender=None):
        self._api_token = settings.NERHY_SMS_API_TOKEN if token is None else token
        self._sender = settings.NERHY_SMS_DEFAULT_SENDER if sender is None else sender
        self._send_message_url = settings.NERHY_SMS_SEND_MESSAGE_URL
        self._bulk_send_message_url = settings.NERHY_SMS_BULK_SEND_MESSAGE_URL
        self._check_balance_url = settings.NERHY_SMS_CHECK_BALANCE_URL
        self._enabled = settings.NERHY_SMS_ENABLED

    def send_message(
        self,
        to,
        content,
        sender=None,
        dlr=False,
        dlr_url=None,
        dlr_level=None,
        dlr_method=None,
    ):
        if not self._enabled:
            return None
        if sender:
            sender = sender.strip()
        elif self._sender:
            sender = self._sender
        else:
            raise Exception("Sender must be provided when default sender is not set.")

        if not isinstance(to, list):
            raise Exception("Argument 'to' must be a list.")

        if to is None or len(to) == 0:
            raise Exception("A recipient must be provided.")

        if content:
            content = content.strip()
        if dlr:
            if dlr_method is None:
                raise Exception("DLR method must be provided when DLR is set to yes.")
            if dlr_method not in ("GET", "POST"):
                raise Exception("DLR method should be GET or POST.")
            if dlr_url:
                dlr_url = dlr_url.strip()
                if dlr_level is None:
                    dlr_level = 3
            else:
                raise Exception("DLR url must be provided when DLR is set to yes")

        request_headers = self.get_request_headers()

        request_data = dict()

        if len(to) == 1:
            request_data["to"] = to[0]
            request_url = self._send_message_url
        else:
            request_data["to"] = to
            request_url = self._bulk_send_message_url

        request_data["from"] = sender
        if dlr:
            request_data["dlr"] = "yes"
            request_data["dlr-url"] = dlr_url
            request_data["dlr-level"] = dlr_level
            request_data["dlr-method"] = dlr_method

        request_data["content"] = content
        try:
            response = requests.post(
                url=request_url,
                headers=request_headers,
                data=json.dumps(request_data),
            )
            self.save_sms_dispatching_feedback(response)
            # return (response.status_code, response.ok, response.json())
            return response.ok
        except Exception as error:
            print(error)
            return None

    def get_request_headers(self):
        headers = dict()
        headers["Authorization"] = "Bearer " + self._api_token
        headers["Content-Type"] = "application/json"
        return headers

    def check_balance(self):
        request_headers = self.get_request_headers()
        balance = -1
        if not self._enabled:
            balance = 0
        try:
            response = requests.get(
                url=self._check_balance_url, headers=request_headers
            )
            if response:
                balance = float(response.json()["balance"])
        except Exception as error:
            print(error)
            return -1
        else:
            return balance

    def save_sms_dispatching_feedback(self, response):
        pass


class ArolitecSMSAPIClient:
    def __init__(self, user=None, password=None, sender=None, numeric_sender=None):
        self._user = settings.AROLITEC_SMS_USER_ACCOUNT if user is None else user
        self._password = (
            settings.AROLITEC_SMS_USER_PASSWORD if password is None else password
        )
        self._sender = (
            settings.AROLITEC_SMS_DEFAULT_SENDER if sender is None else sender
        )
        self._default_numeric_sender = (
            settings.AROLITEC_SMS_DEFAULT_NUMERIC_SENDER
            if numeric_sender is None
            else numeric_sender
        )
        self._send_message_url = settings.AROLITEC_SMS_SEND_MESSAGE_URL
        self._get_message_status_url = settings.AROLITEC_SMS_GET_STATUS_URL
        self._check_balance_url = settings.AROLITEC_SMS_CHECK_BALANCE_URL
        self._default_charset = settings.AROLITEC_SMS_DEFAULT_CHARSET

    def send_message(
        self,
        receiver,
        content,
        sender=None,
        dlrurl=None,
        charset=None,
        flash=None,
        timetosend=None,
        climsgid=None,
        numericsender=None,
    ):
        if sender:
            sender = sender.strip()
        if receiver:
            receiver = receiver.strip()
        if content:
            content = content.strip()
        if dlrurl:
            dlrurl = dlrurl.strip()
        if charset:
            charset = charset.strip()
        if climsgid:
            climsgid = climsgid.strip()

        missing_arguments = list()
        if sender is None and self._sender is None:
            missing_arguments.append("sender")
        elif sender is None:
            sender = self._sender
        if not receiver:
            missing_arguments.append("receiver")
        if not content:
            missing_arguments.append("content")
        if len(missing_arguments) > 0:
            raise MissingArgumentError(
                "Error occured when sending a message.", missing_arguments
            )
        if charset is None:
            charset = self._default_charset

        if charset not in settings.AROLITEC_SMS_CHARSET_LIST:
            raise ArolitecClientTypeError(
                "Error occured when sending a message.",
                valid_values=settings.AROLITEC_SMS_CHARSET_LIST,
            )

        if numericsender and not numericsender.isdigit():
            raise ArolitecClientTypeError(
                "Error occured when sending a message. Numericsender should be numeric."
            )
        if numericsender is None and self._default_numeric_sender:
            numericsender = self._default_numeric_sender

        request_params = self._initialize_request_params()
        request_params["sender"] = sender
        request_params["receiver"] = receiver
        request_params["content"] = content
        if dlrurl:
            request_params["dlrurl"] = dlrurl
        if charset:
            request_params["charset"] = charset

        if flash == 1:
            request_params["flash"] = flash

        if timetosend:
            request_params["timetosend"] = timetosend

        if climsgid:
            request_params["climsgid"] = climsgid

        if numericsender:
            request_params["numericsender"] = numericsender

        # return json.loads(
        #     requests.get(url=self._send_message_url, params=request_params)
        # )
        response = requests.get(url=self._send_message_url, params=request_params)
        response_dict = response.json()
        print("Type:", type(response_dict))
        print("Attributes and methods:", dir(response_dict))
        print("String representation:", response_dict)
        return response

    def get_message_status(self, id=None):
        if id is None:
            raise MissingArgumentError(
                "Error occured when getting message status", ["id"]
            )

        request_params = self._initialize_request_params()
        request_params["id"] = id

        return json.loads(
            requests.get(url=self._get_message_status_url, params=request_params)
        )

    def check_balance(self):
        request_params = self._initialize_request_params()
        return json.loads(
            requests.get(url=self._check_balance_url, params=request_params)
        )

    def _initialize_request_params(self):
        parameters = dict()
        parameters["user"] = self._user
        parameters["password"] = self._password
        return parameters
