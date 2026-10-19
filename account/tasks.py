from celery import shared_task
from .utils import send_mail_to_uranus_user

# Aucun mot de passe n'est envoyé par courriel : il est communiqué par l'administrateur et doit être changé à
# la première connexion. Le second paramètre des deux premières tâches est conservé (ignoré) pour les tâches
# déjà en file d'attente.


@shared_task
def send_email_to_user(user_email, user_password=None):
    subject = "Inscription sur l'application Uranus"
    # # Création des versions plain-text et HTML version du message à envoyer
    text_message = (
        "Bonjour,\n"
        + "Votre administrateur Uranus vient de créer pour vous un compte utilisateur.\n"
        + "Login: "
        + user_email
        + "\n"
        + "Votre mot de passe provisoire vous sera communiqué par votre administrateur ; "
        + "vous devrez le changer à votre première connexion."
    )
    html = (
        " <html> "
        + "<body> "
        + "<p>Bonjour,<br> "
        + "Votre administrateur Uranus vient de créer pour vous un compte utilisateur.<br>"
        + "<b>Login: "
        + user_email
        + "</b><br>"
        + "Votre mot de passe provisoire vous sera communiqué par votre administrateur ; "
        + "vous devrez le changer à votre première connexion."
        + "</p>"
        + "</body>"
        + "</html>"
    )
    return send_mail_to_uranus_user(user_email, subject, text_message, html)


@shared_task
def send_email_password_reset(user_email, user_password=None):
    subject = "Réinitialisation de mot de passe pour l'application Uranus"
    # # Création des versionsplain-text et HTML version du message à envoyer
    text_message = (
        "Bonjour,\n"
        + "Votre administrateur Uranus vient de réinitialiser le mot de passe de votre compte utilisateur.\n"
        + "Login: "
        + user_email
        + "\n"
        + "Vos sessions ouvertes ont été fermées. Votre administrateur vous communiquera le mot de passe provisoire ; "
        + "vous devrez le changer à votre prochaine connexion.\n"
        + "Si vous n'êtes pas à l'origine de cette demande, prévenez votre administrateur immédiatement."
    )
    html = (
        " <html> "
        + "<body> "
        + "<p>Bonjour,<br> "
        + "Votre administrateur Uranus vient de réinitialiser le mot de passe de votre compte utilisateur.<br>"
        + "<b>Login: "
        + user_email
        + "</b><br>"
        + "Vos sessions ouvertes ont été fermées. Votre administrateur vous communiquera le mot de passe provisoire ; "
        + "vous devrez le changer à votre prochaine connexion.<br>"
        + "Si vous n'êtes pas à l'origine de cette demande, prévenez votre administrateur immédiatement."
        + "</p>"
        + "</body>"
        + "</html>"
    )
    return send_mail_to_uranus_user(user_email, subject, text_message, html)


@shared_task
def send_email_password_change(user_email, token):
    subject = "Changement de mot de passe dans l'application Uranus"
    # # Création des versionsplain-text et HTML version du message à envoyer
    text_message = (
        "Bonjour,\n"
        + "Un utilisateur vient de demander le changement de mot de passe pour votre compteur utilisateur.\n"
        + "Utilisez le code suivant pour poursuivre l'opération:\n"
        + str(token)
        + "\n"
        + "Si cette demande n'émane pas de vous, veuillez le notifier à votre administrateur immédiatement."
    )
    html = (
        " <html> "
        + "<body> "
        + "<p>Bonjour,<br> "
        + "Un utilisateur vient de demander le changement de mot de passe pour votre compteur utilisateur.<br>"
        + "Utilisez le code suivant pour poursuivre l'opération:<br>"
        + "<b>"
        + str(token)
        + "</b><br>"
        + "Si cette demande n'émane pas de vous, veuillez le notifier à votre administrateur immédiatement."
        + "</p>"
        + "</body>"
        + "</html>"
    )
    return send_mail_to_uranus_user(user_email, subject, text_message, html)
