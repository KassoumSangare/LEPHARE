from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import (
    DemandeAutorisation, 
    JetonAutorisation,
    Permission,
    TypeOperation,
    StatutDemande
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer pour les informations utilisateur"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'name', 'is_admin']
        read_only_fields = fields


class DemandeAutorisationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer une demande d'autorisation
    Compatible avec n'importe quel modèle Django
    """
    # Paramètres pour identifier l'objet concerné (WRITE-ONLY)
    app_label = serializers.CharField(
        write_only=True,  # 🔑 IMPORTANT: Ne pas lire depuis le modèle
        required=True,
        help_text="Label de l'application (ex: 'production')"
    )
    model_name = serializers.CharField(
        write_only=True,  # 🔑 IMPORTANT: Ne pas lire depuis le modèle
        required=True,
        help_text="Nom du modèle (ex: 'encaissement')"
    )
    object_id = serializers.IntegerField(
        write_only=True,  # 🔑 IMPORTANT: Ne pas lire depuis le modèle
        required=True,
        help_text="ID de l'objet"
    )
    
    class Meta:
        model = DemandeAutorisation
        fields = [
            'id', 'type_operation', 'objet', 'motif', 'date_demande',
            'app_label', 'model_name', 'object_id', 'metadata'
        ]
    
    def validate(self, data):
        """Validation globale"""
        # Récupérer le ContentType
        try:
            content_type = ContentType.objects.get(
                app_label=data['app_label'],
                model=data['model_name'].lower()
            )
            data['content_type'] = content_type
        except ContentType.DoesNotExist:
            raise serializers.ValidationError({
                'model_name': f"Le modèle {data['app_label']}.{data['model_name']} n'existe pas"
            })
        
        # Vérifier que l'objet existe
        model_class = content_type.model_class()
        try:
            obj = model_class.objects.get(pk=data['object_id'])
            data['objet_instance'] = obj
        except model_class.DoesNotExist:
            raise serializers.ValidationError({
                'object_id': f"L'objet avec l'ID {data['object_id']} n'existe pas"
            })
        
        # 🆕 VÉRIFICATION CRITIQUE : Demande en doublon
        demande_active = DemandeAutorisation.verifier_demande_active(
            type_operation=data['type_operation'],
            content_type=content_type,
            object_id=data['object_id']
        )
        
        if demande_active:
            date = demande_active.date_demande.strftime('%d/%m/%Y à %H:%M')
            
            if demande_active.statut == StatutDemande.EN_ATTENTE:
                raise serializers.ValidationError({
                    'object_id': (
                        f'Une demande pour cette opération est déjà en attente. '
                        f'Demande #{demande_active.id} créée le {date} par {demande_active.demandeur.username}. '
                        f'Veuillez attendre son traitement avant de créer une nouvelle demande.'
                    )
                })
            elif demande_active.statut == StatutDemande.APPROUVEE:
                # Vérifier si le jeton n'a pas encore été utilisé
                if hasattr(demande_active, 'jeton') and not demande_active.jeton.utilise:
                    raise serializers.ValidationError({
                        'object_id': (
                            f'Une demande pour cette opération a déjà été approuvée. '
                            f'Demande #{demande_active.id} approuvée le {demande_active.date_traitement.strftime("%d/%m/%Y à %H:%M")}. '
                            f'Le jeton n\'a pas encore été utilisé. '
                            f'Veuillez utiliser le jeton existant avant de créer une nouvelle demande.'
                        )
                    })
        
        # 🆕 VÉRIFICATION : L'objet n'est pas déjà annulé
        if data['type_operation'] == TypeOperation.ANNULATION_ENCAISSEMENT:
            # Vérifier différents noms de champs possibles
            if (hasattr(obj, 'piece_annulee') and obj.piece_annulee):
                raise serializers.ValidationError({
                    'object_id': 'Cet encaissement est déjà annulé. Impossible de créer une demande d\'annulation.'
                })
        
        return data
    
    def create(self, validated_data):
        # Retirer les champs qui ne vont pas dans le modèle
        validated_data.pop('app_label', None)
        validated_data.pop('model_name', None)
        validated_data.pop('objet_instance', None)
        
        validated_data['demandeur'] = self.context['request'].user
        return super().create(validated_data)

class DemandeAutorisationDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les demandes d'autorisation"""
    demandeur = UserSerializer(read_only=True)
    approbateur = UserSerializer(read_only=True)
    type_operation_display = serializers.CharField(
        source='get_type_operation_display',
        read_only=True
    )
    statut_display = serializers.CharField(
        source='get_statut_display',
        read_only=True
    )
    
    # Informations sur l'objet concerné
    objet_type = serializers.SerializerMethodField()
    objet_details = serializers.SerializerMethodField()
    
    class Meta:
        model = DemandeAutorisation
        fields = [
            'id', 'demandeur', 'type_operation', 'type_operation_display',
            'objet', 'motif', 'date_demande', 'metadata',
            'statut', 'statut_display', 'approbateur', 'date_traitement',
            'motif_rejet', 'jeton_genere', 'date_expiration',
            'objet_type', 'objet_details',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_objet_type(self, obj):
        """Retourne le type d'objet concerné"""
        if obj.content_type:
            return {
                'app_label': obj.content_type.app_label,
                'model': obj.content_type.model
            }
        return None
    
    def get_objet_details(self, obj):
        """Retourne les détails de l'objet concerné"""
        if obj.objet_concerne:
            # Vous pouvez personnaliser ce qui est retourné selon le type d'objet
            objet_concerne = obj.objet_concerne
            
            # Pour un encaissement
            if hasattr(objet_concerne, 'numeropiece'):
                return {
                    'id': objet_concerne.idencaissement,
                    'reference': objet_concerne.numeropiece,
                    'montant': str(objet_concerne.montantencaissement) if hasattr(objet_concerne, 'montantencaissement') else None,
                }
            
            # Pour d'autres types d'objets, retourner leur représentation string
            return {
                'id': objet_concerne.id,
                'representation': str(objet_concerne)
            }
        return None


class DemandeAutorisationListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des demandes"""
    demandeur = serializers.StringRelatedField()
    approbateur = serializers.StringRelatedField()
    type_operation_display = serializers.CharField(
        source='get_type_operation_display',
        read_only=True
    )
    statut_display = serializers.CharField(
        source='get_statut_display',
        read_only=True
    )
    
    class Meta:
        model = DemandeAutorisation
        fields = [
            'id', 'demandeur', 'type_operation', 'type_operation_display',
            'objet', 'motif', 'date_demande', 'statut', 'statut_display',
            'approbateur', 'date_traitement', 'created_at'
        ]
        read_only_fields = fields


class ApprouverDemandeSerializer(serializers.Serializer):
    """Serializer pour approuver une demande"""
    duree_validite_heures = serializers.IntegerField(
        default=24,
        min_value=1,
        max_value=168,
        help_text="Durée de validité du jeton en heures"
    )


class RejeterDemandeSerializer(serializers.Serializer):
    """Serializer pour rejeter une demande"""
    motif_rejet = serializers.CharField(
        required=True,
        allow_blank=False,
        min_length=10,
        help_text="Motif du rejet"
    )


class AnnulerAvecJetonSerializer(serializers.Serializer):
    """
    Serializer générique pour annuler une opération avec un jeton
    """
    jeton = serializers.CharField(
        max_length=8,
        min_length=8,
        help_text="Code du jeton d'autorisation"
    )
    
    def validate_jeton(self, value):
        """Valide le format du jeton"""
        return value.upper().strip()
    
    def validate(self, data):
        """Validation avec vérification du jeton"""
        # Récupérer l'objet depuis le context
        objet = self.context.get('objet')
        if not objet:
            raise serializers.ValidationError("Objet non fourni dans le contexte")
        
        # Vérifier le jeton
        try:
            jeton = JetonAutorisation.objects.select_related('demande').get(
                code=data['jeton']
            )
            
            # Vérifications
            if not jeton.est_valide():
                if jeton.utilise:
                    raise serializers.ValidationError({
                        'jeton': 'Ce jeton a déjà été utilisé'
                    })
                elif timezone.now() > jeton.date_expiration:
                    raise serializers.ValidationError({
                        'jeton': 'Ce jeton a expiré'
                    })
                else:
                    raise serializers.ValidationError({
                        'jeton': 'Ce jeton n\'est pas valide'
                    })
            
            # Vérifier que le jeton correspond à l'objet encaissement
            if hasattr(objet, "idencaissement") and hasattr(objet, "numeropiece") and hasattr(objet, "montantencaissement"):
                if jeton.demande.object_id != objet.idencaissement:
                    raise serializers.ValidationError({
                    'jeton': 'Ce jeton ne correspond pas à cet objet'
                })
                    
            # Vérifier que le jeton correspond à l'objet reversement
            if hasattr(objet, "id_reversement") and hasattr(objet, "numero_reversement") and hasattr(objet, "montant_reversement"):
                if jeton.demande.object_id != objet.id_reversement:
                    raise serializers.ValidationError({
                    'jeton': 'Ce jeton ne correspond pas à cet objet'
                })
            
            # Vérifier que le jeton correspond à l'objet contrat
            if hasattr(objet, "idcontrat") and hasattr(objet, "numeropolice") and hasattr(objet, "primettc"):
                if jeton.demande.object_id != objet.idcontrat:
                    raise serializers.ValidationError({
                    'jeton': 'Ce jeton ne correspond pas à cet objet'
                })
            # Vérifier le content type
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(objet)
            if jeton.demande.content_type_id != ct.id:
                raise serializers.ValidationError({
                    'jeton': 'Ce jeton ne correspond pas au type d\'objet'
                })
            
            # Vérifier que le demandeur est celui qui fait l'action
            if jeton.demande.demandeur != self.context['request'].user:
                raise serializers.ValidationError({
                    'jeton': 'Vous n\'êtes pas autorisé à utiliser ce jeton'
                })
            
            data['jeton_obj'] = jeton
            
        except JetonAutorisation.DoesNotExist:
            raise serializers.ValidationError({
                'jeton': 'Jeton invalide ou introuvable'
            })
        
        return data


class JetonAutorisationSerializer(serializers.ModelSerializer):
    """Serializer pour les jetons"""
    demande_id = serializers.IntegerField(source='demande.id', read_only=True)
    est_valide = serializers.SerializerMethodField()
    
    class Meta:
        model = JetonAutorisation
        fields = [
            'id', 'code', 'demande_id', 'date_generation',
            'date_expiration', 'utilise', 'date_utilisation', 'est_valide'
        ]
        read_only_fields = fields
    
    def get_est_valide(self, obj):
        return obj.est_valide()


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer pour les permissions"""
    
    utilisateur = UserSerializer(read_only=True) 
    
    type_operation_display = serializers.CharField(
        source='get_type_operation_display',
        read_only=True
    )
    
    class Meta:
        #
        model = Permission
        fields = [
            'id', 'utilisateur', 'type_operation',
            'type_operation_display', 'actif', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def to_internal_value(self, data):
        """
        Intercepte les données entrantes (POST/PUT).
        Si l'ID utilisateur est fourni, le résout en instance User pour la validation et l'enregistrement.
        """
        # 1. Traitement initial par DRF. À ce stade, 'utilisateur' est ignoré car il est 'read_only=True'.
        internal_value = super().to_internal_value(data)
        
        # 2. Récupérer l'ID utilisateur brut de l'entrée (ex: 123)
        utilisateur_id = data.get('utilisateur')
        
        # 3. Si un ID est fourni, tenter de le valider et de le convertir en objet
        if utilisateur_id is not None:
            try:
                # S'assurer que la valeur est un entier valide
                if not isinstance(utilisateur_id, int) and not str(utilisateur_id).isdigit():
                    raise ValueError("L'ID utilisateur doit être un entier.")

                # Tenter de trouver l'instance utilisateur
                user_instance = get_object_or_404(User, pk=utilisateur_id)
                
                # 4. Injecter l'instance User dans les données validées, 
                #    ce qui permet à .save() de fonctionner correctement.
                internal_value['utilisateur'] = user_instance
                
            except (ValueError, User.DoesNotExist):
                # Lever une erreur de validation claire si l'ID est incorrect
                raise serializers.ValidationError({
                    'utilisateur': "L'ID utilisateur fourni est invalide ou n'existe pas."
                })
        
        # 5. Retourner les données validées avec l'instance utilisateur
        return internal_value
    
    def validate(self, data):
        """
        Vérifie l'unicité de la combinaison (utilisateur, type_operation)
        lors de la création d'une nouvelle permission.
        """
        # 1. Vérifiez si les champs critiques sont présents dans les données validées
        #    Si to_internal_value n'a pas réussi à injecter 'utilisateur', 
        #    ce champ ne sera pas dans 'data' et la validation du champ échouera plus tard,
        #    mais nous devons nous assurer qu'il est là pour cette vérification.
        utilisateur = data.get('utilisateur')
        type_operation = data.get('type_operation')
        
        if not utilisateur or not type_operation:
            # Laissez la validation normale des champs requis gérer cela
            return data

        # 2. Vérifiez si une permission existe déjà avec cette combinaison
        exists = self.Meta.model.objects.filter(
            utilisateur=utilisateur,
            type_operation=type_operation
        ).exists()

        if exists:
            # 3. Lever une erreur de validation qui sera renvoyée en HTTP 400
            raise serializers.ValidationError({
                'erreur': [
                f"L'utilisateur {utilisateur.username} possède déjà la permission pour l'opération '{type_operation}'."
                ]
            }
            )

        return data