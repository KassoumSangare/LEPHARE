"""
Modèles Django pour la gestion des commissions
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from configuration_api.models import Compagnie
from production.models import Contrat, Quittance, Encaissement, DetailEncaissement, ReversementCompagnie, DetailReversement

User = get_user_model()

class PaiementCommission(models.Model):
    """
    Représente un paiement de commission global reçu de la compagnie d'assurance
    """
    STATUS_CHOICES = [
        ('EN_ATTENTE', 'En attente de traitement'),
        ('TRAITE', 'Traité'),
        ('VALIDE', 'Validé'),
    ]
    
    reference = models.CharField(
        max_length=50, 
        unique=True,
        db_index=True,
        help_text="Référence unique du paiement"
    )
    compagnie = models.ForeignKey(
        Compagnie, 
        on_delete=models.PROTECT,
        related_name='paiements_commission',
        help_text="Compagnie d'assurance qui effectue le paiement"
    )
    date_paiement = models.DateField(
        db_index=True,
        help_text="Date du paiement de la commission"
    )
    montant_total = models.DecimalField(
        max_digits=19, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Montant total du paiement"
    )
    statut = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='EN_ATTENTE',
        db_index=True,
        help_text="Statut du paiement"
    )
    fichier_detail = models.FileField(
        upload_to='commissions/details/', 
        blank=True, 
        null=True,
        help_text="Fichier de détail fourni par la compagnie"
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes ou commentaires sur le paiement"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='paiements_commission_crees',
        help_text="Utilisateur ayant créé le paiement"
    )
    
    class Meta:
        db_table = 'std_paiement_commission'
        ordering = ['-date_paiement', '-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['date_paiement', 'statut']),
            models.Index(fields=['compagnie', 'statut']),
        ]
        verbose_name = "Paiement de commission"
        verbose_name_plural = "Paiements de commission"
    
    def __str__(self):
        return f"Paiement {self.reference} - {self.montant_total}€"
    
    def montant_total_details(self):
        """Calcule le montant total des détails"""
        return self.details.filter(
            est_annule=False
        ).aggregate(
            total=models.Sum('montant_commission_paye')
        )['total'] or Decimal('0.00')
    
    def nombre_affaires(self):
        """Retourne le nombre d'affaires dans ce paiement"""
        return self.details.filter(est_annule=False).count()


class DetailPaiementCommission(models.Model):
    """
    Détail du paiement de commission par affaire (quittance)
    Une affaire peut avoir plusieurs paiements partiels
    """
    paiement = models.ForeignKey(
        PaiementCommission,
        on_delete=models.CASCADE,
        related_name='details',
        help_text="Paiement global auquel ce détail appartient"
    )
    quittance = models.ForeignKey(
        Quittance,
        on_delete=models.PROTECT,
        related_name='details_commission',
        help_text="Quittance concernée"
    )
    detail_reversement = models.ForeignKey(
        DetailReversement,
        on_delete=models.PROTECT,
        related_name='details_commission',
        help_text="Ligne de reversement concernée"
    )
    
    # Montants
    montant_prime_reversee = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        help_text="Montant de la prime reversée à la compagnie"
    )
    taux_commission = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Taux de commission en %"
    )
    montant_commission_du = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Montant total de la commission due pour cette affaire"
    )
    montant_commission_paye = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Montant de la commission payée dans ce paiement"
    )
    
    # Statut
    est_annule = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indique si ce paiement a été annulé"
    )
    
    # Métadonnées
    reference_affaire = models.CharField(
        max_length=100,
        blank=True,
        help_text="Référence de l'affaire fournie par la compagnie"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'std_detail_paiement_commission'
        indexes = [
            models.Index(fields=['quittance']),
            models.Index(fields=['detail_reversement']),
            models.Index(fields=['est_annule']),
            models.Index(fields=['paiement', 'est_annule']),
        ]
        verbose_name = "Détail de paiement de commission"
        verbose_name_plural = "Détails de paiement de commission"
    
    def __str__(self):
        return f"Commission {self.montant_commission_paye}€ - Quittance {self.quittance.numeroquittance}"
    
    def save(self, *args, **kwargs):
        # Validation : vérifier que le detail_reversement correspond bien à la quittance
        if self.detail_reversement.ligne_encaissement.numeroquittance.idquittance != self.quittance.idquittance:
            raise ValueError(
                "Le détail de reversement ne correspond pas à la quittance"
            )
        
        # Vérifier que le montant payé ne dépasse pas le montant dû
        if not self.est_annule:
            montant_total_paye = DetailPaiementCommission.objects.filter(
                detail_reversement=self.detail_reversement,
                est_annule=False
            ).exclude(id=self.id).aggregate(
                total=models.Sum('montant_commission_paye')
            )['total'] or Decimal('0.00')
            
            nouveau_total = montant_total_paye + self.montant_commission_paye
            
            if nouveau_total > self.montant_commission_du:
                raise ValueError(
                    f"Le montant total payé ({nouveau_total}) "
                    f"dépasse le montant dû ({self.montant_commission_du})"
                )
        
        super().save(*args, **kwargs)
    
    def montant_restant_a_payer(self):
        """Calcule le montant restant à payer pour cette affaire"""
        montant_total_paye = DetailPaiementCommission.objects.filter(
            detail_reversement=self.detail_reversement,
            est_annule=False
        ).aggregate(
            total=models.Sum('montant_commission_paye')
        )['total'] or Decimal('0.00')
        
        return self.montant_commission_du - montant_total_paye


class AnnulationPaiementCommission(models.Model):
    """
    Enregistre l'annulation d'un ou plusieurs paiements de commission
    """
    reference = models.CharField(
        max_length=50, 
        unique=True,
        db_index=True,
        help_text="Référence unique de l'annulation"
    )
    motif = models.TextField(
        help_text="Motif de l'annulation"
    )
    date_annulation = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Date et heure de l'annulation"
    )
    annule_par = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='annulations_commission',
        help_text="Utilisateur ayant effectué l'annulation"
    )
    
    # Relations vers les détails annulés
    details_annules = models.ManyToManyField(
        DetailPaiementCommission,
        related_name='annulation',
        through='DetailAnnulation'
    )
    
    class Meta:
        db_table = 'std_annulation_paiement_commission'
        ordering = ['-date_annulation']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['date_annulation']),
        ]
        verbose_name = "Annulation de paiement de commission"
        verbose_name_plural = "Annulations de paiement de commission"
    
    def __str__(self):
        return f"Annulation {self.reference} - {self.date_annulation.date()}"
    
    def montant_total_annule(self):
        """Calcule le montant total annulé"""
        return self.details_annules.aggregate(
            total=models.Sum('montant_commission_paye')
        )['total'] or Decimal('0.00')
    
    def nombre_details_annules(self):
        """Retourne le nombre de détails annulés"""
        return self.details_annules.count()


class DetailAnnulation(models.Model):
    """
    Table de liaison pour l'annulation avec informations supplémentaires
    """
    annulation = models.ForeignKey(
        AnnulationPaiementCommission,
        on_delete=models.CASCADE,
        related_name='details_annulation'
    )
    detail_paiement = models.ForeignKey(
        DetailPaiementCommission,
        on_delete=models.CASCADE,
        related_name='details_annulation'
    )
    commentaire = models.TextField(
        blank=True,
        help_text="Commentaire spécifique pour ce détail"
    )
    
    class Meta:
        db_table = 'std_detail_annulation'
        unique_together = [['annulation', 'detail_paiement']]
        verbose_name = "Détail d'annulation"
        verbose_name_plural = "Détails d'annulation"
    
    def __str__(self):
        return f"Annulation {self.annulation.reference} - Détail {self.detail_paiement.id}"


class SnapshotCommission(models.Model):
    """
    Snapshot quotidien des statistiques de commission
    Permet de suivre l'évolution dans le temps et d'améliorer les performances
    """
    date_snapshot = models.DateField(
        unique=True,
        db_index=True,
        help_text="Date du snapshot"
    )
    
    # Statistiques globales
    commissions_dues_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Montant total des commissions dues"
    )
    commissions_payees_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Montant total des commissions payées"
    )
    commissions_en_attente_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Montant total des commissions en attente"
    )
    
    nombre_affaires_total = models.IntegerField(
        help_text="Nombre total d'affaires"
    )
    nombre_affaires_payees = models.IntegerField(
        help_text="Nombre d'affaires entièrement payées"
    )
    nombre_affaires_non_payees = models.IntegerField(
        help_text="Nombre d'affaires non payées"
    )
    nombre_affaires_partielles = models.IntegerField(
        help_text="Nombre d'affaires partiellement payées"
    )
    
    # Performance
    taux_recouvrement = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Pourcentage de commissions recouvrées"
    )
    delai_moyen_paiement_jours = models.IntegerField(
        help_text="Délai moyen entre reversement et paiement commission en jours"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'std_snapshot_commission'
        ordering = ['-date_snapshot']
        indexes = [
            models.Index(fields=['date_snapshot']),
        ]
        verbose_name = "Snapshot de commission"
        verbose_name_plural = "Snapshots de commission"
    
    def __str__(self):
        return f"Snapshot {self.date_snapshot}"


class SnapshotCommissionCompagnie(models.Model):
    """
    Snapshot par compagnie
    """
    snapshot = models.ForeignKey(
        SnapshotCommission,
        on_delete=models.CASCADE,
        related_name='details_compagnie'
    )
    compagnie = models.ForeignKey(
        Compagnie, 
        on_delete=models.CASCADE
    )
    
    commissions_dues = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Montant des commissions dues pour cette compagnie"
    )
    commissions_payees = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Montant des commissions payées par cette compagnie"
    )
    commissions_en_attente = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Montant des commissions en attente pour cette compagnie"
    )
    
    nombre_affaires = models.IntegerField(
        help_text="Nombre d'affaires pour cette compagnie"
    )
    delai_moyen_paiement_jours = models.IntegerField(
        help_text="Délai moyen de paiement pour cette compagnie en jours"
    )
    
    class Meta:
        db_table = 'std_snapshot_commission_compagnie'
        unique_together = [['snapshot', 'compagnie']]
        indexes = [
            models.Index(fields=['compagnie', 'snapshot']),
        ]
        verbose_name = "Snapshot de commission par compagnie"
        verbose_name_plural = "Snapshots de commission par compagnie"
    
    def __str__(self):
        return f"Snapshot {self.snapshot.date_snapshot} - {self.compagnie.nom}"


class CacheDashboard(models.Model):
    """
    Cache des calculs de dashboard pour améliorer les performances
    """
    cle = models.CharField(
        max_length=200, 
        unique=True,
        db_index=True,
        help_text="Clé unique pour identifier le cache"
    )
    donnees = models.JSONField(
        help_text="Données cachées au format JSON"
    )
    date_expiration = models.DateTimeField(
        db_index=True,
        help_text="Date et heure d'expiration du cache"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'std_cache_dashboard'
        indexes = [
            models.Index(fields=['cle', 'date_expiration']),
        ]
        verbose_name = "Cache de dashboard"
        verbose_name_plural = "Caches de dashboard"
    
    def __str__(self):
        return f"Cache {self.cle}"
    
    @classmethod
    def get_cache(cls, cle):
        """Récupère une valeur du cache si elle n'a pas expiré"""
        try:
            cache_obj = cls.objects.get(
                cle=cle,
                date_expiration__gt=timezone.now()
            )
            return cache_obj.donnees
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def set_cache(cls, cle, donnees, duree_minutes=60):
        """Stocke une valeur dans le cache"""
        from datetime import timedelta
        date_expiration = timezone.now() + timedelta(minutes=duree_minutes)
        
        cache_obj, created = cls.objects.update_or_create(
            cle=cle,
            defaults={
                'donnees': donnees,
                'date_expiration': date_expiration
            }
        )
        return cache_obj
    
    @classmethod
    def invalider_cache(cls, pattern=None):
        """Invalide le cache (tout ou par pattern)"""
        if pattern:
            cls.objects.filter(cle__startswith=pattern).delete()
        else:
            cls.objects.all().delete()


class NotificationCommission(models.Model):
    """
    Système de notifications pour les événements importants liés aux commissions
    """
    TYPE_CHOICES = [
        ('RETARD_PAIEMENT', 'Retard de paiement'),
        ('PAIEMENT_RECU', 'Paiement reçu'),
        ('PAIEMENT_ANNULE', 'Paiement annulé'),
        ('VALIDATION_REQUISE', 'Validation requise'),
        ('ANOMALIE_DETECTEE', 'Anomalie détectée'),
    ]
    
    type_notification = models.CharField(
        max_length=30, 
        choices=TYPE_CHOICES,
        db_index=True,
        help_text="Type de notification"
    )
    titre = models.CharField(
        max_length=200,
        help_text="Titre de la notification"
    )
    message = models.TextField(
        help_text="Message de la notification"
    )
    
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications_commission',
        help_text="Destinataire de la notification"
    )
    
    lue = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indique si la notification a été lue"
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Date de création de la notification"
    )
    date_lecture = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date de lecture de la notification"
    )
    
    # Lien vers l'objet concerné (générique)
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    contenu_lie = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        db_table = 'sdt_notification_commission'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['utilisateur', 'lue']),
            models.Index(fields=['type_notification', 'date_creation']),
        ]
        verbose_name = "Notification de commission"
        verbose_name_plural = "Notifications de commission"
    
    def __str__(self):
        return f"{self.type_notification} - {self.titre}"
    
    def marquer_comme_lue(self):
        """Marque la notification comme lue"""
        if not self.lue:
            self.lue = True
            self.date_lecture = timezone.now()
            self.save(update_fields=['lue', 'date_lecture'])