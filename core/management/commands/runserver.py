from django.contrib.staticfiles.management.commands.runserver import Command as RunserverCommand
from django.db import DatabaseError


class Command(RunserverCommand):
    """
    runserver qui démarre même si PostgreSQL est inaccessible (blocage Windows Smart App Control,
    service arrêté) : la vérification des migrations ne fait plus quitter le serveur. Les requêtes
    reprennent seules au retour de la base, et /api/etat-serveur/ renvoie 503 en attendant.
    """

    def check_migrations(self):
        try:
            super().check_migrations()
        except DatabaseError as erreur:
            premiere_ligne = str(erreur).strip().splitlines()[0] if str(erreur).strip() else erreur.__class__.__name__
            self.stderr.write(
                self.style.WARNING(
                    "Base de données inaccessible au démarrage : migrations non vérifiées.\n"
                    f"  {premiere_ligne}\n"
                    "  Le serveur démarre quand même ; les pages fonctionneront au retour de la base."
                )
            )
