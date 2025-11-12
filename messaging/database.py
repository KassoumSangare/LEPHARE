from .models import (
    ArolitecSMSDispatching,
    ArolitecSMSResponse,
    ArolitecSMSAck,
    ArolitecSMSMo,
)


def create_arolitec_sms_dispatching(
    content, receiver, charset, time_to_send, dispatching_status=None
):
    id = "0"
    try:
        sms_dispatching = ArolitecSMSDispatching(
            content=content,
            receiver=receiver,
            charset=charset,
            time_to_send=time_to_send,
            dispatching_status=dispatching_status,
        )
        sms_dispatching.save()
        id = sms_dispatching.climsgid
    except Exception as error:
        print(error)
        return "-1"
    return id


def set_arolitec_sms_dispatching_status(
    climsgid, dispatching_status, dispatching_error=None
):
    try:
        sms_dispatching = ArolitecSMSDispatching.objects.get(pk=climsgid)
        sms_dispatching.dispatching_status = dispatching_status
        sms_dispatching.dispatching_error = dispatching_error
        sms_dispatching.save()
    except ArolitecSMSDispatching.DoesNotExist:
        print("SMS Dispatching with", climsgid, "does not exist.")
        return -1
    except Exception as error:
        print(error)
        return -1
    else:
        return climsgid


def get_arolitec_sms_dispatching(climsgid=None):
    try:
        if climsgid is None:
            return ArolitecSMSDispatching.objects.all().order_by("-date_created")[:1000]
        else:
            return ArolitecSMSDispatching.objects.get(pk=climsgid)
    except Exception as error:
        print(error)
        return None


def create_arolitec_sms_response(
    msgid, receiver, cost, success=None, dispatching_error=None, climsgid=None
):
    id = 0
    try:
        if climsgid is not None:
            sms_dispatching = ArolitecSMSDispatching.objects.get(pk=climsgid)
            sms_dispatching.dispatching_status = "0" if success is None else "1"
            sms_dispatching.dispatching_error = (
                "" if dispatching_error is None else dispatching_error
            )
            dispatching_success = True if success == "1" else False
            sms_response = ArolitecSMSResponse(
                msgid=msgid,
                receiver=receiver,
                cost=cost,
                success=dispatching_success,
                error=dispatching_error,
                climsgid=sms_dispatching,
            )
            sms_response.save()
            id = sms_response.response_id
    except ArolitecSMSDispatching.DoesNotExist:
        print("SMS Dispatching # ", climsgid, "does not exist.")
        return -1
    except Exception as error:
        print(error)
        return -1
    else:
        return id


def get_arolitec_sms_response(msgid=None):
    try:
        if msgid is None:
            return ArolitecSMSResponse.objects.all().order_by("-date_created")[:1000]
        else:
            return ArolitecSMSResponse.objects.get(pk=msgid)
    except ArolitecSMSResponse.DoesNotExist:
        print("Message Response #", msgid, "does not exist.")
        return None
    except Exception as error:
        print(error)
        return None


def create_arolitec_sms_ack():
    pass
