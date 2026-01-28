from rest_framework.exceptions import APIException

class ServiceError(APIException):
    """Exception personnalisée pour les erreurs métier SQL"""
    status_code = 400
    default_detail = 'Une erreur est survenue lors de l\'opération.'
