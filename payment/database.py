from customer.models import Client
from .models import DistripayTransaction


def get_customer(customer_id):
    customer_info = dict()
    if customer_id == 0:
        return customer_info
    try:
        customer = Client.objects.get(IdClient=customer_id)
        customer_info["customer_id"] = customer_id
        customer_info["customer_name"] = (
            customer.Prenoms.strip() if customer.Prenoms else ""
        )
        customer_info["customer_surname"] = customer.Nom.strip()
        customer_info["customer_phone_number"] = (
            customer.Mobile.strip() if customer.Mobile else customer.Telephone.strip()
        )
        customer_info["customer_email"] = (
            customer.Email.strip() if customer.Email else ""
        )
        customer_info["customer_address"] = (
            customer.Adresse2 if customer.Adresse2 else ""
        )
    except Client.DoesNotExist as error:
        print(error)
        customer_info = dict()
    return customer_info


def save_transaction_initiaton_response(input_data: dict) -> int:
    transaction_id = None
    res = -1
    if "transaction_id" in input_data:
        if input_data["transaction_id"]:
            transaction_id = input_data["transaction_id"]
    if not transaction_id:
        return res
    try:
        distripay_transaction = DistripayTransaction.objects.get(pk=transaction_id)
        if distripay_transaction:
            if "completed" in input_data:
                distripay_transaction.terminee = bool(input_data["completed"])
            if "code" in input_data:
                distripay_transaction.code_erreur_initiation = input_data["code"]
            if "payment_token" in input_data:
                distripay_transaction.token_paiement = input_data["payment_token"]
            if "payment_url" in input_data:
                distripay_transaction.url_paiement = input_data["payment_url"]
            if "message" in input_data:
                distripay_transaction.message_initiation = input_data["message"]
            if "api_response_id" in input_data:
                distripay_transaction.api_response_id_initiation = input_data[
                    "api_response_id"
                ]
            distripay_transaction.save()
            res = 0
    except DistripayTransaction.DoesNotExist as error:
        print(error)
    except Exception as error:
        print(error)
    finally:
        return res


def save_transaction_info(input_data: dict) -> int:
    transaction_id = None
    exit_code = -1
    if "transaction_id" in input_data:
        if input_data["transaction_id"]:
            transaction_id = input_data["transaction_id"]
    if not transaction_id:
        return exit_code
    try:
        distripay_transaction = DistripayTransaction.objects.get(pk=transaction_id)
        if distripay_transaction:
            if distripay_transaction.terminee:
                raise Exception("Transaction already completed")
            if "message" in input_data:
                new_msg_transaction = str(input_data["message"]).strip()
                old_msg_transaction = str(
                    distripay_transaction.message_transaction
                ).strip()
                if new_msg_transaction == old_msg_transaction:
                    raise Exception("Transaction status has not changed!")
                distripay_transaction.message_transaction = str(
                    input_data["message"]
                ).strip()
            if "completed" in input_data:
                distripay_transaction.terminee = bool(input_data["completed"])
            if "code" in input_data:
                distripay_transaction.code_erreur_transaction = str(
                    input_data["code"]
                ).strip()
            if "status" in input_data:
                distripay_transaction.statut = input_data["status"]
            if "amount" in input_data:
                distripay_transaction.montant_transaction = input_data["amount"]
            if "currency" in input_data:
                distripay_transaction.devise_transaction = input_data["currency"]
            if "payment_method" in input_data:
                distripay_transaction.methode_paiement = input_data["payment_method"]
            if "description" in input_data:
                distripay_transaction.description_transaction = input_data[
                    "description"
                ]
            if "metadata" in input_data:
                distripay_transaction.metadata = input_data["metadata"]
            if "operator_id" in input_data:
                distripay_transaction.id_operateur = input_data["operator_id"]
            if "payment_date" in input_data:
                distripay_transaction.date_paiement = input_data["payment_date"]
            if "fund_availability_date" in input_data:
                distripay_transaction.date_validite_fonds = input_data[
                    "fund_availability_date"
                ]
            distripay_transaction.save()
            exit_code = 0
    except DistripayTransaction.DoesNotExist as error:
        print(error)
    except Exception as error:
        print(error)
    finally:
        return exit_code
