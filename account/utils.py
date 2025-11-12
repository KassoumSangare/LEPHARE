from rest_framework_simplejwt.tokens import RefreshToken
import smtplib, ssl
from email.mime.text import MIMEText
from django.db.models import Q
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from django.utils import timezone
import pytz
from uranus.settings import (
    SENDER_EMAIL,
    SENDER_EMAIL_PASSWORD,
    SMTP_HOST,
    SMTP_PORT,
    EMAIL_HOST_USER,
)
from django.core.mail import send_mail
from .models import PasswordChangeCode


utc = pytz.UTC


def custom_send_mail(receiver, subject, message):
    status = 0
    email_message = MIMEMultipart()
    email_message["From"] = SENDER_EMAIL
    email_message["To"] = receiver
    email_message["Subject"] = subject

    email_message.attach(MIMEText(message, "html"))
    email_string = email_message.as_string()

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver, email_string)
            # print("Mail envoyé avec succès. Adresse:", receiver)
            # print("Message envoyé:", email_string)

    except Exception as error:
        print(error)
        status = -1
    finally:
        return status


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def check_temporary_code(user, token):
    validity = datetime.strptime("1973-05-02", "%Y-%m-%d").replace(tzinfo=utc)
    try:
        password_code = PasswordChangeCode.objects.filter(
            Q(user=user) & Q(token=token)
        ).order_by("-validity")
        if password_code.exists():
            validity = password_code[0].validity
    except Exception as error:
        print(error)
        return False
    else:
        return timezone.now() < validity


def send_mail_to_uranus_user(user_email, subject, text_message, html):
    return send_mail(
        subject=subject,
        message=text_message,
        from_email=EMAIL_HOST_USER,
        recipient_list=[user_email],
        fail_silently=False,
        html_message=html,
    )
