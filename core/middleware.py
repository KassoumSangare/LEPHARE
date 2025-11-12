from django.http import HttpResponseForbidden
from decouple import config
import logging

logger = logging.getLogger("django")

ALLOWED_IPS = config("ALLOWED_IPS", default="").split(" ")


def get_client_ip(request):
    """Retrieve the client's IP address."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


class RestrictIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = get_client_ip(request)
        print("Client IP Address:", ip)
        if ip not in ALLOWED_IPS:
            return HttpResponseForbidden(
                "Interdit: Votre adresse IP n'est pas permise!"
            )
        else:
            print("Allowed IPS:", ALLOWED_IPS)
        return self.get_response(request)


class LogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.debug(f"Request: {request.method} {request.get_full_path()}")
        response = self.get_response(request)
        logger.debug(f"Response: {response.status_code} {response.content}")
        return response
