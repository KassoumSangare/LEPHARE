from django.core.management import BaseCommand
from production.database import get_contrat_echeance
from messaging.sms import NerhySMSAPIClient
from django.conf import settings


class Command(BaseCommand):
    help = "Envoyer les avis d'échéance aux clients"

    def handle(self, *args, **options):
        nbre_envoi = 0

        if not settings.URANUS_IN_PRODUCTION or settings.DEBUG:
            self.stdout.write("Uranus n'est pas en production!!!")
            return None

        (msg, contrats) = get_contrat_echeance()
        if msg:
            self.stderr.write(msg)
        elif contrats:
            nbre_total = contrats.count()
            sms_client = NerhySMSAPIClient()
            for contrat in contrats:
                content = (
                    "Votre police n° "
                    + contrat.numero_police
                    + " arrive à échéance le "
                    + contrat.date_expiration
                    + ".\n"
                )
                content += "Prière prendre les dispositions utiles pour la renouveler.\nNous vous remercions de votre fidelité."
                to = [
                    contrat.numero_mobile,
                ]
                ok = sms_client.send_message(to, content)
                nbre_envoi += 1 if ok else 0

            if nbre_envoi <= 1:
                self.stdout.write(
                    f"{nbre_envoi} sur {nbre_total} messages a été envoyé."
                )
            else:
                self.stdout.write(
                    f"{nbre_envoi} sur {nbre_total} messages ont été envoyés."
                )
        else:
            self.stdout.write("Aucun avis d'échéance à envoyer aujourd'hui.")
