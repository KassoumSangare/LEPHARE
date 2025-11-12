from django.db import models

import uuid
from django.utils import timezone


class DistripayTransaction(models.Model):
    id_transaction = models.UUIDField(
        verbose_name="ID Transaction",
        db_column="idtransaction",
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    montant_initiation = models.IntegerField(
        verbose_name="Montant Initiation", db_column="montantinitiation"
    )
    devise_initiation = models.CharField(
        verbose_name="Devise", max_length=3, db_column="deviseinitiation"
    )
    description_initiation = models.TextField(
        verbose_name="Description Initiation",
        db_column="descriptioninitiation",
        max_length=255,
    )
    code_erreur_initiation = models.CharField(
        verbose_name="Code Erreur Initiation",
        max_length=3,
        db_column="codeerreurinitiation",
        null=True,
        blank=True,
    )
    message_initiation = models.CharField(
        verbose_name="Message Initiation",
        max_length=100,
        db_column="messageinitiation",
        null=True,
        blank=True,
    )
    token_paiement = models.CharField(
        verbose_name="Token de paiement",
        max_length=255,
        db_column="tokenpaiement",
        null=True,
        blank=True,
    )
    url_paiement = models.CharField(
        verbose_name="URL de paiement",
        max_length=2000,
        db_column="urlpaiement",
        null=True,
        blank=True,
    )
    api_response_id_initiation = models.CharField(
        verbose_name="API Response ID Initiation",
        max_length=50,
        db_column="apiresponseidinitiation",
        null=True,
        blank=True,
    )
    code_erreur_transaction = models.CharField(
        verbose_name="Code Transaction",
        max_length=3,
        db_column="codeerreurtransaction",
        null=True,
        blank=True,
    )
    message_transaction = models.CharField(
        verbose_name="Message Transaction",
        db_column="messagetransaction",
        max_length=100,
        null=True,
        blank=True,
    )
    statut = models.CharField(
        verbose_name="Statut Transaction",
        max_length=50,
        blank=True,
        null=True,
        db_column="statut",
    )
    montant_transaction = models.IntegerField(
        verbose_name="Montant Transaction",
        db_column="montanttransaction",
        null=True,
        blank=True,
    )
    devise_transaction = models.CharField(
        verbose_name="Devise Transaction",
        max_length=3,
        db_column="devisetransaction",
        null=True,
        blank=True,
    )
    methode_paiement = models.CharField(
        verbose_name="Methode Paiement",
        max_length=30,
        db_column="methodepaiement",
        null=True,
        blank=True,
    )
    description_transaction = models.CharField(
        verbose_name="Description Transaction",
        max_length=255,
        db_column="descriptiontransaction",
        null=True,
        blank=True,
    )
    metadata = models.CharField(
        verbose_name="Metadata Transaction",
        blank=True,
        max_length=255,
        null=True,
        db_column="metadata",
    )
    id_operateur = models.CharField(
        verbose_name="ID Operateur",
        blank=True,
        max_length=30,
        null=True,
        db_column="idoperateur",
    )
    date_paiement = models.DateTimeField(
        verbose_name="Date Paiement", blank=True, null=True, db_column="datepaiement"
    )
    date_validite_fonds = models.DateTimeField(
        verbose_name="Date Validité Fonds",
        blank=True,
        null=True,
        db_column="datevaliditefonds",
    )
    terminee = models.BooleanField(
        verbose_name="Transaction terminée",
        null=True,
        blank=True,
        db_column="terminee",
        default=False,
    )
    date_creation = models.DateTimeField(
        verbose_name="Date Création",
        null=True,
        db_column="datecreation",
        blank=True,
        default=timezone.now,
    )

    def __str__(self):
        return self.description_initiation

    class Meta:
        db_table = "stddistripaytransaction"
        verbose_name = "Transaction DISTRIPAY"
        verbose_name_plural = "Transactions DISTRIPAY"
