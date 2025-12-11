"""
Modèles pour le système d'autorisation générique
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
import secrets
import string


User = get_user_model()

class TypeOperation(models.TextChoices):
    """Types d'opérations nécessitant une autorisation"""
    ANNULATION_ENCAISSEMENT = 'ANNUL_ENC', 'Annulation Encaissement'
    ANNULATION_REVERSEMENT = 'ANNUL_REV', 'Annulation Reversement'
    ANNULATION_CONTRAT = 'ANNUL_CNT', 'Annulation Contrat'
    


class StatutDemande(models.TextChoices):
    """Statuts possibles d'une demande d'autorisation"""
    EN_ATTENTE = 'PENDING', 'En attente'
    APPROUVEE = 'APPROVED', 'Approuvée'
    REJETEE = 'REJECTED', 'Rejetée'
    EXPIREE = 'EXPIRED', 'Expirée'
    UTILISEE = 'USED', 'Utilisée'
    ANNULEE = 'CANCELLED', 'Annulée'  # Demande annulée par le demandeur


class DemandeAutorisation(models.Model):
    """
    Modèle générique pour toute demande d'autorisation
    """
    # Identification
    demandeur = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='demandes_effectuees',
        verbose_name="Demandeur"
    )
    type_operation = models.CharField(
        max_length=20,
        choices=TypeOperation.choices,
        default=TypeOperation.ANNULATION_ENCAISSEMENT,
        verbose_name="Type d'opération"
    )
    
    # Objet de la demande
    objet = models.CharField(max_length=255, verbose_name="Objet")
    motif = models.TextField(verbose_name="Motif")
    date_demande = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de la demande"
    )
    
    # Référence générique à n'importe quel objet Django
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Type d'objet"
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="ID de l'objet"
    )
    objet_concerne = GenericForeignKey('content_type', 'object_id')
    
    # Métadonnées
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Métadonnées"
    )
    
    # Statut
    statut = models.CharField(
        max_length=20,
        choices=StatutDemande.choices,
        default=StatutDemande.EN_ATTENTE,
        verbose_name="Statut"
    )
    
    # Approbation/Rejet
    approbateur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='demandes_traitees',
        verbose_name="Approbateur"
    )
    date_traitement = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de traitement"
    )
    motif_rejet = models.TextField(
        blank=True,
        verbose_name="Motif du rejet"
    )
    
    # Gestion des jetons
    jeton_genere = models.BooleanField(
        default=False,
        verbose_name="Jeton généré"
    )
    date_expiration = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'expiration"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['date_demande']),
            models.Index(fields=['date_traitement']),
            models.Index(fields=['statut', 'date_demande']),
            models.Index(fields=['demandeur', 'statut']),
            models.Index(fields=['type_operation', 'statut']),
            models.Index(fields=['content_type', 'object_id', 'statut']),
            # Index pour détecter les doublons
            models.Index(fields=['type_operation', 'content_type', 'object_id', 'statut']),
        ]
        ordering = ['-date_demande']
        verbose_name = "Demande d'autorisation"
        verbose_name_plural = "Demandes d'autorisation"
    
    def __str__(self):
        return f"{self.get_type_operation_display()} - {self.demandeur} - {self.statut}"
    
    def clean(self):
        """Validation étendue avec vérification des doublons"""
        super().clean()
        
        # 🆕 Vérifier qu'il n'existe pas déjà une demande en attente ou approuvée
        if self.content_type and self.object_id:
            demandes_actives = DemandeAutorisation.objects.filter(
                type_operation=self.type_operation,
                content_type=self.content_type,
                object_id=self.object_id,
                statut__in=[StatutDemande.EN_ATTENTE, StatutDemande.APPROUVEE]
            )
            
            # Exclure la demande actuelle lors de la mise à jour
            if self.pk:
                demandes_actives = demandes_actives.exclude(pk=self.pk)
            
            if demandes_actives.exists():
                demande_existante = demandes_actives.first()
                raise ValidationError({
                    'object_id': f'Une demande pour cette opération est déjà {demande_existante.get_statut_display().lower()}. '
                                f'Demande #{demande_existante.id} créée le {demande_existante.date_demande.strftime("%d/%m/%Y")}'
                })
        
        # 🆕 Vérifier que l'objet n'est pas déjà annulé/traité
        if self.objet_concerne:
            obj = self.objet_concerne
            
            # Pour les encaissements
            if self.type_operation == TypeOperation.ANNULATION_ENCAISSEMENT:
                if hasattr(obj, 'piece_annulee') and obj.piece_annulee:
                    raise ValidationError({
                        'object_id': 'Cet encaissement est déjà annulé'
                    })
                if hasattr(obj, 'annule') and obj.annule:
                    raise ValidationError({
                        'object_id': 'Cet encaissement est déjà annulé'
                    })
    
    def save(self, *args, **kwargs):
        """Override save pour ajouter la validation"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def approuver(self, approbateur):
        """Approuve la demande avec vérifications robustes"""
        if self.statut != StatutDemande.EN_ATTENTE:
            raise ValidationError(
                f"Cette demande a déjà été traitée (statut: {self.get_statut_display()})"
            )
        
        # 🆕 Vérifier à nouveau qu'il n'y a pas eu d'autre approbation entre temps
        with transaction.atomic():
            # Lock la ligne pour éviter les race conditions
            demande = DemandeAutorisation.objects.select_for_update().get(pk=self.pk)
            
            if demande.statut != StatutDemande.EN_ATTENTE:
                raise ValidationError("Cette demande a déjà été traitée")
            
            # 🆕 Vérifier qu'il n'y a pas d'autre demande approuvée pour le même objet
            autres_demandes_approuvees = DemandeAutorisation.objects.filter(
                type_operation=self.type_operation,
                content_type=self.content_type,
                object_id=self.object_id,
                statut=StatutDemande.APPROUVEE
            ).exclude(pk=self.pk)
            
            if autres_demandes_approuvees.exists():
                raise ValidationError(
                    "Une autre demande pour cette opération a déjà été approuvée"
                )
            
            # 🆕 Annuler automatiquement les autres demandes en attente
            DemandeAutorisation.objects.filter(
                type_operation=self.type_operation,
                content_type=self.content_type,
                object_id=self.object_id,
                statut=StatutDemande.EN_ATTENTE
            ).exclude(pk=self.pk).update(
                statut=StatutDemande.ANNULEE,
                motif_rejet='Annulée automatiquement suite à l\'approbation d\'une autre demande',
                date_traitement=timezone.now()
            )
            
            # Approuver la demande
            demande.statut = StatutDemande.APPROUVEE
            demande.approbateur = approbateur
            demande.date_traitement = timezone.now()
            demande.save()
            
            # Rafraîchir l'instance actuelle
            self.refresh_from_db()
    
    def rejeter(self, approbateur, motif_rejet):
        """Rejette la demande"""
        if self.statut != StatutDemande.EN_ATTENTE:
            raise ValidationError(
                f"Cette demande a déjà été traitée (statut: {self.get_statut_display()})"
            )
        
        self.statut = StatutDemande.REJETEE
        self.approbateur = approbateur
        self.date_traitement = timezone.now()
        self.motif_rejet = motif_rejet
        self.save()
    
    def marquer_comme_utilisee(self):
        """Marque la demande comme utilisée après utilisation du jeton"""
        if self.statut != StatutDemande.APPROUVEE:
            raise ValidationError(
                "Seules les demandes approuvées peuvent être marquées comme utilisées"
            )
        
        self.statut = StatutDemande.UTILISEE
        self.save()
    
    @staticmethod
    def verifier_demande_active(type_operation, content_type, object_id):
        """
        🆕 Méthode utilitaire pour vérifier s'il existe une demande active
        Retourne la demande active ou None
        """
        return DemandeAutorisation.objects.filter(
            type_operation=type_operation,
            content_type=content_type,
            object_id=object_id,
            statut__in=[StatutDemande.EN_ATTENTE, StatutDemande.APPROUVEE]
        ).first()
    
    @staticmethod
    def peut_creer_demande(type_operation, content_type, object_id):
        """
        🆕 Vérifie si une nouvelle demande peut être créée
        """
        demande_active = DemandeAutorisation.verifier_demande_active(
            type_operation, content_type, object_id
        )
        return demande_active is None


class JetonAutorisation(models.Model):
    """Jeton d'autorisation généré après approbation"""
    demande = models.OneToOneField(
        DemandeAutorisation,
        on_delete=models.CASCADE,
        related_name='jeton',
        verbose_name="Demande"
    )
    code = models.CharField(
        max_length=8,
        unique=True,
        db_index=True,
        verbose_name="Code"
    )
    
    # Sécurité
    date_generation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de génération"
    )
    date_expiration = models.DateTimeField(verbose_name="Date d'expiration")
    utilise = models.BooleanField(
        default=False,
        verbose_name="Utilisé"
    )
    date_utilisation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'utilisation"
    )
    
    # Traçabilité
    ip_utilisation = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP d'utilisation"
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['code', 'utilise']),
            models.Index(fields=['date_expiration', 'utilise']),
        ]
        verbose_name = "Jeton d'autorisation"
        verbose_name_plural = "Jetons d'autorisation"
    
    def __str__(self):
        return f"Jeton {self.code} - {self.demande}"
    
    @staticmethod
    def generer_code():
        """Génère un code alphanumérique sécurisé de 8 caractères"""
        alphabet = string.ascii_uppercase + string.digits
        alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
        return ''.join(secrets.choice(alphabet) for _ in range(8))
    
    def save(self, *args, **kwargs):
        if not self.code:
            while True:
                code = self.generer_code()
                if not JetonAutorisation.objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)
    
    def est_valide(self):
        """Vérifie si le jeton est encore valide"""
        if self.utilise:
            return False
        if timezone.now() > self.date_expiration:
            return False
        if self.demande.statut != StatutDemande.APPROUVEE:
            return False
        return True
    
    def utiliser(self, ip_address=None, user_agent=None):
        """
        Marque le jeton comme utilisé avec vérifications robustes
        """
        # 🆕 Utiliser select_for_update pour éviter les race conditions
        with transaction.atomic():
            jeton = JetonAutorisation.objects.select_for_update().get(pk=self.pk)
            
            if jeton.utilise:
                raise ValidationError("Ce jeton a déjà été utilisé")
            
            if timezone.now() > jeton.date_expiration:
                raise ValidationError("Ce jeton a expiré")
            
            if jeton.demande.statut != StatutDemande.APPROUVEE:
                raise ValidationError("Ce jeton n'est plus valide")
            
            jeton.utilise = True
            jeton.date_utilisation = timezone.now()
            jeton.ip_utilisation = ip_address
            jeton.user_agent = user_agent
            jeton.save()
            
            # Marquer la demande comme utilisée
            jeton.demande.marquer_comme_utilisee()
            
            # Rafraîchir l'instance actuelle
            self.refresh_from_db()


class Permission(models.Model):
    """Permissions pour autoriser des demandes"""
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='permissions_autorisation',
        verbose_name="Utilisateur"
    )
    type_operation = models.CharField(
        max_length=20,
        choices=TypeOperation.choices,
        verbose_name="Type d'opération"
    )
    actif = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['utilisateur', 'type_operation']
        verbose_name = "Permission d'autorisation"
        verbose_name_plural = "Permissions d'autorisation"
    
    def __str__(self):
        return f"{self.utilisateur} - {self.get_type_operation_display()}"
    
    @staticmethod
    def obtenir_approbateurs(type_operation):
        """Retourne les utilisateurs habilités à approuver un type d'opération"""
        return User.objects.filter(
            permissions_autorisation__type_operation=type_operation,
            permissions_autorisation__actif=True,
            is_active=True
        ).distinct()