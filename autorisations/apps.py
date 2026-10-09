from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _synchroniser_catalogue(sender, **kwargs):
    """Catalogue des droits aligné sur le code après chaque migration (nouveaux modules compris)."""
    from .catalogue import synchroniser_droits
    from .models import Droit

    try:
        synchroniser_droits(Droit)
    except Exception:  # table pas encore créée (première migration)
        pass


class AutorisationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "autorisations"

    def ready(self):
        from . import garde

        # Contrôle des droits et journal d'audit sur toutes les vues de l'API
        garde.installer()
        post_migrate.connect(_synchroniser_catalogue, sender=self)
