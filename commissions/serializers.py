"""
Serializers Django REST Framework pour l'API de gestion des commissions
"""
from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from .models import (
    PaiementCommission,
    DetailPaiementCommission,
    AnnulationPaiementCommission,
    DetailAnnulation,
    SnapshotCommission,
    SnapshotCommissionCompagnie,
    NotificationCommission
)
from configuration_api.models import Compagnie

def MoneyField(**kwargs):
    """Champ monétaire qui retourne une string pour préserver la précision"""
    return serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        coerce_to_string=True,
        **kwargs
    )

def PercentField(**kwargs):
    """Champ pourcentage qui retourne une string"""
    return serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=True,
        **kwargs
    )


# =====================================================
# Serializers pour PaiementCommission
# =====================================================

class DetailPaiementCommissionSerializer(serializers.ModelSerializer):
    """
    Serializer de base pour les détails de paiement
    """
    contrat_numero = serializers.CharField(
        source='quittance.police', 
        read_only=True
    )
    quittance_numero = serializers.CharField(
        source='quittance.numeroquittance', 
        read_only=True
    )
    
    class Meta:
        model = DetailPaiementCommission
        fields = [
            'id', 'quittance', 'detail_reversement',
            'contrat_numero', 'quittance_numero',
            'montant_prime_reversee', 'taux_commission',
            'montant_commission_du', 'montant_commission_paye',
            'reference_affaire', 'est_annule', 'created_at'
        ]
        read_only_fields = ['created_at', 'est_annule']
    
    def validate(self, data):
        """Valide que le detail_reversement correspond bien à la quittance"""
        detail_reversement = data.get('detail_reversement')
        quittance = data.get('quittance')
        
        if detail_reversement and quittance:
            if detail_reversement.ligne_encaissement.numeroquittance != quittance:
                raise serializers.ValidationError(
                    "Le détail de reversement ne correspond pas à la quittance"
                )
            
            # Vérifier que ce reversement n'a pas déjà été totalement payé
            montant_deja_paye = DetailPaiementCommission.objects.filter(
                detail_reversement=detail_reversement,
                est_annule=False
            ).aggregate(total=Sum('montant_commission_paye'))['total'] or Decimal('0.00')
            
            montant_du = data.get('montant_commission_du', Decimal('0.00'))
            montant_a_payer = data.get('montant_commission_paye', Decimal('0.00'))
            
            if montant_deja_paye + montant_a_payer > montant_du:
                raise serializers.ValidationError(
                    f"Le montant total payé ({montant_deja_paye + montant_a_payer}) "
                    f"dépasse le montant dû ({montant_du})"
                )
        
        return data


class DetailPaiementCommissionEnrichedSerializer(serializers.ModelSerializer):
    """
    Serializer enrichi avec toutes les informations pour l'affichage
    """
    # Informations du contrat et du client
    contrat_id = serializers.IntegerField(source='quittance.contrat.idcontrat', read_only=True)
    contrat_numero = serializers.CharField(source='quittance.police', read_only=True)
    client_id = serializers.IntegerField(source='quittance.client.IdClient', read_only=True)
    client_nom = serializers.CharField(source='quittance.client.Nom', read_only=True)
    client_prenom = serializers.CharField(source='quittance.client.Prenoms', read_only=True)
    
    # Informations de la quittance
    quittance_id = serializers.IntegerField(source='quittance.idquittance', read_only=True)
    quittance_numero = serializers.CharField(source='quittance.numeroquittance', read_only=True)
    
    # Informations du paiement
    paiement_id = serializers.IntegerField(source='paiement.id', read_only=True)
    paiement_reference = serializers.CharField(source='paiement.reference', read_only=True)
    date_paiement = serializers.DateField(source='paiement.date_paiement', read_only=True)
    paiement_statut = serializers.CharField(source='paiement.statut', read_only=True)
    
    # Informations de la compagnie
    compagnie_id = serializers.IntegerField(source='paiement.compagnie.IdCompagnie', read_only=True)
    compagnie_nom = serializers.CharField(source='paiement.compagnie.RaisonSociale', read_only=True)
    
    # Statut d'annulation
    peut_etre_annule = serializers.SerializerMethodField()
    annulation_reference = serializers.SerializerMethodField()
    date_annulation = serializers.SerializerMethodField()
    
    class Meta:
        model = DetailPaiementCommission
        fields = [
            'id',
            # Contrat et client
            'contrat_id', 'contrat_numero',
            'client_id', 'client_nom', 'client_prenom',
            # Quittance
            'quittance_id', 'quittance_numero',
            # Paiement
            'paiement_id', 'paiement_reference', 'date_paiement', 'paiement_statut',
            # Compagnie
            'compagnie_id', 'compagnie_nom',
            # Montants
            'montant_prime_reversee', 'taux_commission',
            'montant_commission_du', 'montant_commission_paye',
            # Métadonnées
            'reference_affaire', 'est_annule',
            'peut_etre_annule', 'annulation_reference', 'date_annulation',
            'created_at'
        ]
        read_only_fields = ['created_at', 'est_annule']
    
    def get_peut_etre_annule(self, obj):
        """Indique si cette ligne peut être annulée"""
        return not obj.est_annule and obj.paiement.statut in ['EN_ATTENTE', 'TRAITE']
    
    def get_annulation_reference(self, obj):
        """Référence de l'annulation si annulé"""
        if obj.est_annule:
            annulation = obj.annulation.first()
            return annulation.reference if annulation else None
        return None
    
    def get_date_annulation(self, obj):
        """Date de l'annulation si annulé"""
        if obj.est_annule:
            annulation = obj.annulation.first()
            return annulation.date_annulation if annulation else None
        return None


class PaiementCommissionSerializer(serializers.ModelSerializer):
    """
    Serializer principal pour les paiements de commission
    """
    details = DetailPaiementCommissionSerializer(many=True, required=False)
    montant_total_calcule = serializers.SerializerMethodField()
    nombre_affaires = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(
        source='created_by.name', 
        read_only=True
    )
    compagnie_nom = serializers.CharField(
        source='compagnie.RaisonSociale',
        read_only=True
    )
    
    class Meta:
        model = PaiementCommission
        fields = [
            'id', 'reference', 'compagnie', 'compagnie_nom', 'date_paiement',
            'montant_total', 'montant_total_calcule', 'statut',
            'fichier_detail', 'notes', 'details', 'nombre_affaires',
            'created_at', 'updated_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def get_montant_total_calcule(self, obj):
        """Calcule le total des commissions détaillées"""
        return str(obj.montant_total_details())
    
    def get_nombre_affaires(self, obj):
        """Retourne le nombre d'affaires"""
        return obj.nombre_affaires()
    
    def validate_reference(self, value):
        """Vérifie l'unicité de la référence"""
        if self.instance is None:  # Création
            if PaiementCommission.objects.filter(reference=value).exists():
                raise serializers.ValidationError(
                    'Cette référence existe déjà'
                )
        return value


class PaiementCommissionBatchItemSerializer(serializers.Serializer):
    """
    Item pour le paiement batch
    """
    detail_reversement_id = serializers.IntegerField()
    montant_commission_paye = serializers.DecimalField(
        max_digits=19, 
        decimal_places=4,
        min_value=Decimal('0.01')
    )
    reference_affaire = serializers.CharField(
        max_length=100, 
        required=False, 
        allow_blank=True
    )


class PaiementCommissionBatchSerializer(serializers.Serializer):
    """
    Serializer pour l'enregistrement de paiements par lot
    """
    reference = serializers.CharField(max_length=50)
    compagnie_id = serializers.IntegerField()
    date_paiement = serializers.DateField()
    fichier_detail = serializers.FileField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    affaires = PaiementCommissionBatchItemSerializer(many=True, min_length=1)
    
    def validate_compagnie_id(self, value):
        """Vérifier que la compagnie existe"""
        if not Compagnie.objects.filter(IdCompagnie=value).exists():
            raise serializers.ValidationError(
                f"La compagnie {value} n'existe pas"
            )
        return value
    
    def validate_reference(self, value):
        """Vérifier l'unicité de la référence"""
        if PaiementCommission.objects.filter(reference=value).exists():
            raise serializers.ValidationError(
                f"La référence {value} existe déjà"
            )
        return value
    
    def validate_affaires(self, value):
        """Validations sur les affaires"""
        from .models import DetailReversement
        
        detail_reversement_ids = [item['detail_reversement_id'] for item in value]
        
        # Vérifier les doublons
        if len(detail_reversement_ids) != len(set(detail_reversement_ids)):
            raise serializers.ValidationError(
                "Il y a des affaires en double dans la liste"
            )
        
        # Récupérer les informations des reversements
        reversements = DetailReversement.objects.filter(
            id_detail_reversement__in=detail_reversement_ids
        ).select_related('quittance')
        
        if reversements.count() != len(detail_reversement_ids):
            raise serializers.ValidationError(
                "Certains détails de reversement n'existent pas"
            )
        
        # Vérifier pour chaque affaire que le montant ne dépasse pas le reste à payer
        for item in value:
            reversement = reversements.get(id_detail_reversement=item['detail_reversement_id'])
            
            # Calculer le montant commission dû
            montant_commission_du = reversement.ligne_encaissement.numeroquittance.commission
            
            # Calculer le montant déjà payé
            montant_deja_paye = DetailPaiementCommission.objects.filter(
                detail_reversement_id=item['detail_reversement_id'],
                est_annule=False
            ).aggregate(
                total=Sum('montant_commission_paye')
            )['total'] or Decimal('0.00')
            
            montant_restant = montant_commission_du - montant_deja_paye
            
            if item['montant_commission_paye'] > montant_restant:
                raise serializers.ValidationError(
                    f"Affaire {reversement.ligne_encaissement.numeroquittance.numeroquittance}: "
                    f"le montant à payer ({item['montant_commission_paye']}) "
                    f"dépasse le montant restant dû ({montant_restant})"
                )
        
        return value


# =====================================================
# Serializers pour Annulation
# =====================================================

class DetailAnnulationSerializer(serializers.ModelSerializer):
    """
    Serializer pour les détails d'annulation
    """
    detail_paiement_id = serializers.IntegerField(source='detail_paiement.id', read_only=True)
    quittance_numero = serializers.CharField(source='detail_paiement.quittance.numeroquittance', read_only=True)
    montant_annule = serializers.DecimalField(
        source='detail_paiement.montant_commission_paye',
        max_digits=19,
        decimal_places=4,
        read_only=True
    )
    
    class Meta:
        model = DetailAnnulation
        fields = ['id', 'detail_paiement_id', 'quittance_numero', 'montant_annule', 'commentaire']


class AnnulationPaiementCommissionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les annulations de paiement
    """
    details_count = serializers.IntegerField(
        source='nombre_details_annules',
        read_only=True
    )
    montant_total_annule = serializers.SerializerMethodField()
    annule_par_username = serializers.CharField(
        source='annule_par.name', 
        read_only=True
    )
    details = DetailAnnulationSerializer(
        source='details_annulation',
        many=True,
        read_only=True
    )
    
    class Meta:
        model = AnnulationPaiementCommission
        fields = [
            'id', 'reference', 'motif', 'date_annulation',
            'annule_par', 'annule_par_username',
            'details_count', 'montant_total_annule', 'details'
        ]
        read_only_fields = ['date_annulation', 'annule_par']
    
    def get_montant_total_annule(self, obj):
        return str(obj.montant_total_annule())


class AnnulerSelectionSerializer(serializers.Serializer):
    """
    Serializer pour l'annulation d'une sélection de lignes
    """
    reference = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Référence de l'annulation (générée automatiquement si non fournie)"
    )
    motif = serializers.CharField(min_length=10)
    details_paiement_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    commentaires = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        help_text="Commentaires optionnels par detail_paiement_id"
    )
    
    def validate_details_paiement_ids(self, value):
        """Vérifier que tous les détails existent"""
        existing_count = DetailPaiementCommission.objects.filter(
            id__in=value
        ).count()
        
        if existing_count != len(value):
            raise serializers.ValidationError(
                "Certains détails n'existent pas"
            )
        
        # Vérifier les doublons
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Il y a des doublons dans la sélection"
            )
        
        return value
    
    def validate(self, data):
        """Générer une référence si non fournie"""
        if not data.get('reference'):
            data['reference'] = f'ANN-{timezone.now().strftime("%Y%m%d-%H%M%S")}'
        
        # Vérifier l'unicité de la référence
        if AnnulationPaiementCommission.objects.filter(
            reference=data['reference']
        ).exists():
            raise serializers.ValidationError({
                'reference': 'Cette référence existe déjà'
            })
        
        return data


# =====================================================
# Serializers pour Affaires et Recherche
# =====================================================

class AffaireCommissionSerializer(serializers.Serializer):
    """
    Serializer pour afficher les informations d'une affaire et son statut de commission
    """
    # Informations de l'affaire
    detail_reversement_id = serializers.IntegerField()
    quittance_id = serializers.IntegerField()
    quittance_numero = serializers.CharField()
    contrat_id = serializers.IntegerField()
    contrat_numero = serializers.CharField()
    client_id = serializers.IntegerField()
    client_nom = serializers.CharField()
    client_prenom = serializers.CharField()
    client_nom_complet = serializers.CharField()
    compagnie_id = serializers.IntegerField()
    compagnie_nom = serializers.CharField()
    
    # Informations de reversement
    reversement_id = serializers.IntegerField()
    date_reversement = serializers.DateField()
    montant_prime_reversee = MoneyField()
    
    # Informations de commission
    taux_commission = PercentField()
    montant_commission_du = MoneyField()
    montant_commission_paye = MoneyField()
    montant_commission_restant = MoneyField()
    
    # Dates de paiement
    derniere_date_paiement = serializers.DateField(allow_null=True)
    
    # Statut
    statut_paiement = serializers.CharField()


class RechercheAffairePourPaiementSerializer(serializers.Serializer):
    """
    Serializer pour la recherche d'affaires éligibles au paiement
    """
    compagnie_id = serializers.IntegerField(required=False)
    client_nom = serializers.CharField(required=False, max_length=200)
    quittance_numero = serializers.CharField(required=False, max_length=100)
    contrat_numero = serializers.CharField(required=False, max_length=100)
    
    date_reversement_debut = serializers.DateField(required=False)
    date_reversement_fin = serializers.DateField(required=False)
    
    montant_restant_min = serializers.DecimalField(
        required=False,
        max_digits=19,
        decimal_places=4
    )
    montant_restant_max = serializers.DecimalField(
        required=False,
        max_digits=19,
        decimal_places=4
    )
    
    statut = serializers.ChoiceField(
        required=False,
        choices=['NON_PAYE', 'PARTIELLEMENT_PAYE']
    )
    
    ordre = serializers.ChoiceField(
        required=False,
        default='date_reversement_asc',
        choices=[
            'date_reversement_asc',
            'date_reversement_desc',
            'montant_restant_asc',
            'montant_restant_desc'
        ]
    )
    
    limite = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=1000
    )
    
    def validate(self, data):
        """Vérifier la cohérence des paramètres"""
        # Vérifier la cohérence des dates
        if (data.get('date_reversement_debut') and 
            data.get('date_reversement_fin') and
            data['date_reversement_debut'] > data['date_reversement_fin']):
            raise serializers.ValidationError(
                "La date de début doit être antérieure à la date de fin"
            )
        
        # Vérifier la cohérence des montants
        if (data.get('montant_restant_min') and 
            data.get('montant_restant_max') and
            data['montant_restant_min'] > data['montant_restant_max']):
            raise serializers.ValidationError(
                "Le montant minimum doit être inférieur au montant maximum"
            )
        
        return data


# =====================================================
# Serializers pour Dashboard
# =====================================================

class KPIGlobalSerializer(serializers.Serializer):
    """
    Serializer pour les KPI globaux
    """
    commissions_dues_total = MoneyField()
    commissions_payees_total = MoneyField()
    commissions_en_attente = MoneyField()
    
    nombre_affaires_total = serializers.IntegerField()
    nombre_affaires_payees = serializers.IntegerField()
    nombre_affaires_non_payees = serializers.IntegerField()
    nombre_affaires_partielles = serializers.IntegerField()
    
    taux_recouvrement = PercentField()
    delai_moyen_paiement = serializers.IntegerField()
    
    # Métadonnées
    periode_debut = serializers.DateField(required=False, allow_null=True)
    periode_fin = serializers.DateField(required=False, allow_null=True)
    date_calcul = serializers.DateTimeField(required=False)


class StatistiqueCompagnieSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques par compagnie
    """
    compagnie_id = serializers.IntegerField()
    compagnie_nom = serializers.CharField()
    
    commissions_dues = MoneyField()
    commissions_payees = MoneyField()
    commissions_en_attente = MoneyField()
    
    nombre_affaires = serializers.IntegerField()
    nombre_payees = serializers.IntegerField()
    nombre_non_payees = serializers.IntegerField()
    nombre_partielles = serializers.IntegerField()
    
    taux_recouvrement = PercentField()


class EvolutionMensuelleSerializer(serializers.Serializer):
    """
    Serializer pour l'évolution mensuelle
    """
    mois = serializers.DateField()
    commissions_dues = MoneyField()
    commissions_payees = MoneyField()
    commissions_en_attente = MoneyField()
    nombre_affaires = serializers.IntegerField()


class CommissionParAncienneteSerializer(serializers.Serializer):
    """
    Serializer pour les commissions par ancienneté
    """
    tranche = serializers.CharField()
    montant = MoneyField()
    nombre = serializers.IntegerField()


class TopAffaireSerializer(serializers.Serializer):
    """
    Serializer pour le top des affaires
    """
    detail_reversement_id = serializers.IntegerField()
    quittance_numero = serializers.CharField()
    contrat_numero = serializers.CharField()
    client_nom = serializers.CharField()
    compagnie_nom = serializers.CharField()
    
    montant_commission_du = MoneyField()
    montant_commission_paye = MoneyField()
    montant_commission_restant = MoneyField()
    statut = serializers.CharField()


class PerformancePaiementSerializer(serializers.Serializer):
    """
    Serializer pour les performances de paiement
    """
    compagnie_id = serializers.IntegerField()
    compagnie_nom = serializers.CharField()
    delai_moyen_jours = serializers.IntegerField()
    nombre_paiements = serializers.IntegerField()


class TauxConformiteSerializer(serializers.Serializer):
    """
    Serializer pour le taux de conformité
    """
    taux_conformite = PercentField()
    nombre_ecarts = serializers.IntegerField()
    nombre_paiements = serializers.IntegerField()


# =====================================================
# Serializers pour Snapshots
# =====================================================

class SnapshotCommissionCompagnieSerializer(serializers.ModelSerializer):
    """
    Serializer pour les snapshots par compagnie
    """
    compagnie_nom = serializers.CharField(source='compagnie.RaisonSociale', read_only=True)
    
    class Meta:
        model = SnapshotCommissionCompagnie
        fields = [
            'id',
            'compagnie',
            'compagnie_nom',
            'commissions_dues',
            'commissions_payees',
            'commissions_en_attente',
            'nombre_affaires',
            'delai_moyen_paiement_jours',
        ]
        read_only_fields = ['id']


class SnapshotCommissionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les snapshots quotidiens
    """
    details_compagnie = SnapshotCommissionCompagnieSerializer(
        many=True,
        read_only=True
    )
    
    class Meta:
        model = SnapshotCommission
        fields = [
            'id',
            'date_snapshot',
            'commissions_dues_total',
            'commissions_payees_total',
            'commissions_en_attente_total',
            'nombre_affaires_total',
            'nombre_affaires_payees',
            'nombre_affaires_non_payees',
            'nombre_affaires_partielles',
            'taux_recouvrement',
            'delai_moyen_paiement_jours',
            'created_at',
            'details_compagnie',
        ]
        read_only_fields = ['id', 'created_at']


class SnapshotCommissionListSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour la liste des snapshots (sans les détails)
    """
    class Meta:
        model = SnapshotCommission
        fields = [
            'id',
            'date_snapshot',
            'commissions_dues_total',
            'commissions_payees_total',
            'commissions_en_attente_total',
            'taux_recouvrement',
            'delai_moyen_paiement_jours',
        ]
        read_only_fields = ['id']


# =====================================================
# Serializers pour Notifications
# =====================================================

class NotificationCommissionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les notifications
    """
    utilisateur_email = serializers.CharField(
        source='utilisateur.email',
        read_only=True
    )
    
    class Meta:
        model = NotificationCommission
        fields = [
            'id', 'type_notification', 'titre', 'message',
            'utilisateur', 'utilisateur_email', 'lue',
            'date_creation', 'date_lecture'
        ]
        read_only_fields = ['date_creation', 'date_lecture']