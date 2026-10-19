"""
python manage.py semer_demo_institutionnel [--forcer]

Insère les données de démonstration du module institutionnel dans les tables encore vides
(institutionnel/demo.py). Réservé aux environnements de test : refusé quand DEBUG est désactivé,
sauf --forcer. Aucune donnée existante n'est modifiée ni supprimée.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from institutionnel.demo import semer_donnees_demo


class Command(BaseCommand):
    help = "Insère les données de démonstration du module institutionnel (tables vides seulement)."

    def add_arguments(self, parser):
        parser.add_argument("--forcer", action="store_true",
                            help="Autorise l'insertion alors que DEBUG est désactivé (environnement de production).")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["forcer"]:
            raise CommandError("DEBUG désactivé : données de démonstration refusées (--forcer pour passer outre).")
        remplies = semer_donnees_demo()
        if remplies:
            self.stdout.write(self.style.SUCCESS("Données de démonstration insérées : " + ", ".join(remplies)))
        else:
            self.stdout.write("Aucune table vide : rien n'a été inséré.")
