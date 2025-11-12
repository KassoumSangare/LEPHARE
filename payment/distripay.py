from django.conf import settings
import requests
import uuid
import json
from .models import DistripayTransaction
from .database import (
    get_customer,
    save_transaction_initiaton_response,
    save_transaction_info,
)


distripay_customer_fields = {
    "customer_id",
    "customer_name",
    "customer_surname",
    "customer_phone_number",
    "customer_email",
    "customer_address",
    "customer_city",
    "customer_country",
    "customer_state",
    "customer_zip_code",
}

distripay_customer_mandatory_fields = {
    "customer_name",
    "customer_surname",
    "customer_phone_number",
    "customer_email",
    "customer_address",
    "customer_city",
    "customer_country",
    "customer_state",
    "customer_zip_code",
}

distripay_error_codes = {
    "00": "SUCCES",
    "201": "CREATED",
    "600": "PAYMENT_FAILED",
    "602": "INSUFFICIENT_BALANCE",
    "604": "OTP_CODE_ERROR",
    "608": "MINIMUM_REQUIRED_FIELDS",
    "606": "INCORRECT_SETTINGS",
    "609": "AUTH_NOT_FOUND",
    "623": "WAITING_CUSTOMER_TO_VALIDATE",
    "625": "ABONNEMENT_OR_TRANSACTIONS_EXPIRED",
    "627": "TRANSACTION_CANCEL",
    "662": "WAITING_CUSTOMER_PAYMENT",
    "663": "WAITING_CUSTOMER_OTP_CODE",
}

distripay_transaction_completed_codes = {
    "00",
    "600",
    "602",
    "604",
    "606",
    "608",
    "609",
    "625",
    "627",
}


def transaction_completed(code: str) -> bool:
    code = code.strip()
    return code in distripay_transaction_completed_codes


class DistripayCustomer(dict):
    def __init__(self, *args, **kwargs):
        # Define the allowed keys
        self.allowed_keys = distripay_customer_fields
        super().__init__(*args, **kwargs)

        if not self.allowed_keys.issubset(self.keys()):
            missing_keys = self.allowed_keys - self.keys()
            raise KeyError(f"Missing keys: {missing_keys}")

        # Remove any keys that are not allowed
        for key in list(self.keys()):
            if key not in self.allowed_keys:
                del self[key]

    def __setitem__(self, key, value):
        if key in self.allowed_keys:
            super().__setitem__(key, value)
        else:
            raise KeyError(f"Key {key} is not allowed.")

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            if key in self.allowed_keys:
                super().__setitem__(key, value)
            else:
                raise KeyError(f"Key {key} is not allowed.")


class FactoryDistripayCustomer(object):
    @staticmethod
    def get_distripay_default_customer():
        return DistripayCustomer(
            {
                "customer_id": 1,
                "customer_name": "FRANCK DELORD",
                "customer_surname": "TOKPA",
                "customer_phone_number": "0505344616",
                "customer_email": "franckdelord@hotmail.com",
                "customer_address": "II PLATEAUX LES PERLES",
                "customer_city": "ABIDJAN",
                "customer_country": "CI",
                "customer_state": "01",
                "customer_zip_code": "35004",
            }
        )

    @staticmethod
    def get_distripay_customer(customer_id: int) -> DistripayCustomer:
        if customer_id == 0:
            return FactoryDistripayCustomer.get_distripay_default_customer()

        customer = get_customer(customer_id)
        if not bool(customer):
            return None
        distripay_customer = FactoryDistripayCustomer.get_distripay_default_customer()
        for key in customer.keys():
            distripay_customer[key] = customer[key]
        return distripay_customer


class DistripayAPIClient:
    def __init__(self, api_key=None, site_id=None):
        if api_key:
            self._api_key = api_key
        else:
            self._api_key = settings.DISTRIPAY_API_KEY
        if site_id:
            self._site_id = site_id
        else:
            self._site_id = settings.DISTRIPAY_SITE_ID
        self._init_trans_url = settings.DISTRIPAY_INIT_TRANS_URL
        self._verify_trans_url = settings.DISTRIPAY_VERIFY_TRANS_URL
        self._payment_enabled = settings.DISTRIPAY_ENABLED
        self._default_currency = settings.DISTRIPAY_DEFAULT_CURRENCY
        self._default_language = settings.DISTRIPAY_DEFAULT_LANGUAGE
        self._default_channel = settings.DISTRIPAY_DEFAULT_CHANNEL

    def _get_request_headers(self):
        headers = dict()
        headers["Accept"] = "*/*"
        headers["Accept-Encoding"] = "gzip, deflate, br"
        headers["Connection"] = "keep-alive"
        headers["Content-Type"] = "application/json"
        return headers

    def _generate_transaction_id(
        self, amount: int, currency: str, description: str
    ) -> uuid.uuid4:
        transaction_id = None
        try:
            trans = DistripayTransaction.objects.create(
                montant_initiation=amount,
                devise_initiation=currency,
                description_initiation=description,
            )
            trans.save()
            transaction_id = trans.id_transaction
        except Exception as error:
            print(error)
        finally:
            return transaction_id

    def _handle_transaction_initiation_response(
        self,
        transaction_id: uuid.uuid4,
        response: requests.models.Response,
    ) -> dict:
        response_json = response.json()
        response_dict = dict()
        response_dict["transaction_id"] = str(transaction_id)
        response_dict["status_code"] = response.status_code
        response_dict["payment_token"] = ""
        response_dict["payment_url"] = ""
        for key, value in response_json.items():
            if key in ("code", "message", "description", "api_response_id"):
                response_dict[key] = value
        if response.status_code == 200 and "data" in response_json:
            if isinstance(response_json["data"], dict):
                for key, value in response_json["data"].items():
                    response_dict[key] = value
        response_dict["completed"] = transaction_completed(
            response_dict.get("code", "")
        )
        save_transaction_initiaton_response(response_dict)
        return {
            key: response_dict[key]
            for key in ("status_code", "code", "payment_url")
            if key in response_dict
        }

    def _handle_transaction_verification_response(
        self, transaction_id: str, response: requests.models.Response
    ) -> dict:
        res_dict = {
            "transaction_id": transaction_id,
            "status_code": response.status_code,
        }
        res_json = response.json()
        if response.status_code == 200:
            for key, value in res_json.items():
                if key in ("code", "message", "api_response_id"):
                    res_dict[key] = value
            if "data" in res_json:
                if res_json["data"]:
                    for key, value in res_json["data"].items():
                        if key in (
                            "status",
                            "amount",
                            "currency",
                            "payment_method",
                            "description",
                            "metadata",
                            "operator_id",
                            "payment_date",
                            "fund_availability_date",
                        ):
                            res_dict[key] = value
        res_dict["completed"] = transaction_completed(res_dict.get("code", ""))
        save_transaction_info(res_dict)
        return {
            key: res_dict[key]
            for key in (
                "transaction_id",
                "status_code",
                "status",
                "code",
                "message",
                "amount",
                "currency",
                "payment_method",
                "operator_id",
                "payment_date",
            )
            if key in res_dict
        }

    def initiate_transaction(
        self,
        amount: int,
        description: str,
        currency: str = "XOF",
        channel: str = "ALL",
        language: str = "fr",
        customer_id: int = 0,
    ) -> dict:

        res = dict()
        request_headers = self._get_request_headers()
        request_data = dict()
        if not amount:
            raise Exception("amount is a mandatory field")

        if not description:
            raise Exception("description is a mandatory field")

        if not currency:
            currency = self._default_currency

        request_data["apiKey"] = self._api_key
        request_data["site_id"] = self._site_id

        transaction_id = self._generate_transaction_id(
            amount=amount, currency=currency, description=description
        )
        if not transaction_id:
            raise Exception("Cannot genrate transaction id")
        request_data["transaction_id"] = str(transaction_id)

        request_data["amount"] = amount
        request_data["currency"] = currency
        request_data["description"] = description

        if not channel:
            request_data["channels"] = self._default_channel
        else:
            request_data["channels"] = channel

        if not language:
            request_data["lang"] = self._default_language
        else:
            request_data["lang"] = language

        customer = FactoryDistripayCustomer.get_distripay_customer(
            customer_id=customer_id
        )
        if not customer:
            raise Exception("Customer info is mandatory")
        for key, value in customer.items():
            request_data[key] = value

        try:
            response = requests.post(
                url=self._init_trans_url,
                headers=request_headers,
                data=json.dumps(request_data),
            )
            if response:
                res = self._handle_transaction_initiation_response(
                    transaction_id, response
                )
                # return (response.status_code, response.ok, response.json())
                if bool(res):
                    res["transaction_id"] = str(transaction_id)
                print("Transaction ID: {}.".format(str(transaction_id)))
                print("Response:", response.json())

        except Exception as error:
            print(error)
        finally:
            return res

    def check_transaction_status(self, transaction_id: str) -> dict:
        if not self._payment_enabled:
            return {}
        request_headers = self._get_request_headers()
        request_data = dict()
        request_data["transaction_id"] = transaction_id
        request_data["site_id"] = self._site_id
        request_data["apiKey"] = self._api_key
        res = dict()
        try:
            response = requests.post(
                url=self._verify_trans_url,
                headers=request_headers,
                data=json.dumps(request_data),
            )
            if response:
                res = self._handle_transaction_verification_response(
                    transaction_id, response
                )
                print("Transaction ID: {}.".format(str(transaction_id)))
                print("Response:", response.json())

        except Exception as error:
            print(error)
        finally:
            return res
