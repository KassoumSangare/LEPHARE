# commissions/apps.py

from django.apps import AppConfig


class CommissionsConfig(AppConfig):
    """
    Configuration de l'application de gestion des commissions
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'commissions'
    verbose_name = 'Gestion des Commissions'
    
    def ready(self):
        """
        Code à exécuter quand l'application est prête
        """
        # Importer les signals s'il y en a
        # import apps.commissions.signals
        pass