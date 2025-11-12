from celery import shared_task
from .utils import send_mail_to_uranus_user


@shared_task
def send_email_to_user(user_email, user_password):
    subject = "Inscription sur l'application Uranus"
    # # Création des versions plain-text et HTML version du message à envoyer
    text_message = (
        "Bonjour,\n"
        + "Votre administrateur Uranus vient de créer pour vous un compteur utilisateur.\n"
        + "Vos parmètres de connexion sont:\n"
        + "Login: "
        + user_email
        + "\n"
        + "Mot de passe: "
        + user_password
        + "\n"
        + "Il vous est conseillé de changer votre mot de passe après votre première connexion."
    )
    html = (
        " <html> "
        + "<body> "
        + "<p>Bonjour,<br> "
        + "Votre administrateur Uranus vient de créer pour vous un compteur utilisateur.<br>"
        + "Vos parmètres de connexion sont:<br>"
        + "<b>Login: "
        + user_email
        + "</b><br>"
        + "<b>Mot de passe: "
        + user_password
        + "</b><br>"
        + "Il vous est conseillé de changer votre mot de passe après votre première connexion."
        + "</p>"
        + "</body>"
        + "</html>"
    )
    return send_mail_to_uranus_user(user_email, subject, text_message, html)


@shared_task
def send_email_password_reset(user_email, user_password):
    subject = "Réinitialisation de mot de passe pour l'application Uranus"
    # # Création des versionsplain-text et HTML version du message à envoyer
    text_message = (
        "Bonjour,\n"
        + "Votre administrateur Uranus vient de réinitialiser le mot de passe de votre compteur utilisateur.\n"
        + "Vos parmètres de connexion sont:\n"
        + "Login: "
        + user_email
        + "\n"
        + "Nouveau mot de passe: "
        + user_password
        + "\n"
        + "Il vous est conseillé de changer votre mot de passe après votre première connexion."
    )
    html = (
        " <html> "
        + "<body> "
        + "<p>Bonjour,<br> "
        + "Votre administrateur Uranus vient de réinitialiser le mot de passe de votre compteur utilisateur.<br>"
        + "Vos parmètres de connexion sont:<br>"
        + "<b>Login: "
        + user_email
        + "</b><br>"
        + "<b>Nouveau mot de passe: "
        + user_password
        + "</b><br>"
        + "Il vous est conseillé de changer votre mot de passe après votre première connexion."
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
