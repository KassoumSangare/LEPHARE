from django.db import models
from django.contrib.auth.models import User, BaseUserManager, AbstractBaseUser
import uuid
import datetime
from django.utils import timezone
from django.dispatch import receiver
from django.urls import reverse
from django_rest_passwordreset.signals import reset_password_token_created
from django.core.mail import send_mail
from uranus.settings import EMAIL_HOST_USER

from django_rest_passwordreset.signals import reset_password_token_created
from django.contrib.sites.shortcuts import get_current_site

# Create your models here.


class UranusUserManager(BaseUserManager):
    # def create_user(self, email, date_of_birth, password = None):
    def create_user(self, email, password=None, name=None):
        """
        Créer et enregistrer un utilisateur avec l'adresse email, la date de naissance et
        le mot de passe fournis.
        """
        if not email:
            raise ValueError(
                "Les utilisateurs doivent avoir une adresse e-mail valide."
            )

        user = self.model(
            email=self.normalize_email(email),
            # date_of_birth=date_of_birth,
        )

        user.set_password(password)
        user.set_name(name)
        user.save(using=self._db)
        return user

    # def create_superuser(self, email, date_of_birth, password=None):
    def create_superuser(self, email, password=None):
        """
        Créer et enregistrer un super utilisateur avec l'adresse email, la date de naissance et
        le mot de passe fournis.
        """
        user = self.create_user(
            email,
            password=password,
            # date_of_birth=date_of_birth,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class UranusUser(AbstractBaseUser):
    email = models.EmailField(
        max_length=255,
        unique=True,
    )
    date_of_birth = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    expiry_date = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=110, null=True, blank=True)
    objects = UranusUserManager()

    USERNAME_FIELD = "email"
    # REQUIRED_FIELDS = ['date_of_birth']
    REQUIRED_FIELDS = []

    def set_name(self, name):
        self.name = name

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "A-t-il cette permission?"
        # Réponse la plus simple: Oui, toujours
        return True

    def has_module_perms(self, app_label):
        "A-t-il la permission de voir l'application `app_label`?"
        # Réponse la plus simple: Oui, toujours
        return True

    @property
    def is_staff(self):
        "Est-il un membre du personnel?"
        # Réponse la plus simple: Oui, toujours
        return self.is_admin

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"


class Profile(models.Model):
    utilisateur = models.OneToOneField(
        UranusUser, on_delete=models.CASCADE, null=True, blank=True
    )
    code_demandeur = models.CharField(
        verbose_name="Code Demandeur ASACI", max_length=100
    )
    code_acces = models.CharField(
        verbose_name="Code d'accès ASACI", max_length=100, null=True
    )

    def __str__(self):
        return self.utilisateur.email

    class Meta:
        db_table = "stdprofilutilisateur"
        verbose_name = "Profil d'utilisateur"
        verbose_name_plural = "Profils d'utilisateur"


@receiver(reset_password_token_created)
def password_reset_token_created(
    sender, instance, reset_password_token, *args, **kwargs
):
    # email_plaintext_message = "{}?token={}".format(
    #     reverse("password_reset:reset-password-request"), reset_password_token.key
    # )
    email_plaintext_message = get_current_site(
        instance.request
    ).domain + "/{}?token={}".format(
        instance.request.build_absolute_uri(
            reverse("password_reset:reset-password-confirm")
        ),
        reset_password_token.key,
    )
    try:
        send_mail(
            # title:
            subject="Récupération de mot de passe pour {title}".format(
                title="Uranus App"
            ),
            # message:
            message=email_plaintext_message,
            from_email=EMAIL_HOST_USER,
            # to:
            recipient_list=[reset_password_token.user.email],
            fail_silently=False,
        )
    except Exception as error:
        print(error)


class PasswordChangeCode(models.Model):
    id = models.AutoField(primary_key=True)
    token = models.UUIDField()
    validity = models.DateTimeField()
    user = models.ForeignKey(UranusUser, db_column="user_id", on_delete=models.CASCADE)

    def __str__(self):
        return "Token {} for user {}".format(self.token, self.user)

    class Meta:
        db_table = "stdpasswordchangetoken"


class Derogation(models.Model):
    user_beneficiaire = models.ForeignKey(
        UranusUser,
        db_column="idutilisateurbeneficiaire",
        on_delete=models.CASCADE,
        related_name="derogations",
        verbose_name="Utilisateur bénéficiaire",
    )
    user_habilite = models.ForeignKey(
        UranusUser,
        db_column="idutilisateurhabilite",
        on_delete=models.SET_NULL,
        null=True,
        related_name="derogations_accordees",
        verbose_name="Utilisateur habilité",
    )
    date_creation = models.DateTimeField(
        db_column="datecreation", auto_now_add=True, verbose_name="Date de création"
    )
    date_expiration = models.DateTimeField(
        db_column="dateexpiration", verbose_name="Date d'expiration"
    )
    motif = models.TextField(
        db_column="motif",
        help_text="Motif détaillé de la dérogation.",
        verbose_name="Motif",
    )
    is_used = models.BooleanField(
        db_column="utilisee",
        default=False,
        verbose_name="Utilisée",
        help_text="Indique si la dérogation a déjà été consommée.",
    )

    class Meta:
        db_table = "stdderogation"
        verbose_name = "Dérogation"
        verbose_name_plural = "Dérogations"
        permissions = [
            ("can_accord_derogation", "Peut accorder une dérogation"),
        ]

    def __str__(self):
        return f"Dérogation pour {self.user_beneficiaire.username}"
