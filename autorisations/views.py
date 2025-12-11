from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend
from typing import cast
from django.contrib.auth import get_user_model

from .models import (
    DemandeAutorisation,
    JetonAutorisation,
    Permission as PermissionModel,
    StatutDemande
)
from .serializers import (
    DemandeAutorisationCreateSerializer,
    DemandeAutorisationDetailSerializer,
    DemandeAutorisationListSerializer,
    ApprouverDemandeSerializer,
    RejeterDemandeSerializer,
    JetonAutorisationSerializer,
    PermissionSerializer,
    UserSerializer,
)
from .permissions import (
    EstApprobateur,
    EstDemandeur,
    PeutCreerDemande
)
from core.date_parser import parse_date_string
from .filters import DemandeAutorisationFilter
from .tasks import (
    envoyer_notification_nouvelle_demande,
    envoyer_jeton_autorisation,
    envoyer_notification_rejet
)

User = get_user_model()

class DemandeAutorisationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les demandes d'autorisation
    
    Endpoints disponibles:
    - list: Liste les demandes (filtrées selon le rôle)
    - create: Crée une nouvelle demande
    - retrieve: Détails d'une demande
    - update/partial_update: Modification (restreinte)
    - destroy: Suppression (restreinte)
    - mes_demandes: Liste les demandes de l'utilisateur connecté
    - en_attente: Liste les demandes en attente d'autorisation
    - approuvees: Liste les demandes approuvées
    - rejetees: Liste les demandes rejetées
    - utilisees: Liste les demandes utilisées
    - approuver: Approuve une demande et génère un jeton
    - rejeter: Rejette une demande
    - statistiques: Statistiques des demandes
    """
    queryset = DemandeAutorisation.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DemandeAutorisationFilter
    filterset_fields = ['statut', 'type_operation', 'demandeur', 'approbateur']
    search_fields = ['objet', 'motif', 'demandeur__username', 'demandeur__email']
    ordering_fields = ['date_demande', 'date_traitement', 'created_at']
    ordering = ['-date_demande']
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'create':
            return DemandeAutorisationCreateSerializer
        elif self.action in ['list', 'mes_demandes', 'en_attente', 'approuvees', 'rejetees', 'utilisees', 'par_periode', 'aujourdhui', 'cette_semaine', 'ce_mois']:
            return DemandeAutorisationListSerializer
        return DemandeAutorisationDetailSerializer
    
    def get_permissions(self):
        """Permissions selon l'action"""
        if self.action == 'create':
            return [PeutCreerDemande()]
        elif self.action in ['approuver', 'rejeter']:
            return [IsAuthenticated(), EstApprobateur()]
        elif self.action == 'retrieve':
            # Le demandeur ou un approbateur peut voir les détails
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Seul le demandeur peut modifier/supprimer (et seulement si en attente)
            return [IsAuthenticated(), EstDemandeur()]
        return super().get_permissions()
    
    def get_queryset(self):
        """
        Filtre les demandes selon le rôle de l'utilisateur:
        - Demandeur: voit ses propres demandes
        - Approbateur: voit les demandes qu'il peut approuver + celles qu'il a traitées
        - Superuser: voit tout
        """
        user = self.request.user
        
        if user.is_admin:
            return DemandeAutorisation.objects.select_related(
                'demandeur', 'approbateur', 'content_type'
            ).all()
        
        # Les demandes que l'utilisateur peut voir
        # 1. Ses propres demandes
        mes_demandes = DemandeAutorisation.objects.filter(demandeur=user)
        
        # 2. Les demandes qu'il peut approuver (selon ses permissions)
        types_autorises = PermissionModel.objects.filter(
            utilisateur=user,
            actif=True
        ).values_list('type_operation', flat=True)
        
        demandes_a_approuver = DemandeAutorisation.objects.filter(
            type_operation__in=types_autorises
        )
        
        # 3. Les demandes qu'il a déjà traitées
        demandes_traitees = DemandeAutorisation.objects.filter(approbateur=user)
        
        # Union des trois querysets
        return (mes_demandes | demandes_a_approuver | demandes_traitees).select_related(
            'demandeur', 'approbateur', 'content_type'
        ).distinct()
    
    def perform_create(self, serializer):
        """Crée la demande et envoie les notifications"""
        demande = serializer.save()
        
        # Envoyer la notification de manière asynchrone
        envoyer_notification_nouvelle_demande.delay(demande.id)
    
    def perform_update(self, serializer):
        """Empêche la modification si la demande n'est plus en attente"""
        if serializer.instance.statut != StatutDemande.EN_ATTENTE:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Seules les demandes en attente peuvent être modifiées")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Empêche la suppression si la demande n'est plus en attente"""
        if instance.statut != StatutDemande.EN_ATTENTE:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Seules les demandes en attente peuvent être supprimées")
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def mes_demandes(self, request):
        """
        Liste toutes les demandes créées par l'utilisateur connecté
        
        GET /api/autorisations/demandes/mes_demandes/
        Query params: ?statut=PENDING&type_operation=ANNUL_ENC
        """
        demandes = DemandeAutorisation.objects.filter(
            demandeur=request.user
        ).select_related('demandeur', 'approbateur', 'content_type')
        
        # Appliquer les filtres
        statut = request.query_params.get('statut')
        if statut:
            demandes = demandes.filter(statut=statut)
        
        type_op = request.query_params.get('type_operation')
        if type_op:
            demandes = demandes.filter(type_operation=type_op)
        
        page = self.paginate_queryset(demandes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(demandes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def en_attente(self, request):
        """
        Liste les demandes en attente que l'utilisateur peut approuver
        
        GET /api/autorisations/demandes/en_attente/
        """
        # Récupérer les types d'opérations que l'utilisateur peut approuver
        types_autorises = PermissionModel.objects.filter(
            utilisateur=request.user,
            actif=True
        ).values_list('type_operation', flat=True)
        
        if not types_autorises:
            return Response({
                'count': 0,
                'results': [],
                'message': "Vous n'avez pas de permissions d'approbation"
            })
        
        demandes = DemandeAutorisation.objects.filter(
            type_operation__in=types_autorises,
            statut=StatutDemande.EN_ATTENTE
        ).select_related('demandeur', 'content_type').order_by('-date_demande')
        
        page = self.paginate_queryset(demandes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(demandes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def approuvees(self, request):
        """
        Liste les demandes approuvées
        
        GET /api/autorisations/demandes/approuvees/
        """
        demandes = self.get_queryset().filter(
            statut=StatutDemande.APPROUVEE
        ).order_by('-date_traitement')
        
        page = self.paginate_queryset(demandes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(demandes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def rejetees(self, request):
        """
        Liste les demandes rejetées
        
        GET /api/autorisations/demandes/rejetees/
        """
        demandes = self.get_queryset().filter(
            statut=StatutDemande.REJETEE
        ).order_by('-date_traitement')
        
        page = self.paginate_queryset(demandes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(demandes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def utilisees(self, request):
        """
        Liste les demandes dont le jeton a été utilisé
        
        GET /api/autorisations/demandes/utilisees/
        """
        demandes = self.get_queryset().filter(
            statut=StatutDemande.UTILISEE
        ).order_by('-updated_at')
        
        page = self.paginate_queryset(demandes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(demandes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def statistiques(self, request):
        """
        Retourne des statistiques sur les demandes
        
        GET /api/autorisations/demandes/statistiques/
        """
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'en_attente': queryset.filter(statut=StatutDemande.EN_ATTENTE).count(),
            'approuvees': queryset.filter(statut=StatutDemande.APPROUVEE).count(),
            'rejetees': queryset.filter(statut=StatutDemande.REJETEE).count(),
            'utilisees': queryset.filter(statut=StatutDemande.UTILISEE).count(),
            'expirees': queryset.filter(statut=StatutDemande.EXPIREE).count(),
        }
        
        # Si l'utilisateur est demandeur
        if not request.user.is_admin:
            stats['mes_demandes'] = {
                'total': queryset.filter(demandeur=request.user).count(),
                'en_attente': queryset.filter(
                    demandeur=request.user,
                    statut=StatutDemande.EN_ATTENTE
                ).count(),
            }
        
        # Si l'utilisateur est approbateur
        types_autorises = PermissionModel.objects.filter(
            utilisateur=request.user,
            actif=True
        ).values_list('type_operation', flat=True)
        
        if types_autorises:
            stats['a_traiter'] = queryset.filter(
                type_operation__in=types_autorises,
                statut=StatutDemande.EN_ATTENTE
            ).count()
        
        return Response(stats)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, EstApprobateur])
    def approuver(self, request, pk=None):
        """
        Approuve une demande d'autorisation et génère un jeton
        
        POST /api/autorisations/demandes/{id}/approuver/
        Body: {
            "duree_validite_heures": 24  // optionnel, défaut: 24h
        }
        """
        demande = cast(DemandeAutorisation, self.get_object())
        
        # Vérifier le statut
        if demande.statut != StatutDemande.EN_ATTENTE:
            return Response({
                'error': f'Cette demande a déjà été traitée (statut: {demande.get_statut_display()})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validation
        serializer = ApprouverDemandeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        duree_heures = serializer.validated_data['duree_validite_heures']
        
        # Transaction atomique
        with transaction.atomic():
            # Approuver la demande
            demande.approuver(request.user)
            
            # Créer le jeton
            jeton = JetonAutorisation.objects.create(
                demande=demande,
                date_expiration=timezone.now() + timedelta(hours=duree_heures)
            )
            
            # Marquer que le jeton a été généré
            demande.jeton_genere = True
            demande.date_expiration = jeton.date_expiration
            demande.save()
        
        # Envoyer le jeton par email de manière asynchrone
        envoyer_jeton_autorisation.delay(jeton.id)
        
        return Response({
            'message': 'Demande approuvée avec succès',
            'demande': DemandeAutorisationDetailSerializer(demande).data,
            'jeton': JetonAutorisationSerializer(jeton).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, EstApprobateur])
    def rejeter(self, request, pk=None):
        """
        Rejette une demande d'autorisation
        
        POST /api/autorisations/demandes/{id}/rejeter/
        Body: {
            "motif_rejet": "Raison du rejet..."
        }
        """
        demande = cast(DemandeAutorisation, self.get_object())
        
        # Vérifier le statut
        if demande.statut != StatutDemande.EN_ATTENTE:
            return Response({
                'error': f'Cette demande a déjà été traitée (statut: {demande.get_statut_display()})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validation
        serializer = RejeterDemandeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        motif = serializer.validated_data['motif_rejet']
        
        # Rejeter la demande
        with transaction.atomic():
            demande.rejeter(request.user, motif)
        
        # Envoyer la notification de rejet de manière asynchrone
        envoyer_notification_rejet.delay(demande.id)
        
        return Response({
            'message': 'Demande rejetée avec succès',
            'demande': DemandeAutorisationDetailSerializer(demande).data
        }, status=status.HTTP_200_OK)

    
    @action(detail=False, methods=['get'])
    def par_periode(self, request):
        """
        Retourne les demandes dans une plage de dates spécifique
        
        GET /api/autorisations/demandes/par_periode/
        Query params: 
        - date_debut: Date de début (YYYY-MM-DD)
        - date_fin: Date de fin (YYYY-MM-DD) (optionnel, défaut: aujourd'hui)
        - champ_date: 'date_demande' ou 'date_traitement' (optionnel, défaut: 'date_demande')
        """
        date_debut_str = request.query_params.get('date_debut')
        date_fin_str = request.query_params.get('date_fin', timezone.now().date().isoformat())
        champ_date = request.query_params.get('champ_date', 'date_demande')  # 'date_demande' ou 'date_traitement'
        
        # Validation des paramètres
        if not date_debut_str:
            return Response(
                {'erreur': 'Le paramètre "date_debut" est requis (format: YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        
        date_debut = parse_date_string(date_debut_str)
        date_fin = parse_date_string(date_fin_str)
        if date_debut is None or date_fin is None:
            return Response(
                {'erreur': 'Format de date invalide. Utilisez le format YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        date_debut = date_debut.date()
        date_fin = date_fin.date()
        
        # Vérifier que la date de début est antérieure à la date de fin
        if date_debut > date_fin:
            return Response(
                {'erreur': 'La date de début doit être antérieure ou égale à la date de fin'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que le champ_date est valide
        if champ_date not in ['date_demande', 'date_traitement']:
            return Response(
                {'erreur': 'Le champ_date doit être "date_demande" ou "date_traitement"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filtrer les demandes
        queryset = self.get_queryset()
        
        # Construire le filtre dynamiquement
        filter_kwargs = {
            f'{champ_date}__date__gte': date_debut,
            f'{champ_date}__date__lte': date_fin
        }
        
        demandes = queryset.filter(**filter_kwargs).order_by(f'-{champ_date}')
        
        # Appliquer les filtres supplémentaires si présents
        statut = request.query_params.get('statut')
        if statut:
            demandes = demandes.filter(statut=statut)
        
        type_op = request.query_params.get('type_operation')
        if type_op:
            demandes = demandes.filter(type_operation=type_op)
        
        # Pagination
        page = self.paginate_queryset(demandes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(demandes, many=True)
        
        return Response({
            'date_debut': date_debut_str,
            'date_fin': date_fin_str,
            'champ_date': champ_date,
            'total': demandes.count(),
            'resultats': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def aujourdhui(self, request):
        """
        Retourne les demandes créées aujourd'hui
        
        GET /api/autorisations/demandes/aujourdhui/
        Query params: statut, type_operation
        """
        aujourdhui = timezone.now().date()
        
        queryset = self.get_queryset().filter(date_demande__date=aujourdhui)
        
        # Appliquer les filtres supplémentaires si présents
        statut = request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        type_op = request.query_params.get('type_operation')
        if type_op:
            queryset = queryset.filter(type_operation=type_op)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'date': aujourdhui.isoformat(),
            'total': queryset.count(),
            'resultats': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def cette_semaine(self, request):
        """
        Retourne les demandes de la semaine en cours
        
        GET /api/autorisations/demandes/cette_semaine/
        """
        aujourdhui = timezone.now().date()
        debut_semaine = aujourdhui - timedelta(days=aujourdhui.weekday())
        fin_semaine = debut_semaine + timedelta(days=6)
        
        queryset = self.get_queryset().filter(
            date_demande__date__gte=debut_semaine,
            date_demande__date__lte=fin_semaine
        )
        
        # Appliquer les filtres supplémentaires si présents
        statut = request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        type_op = request.query_params.get('type_operation')
        if type_op:
            queryset = queryset.filter(type_operation=type_op)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'debut_semaine': debut_semaine.isoformat(),
            'fin_semaine': fin_semaine.isoformat(),
            'total': queryset.count(),
            'resultats': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def ce_mois(self, request):
        """
        Retourne les demandes du mois en cours
        
        GET /api/autorisations/demandes/ce_mois/
        """
        aujourdhui = timezone.now().date()
        debut_mois = aujourdhui.replace(day=1)
        
        # Calculer le dernier jour du mois
        if aujourdhui.month == 12:
            fin_mois = aujourdhui.replace(year=aujourdhui.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fin_mois = aujourdhui.replace(month=aujourdhui.month + 1, day=1) - timedelta(days=1)
        
        queryset = self.get_queryset().filter(
            date_demande__date__gte=debut_mois,
            date_demande__date__lte=fin_mois
        )
        
        # Appliquer les filtres supplémentaires si présents
        statut = request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        type_op = request.query_params.get('type_operation')
        if type_op:
            queryset = queryset.filter(type_operation=type_op)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'debut_mois': debut_mois.isoformat(),
            'fin_mois': fin_mois.isoformat(),
            'total': queryset.count(),
            'resultats': serializer.data
        })

class JetonAutorisationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet en lecture seule pour les jetons d'autorisation
    
    Endpoints disponibles:
    - list: Liste les jetons (filtrés par utilisateur)
    - retrieve: Détails d'un jeton
    - verifier: Vérifie la validité d'un jeton
    - mes_jetons: Liste les jetons de l'utilisateur
    """
    queryset = JetonAutorisation.objects.all()
    serializer_class = JetonAutorisationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['utilise', 'demande__statut']
    ordering_fields = ['date_generation', 'date_expiration', 'date_utilisation']
    ordering = ['-date_generation']
    
    def get_queryset(self):
        """Filtre pour n'afficher que les jetons de l'utilisateur"""
        if self.request.user.is_admin:
            return JetonAutorisation.objects.select_related(
                'demande__demandeur', 'demande__approbateur'
            ).all()
        return JetonAutorisation.objects.filter(
            demande__demandeur=self.request.user
        ).select_related('demande__demandeur', 'demande__approbateur')
    
    @action(detail=False, methods=['get'])
    def mes_jetons(self, request):
        """
        Liste tous les jetons de l'utilisateur connecté
        
        GET /api/autorisations/jetons/mes_jetons/
        Query params: ?utilise=false
        """
        jetons = JetonAutorisation.objects.filter(
            demande__demandeur=request.user
        ).select_related('demande__demandeur', 'demande__approbateur')
        
        # Filtrer par utilisation
        utilise = request.query_params.get('utilise')
        if utilise is not None:
            utilise_bool = utilise.lower() in ['true', '1', 'yes', 'oui', 'vrai']
            jetons = jetons.filter(utilise=utilise_bool)
        
        # Filtrer les jetons valides uniquement
        valides_only = request.query_params.get('valides_only')
        if valides_only and valides_only.lower() in ['true', '1', 'yes', 'oui', 'vrai']:
            jetons = jetons.filter(
                utilise=False,
                date_expiration__gt=timezone.now(),
                demande__statut=StatutDemande.APPROUVEE
            )
        
        page = self.paginate_queryset(jetons)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(jetons, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def verifier(self, request):
        """
        Vérifie la validité d'un jeton sans l'utiliser
        
        POST /api/autorisations/jetons/verifier/
        Body: {
            "code": "ABC12345"
        }
        """
        code = request.data.get('code', '').upper().strip()
        
        if not code:
            return Response({
                'valide': False,
                'message': 'Code requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            jeton = JetonAutorisation.objects.select_related(
                'demande__demandeur', 'demande__approbateur'
            ).get(code=code)
            
            # Vérifier que c'est bien le demandeur
            if jeton.demande.demandeur != request.user and not request.user.is_admin:
                return Response({
                    'valide': False,
                    'message': 'Jeton introuvable'
                }, status=status.HTTP_404_NOT_FOUND)
            
            est_valide = jeton.est_valide()
            
            if est_valide:
                return Response({
                    'valide': True,
                    'jeton': JetonAutorisationSerializer(jeton).data,
                    'message': 'Jeton valide',
                    'temps_restant_heures': (jeton.date_expiration - timezone.now()).total_seconds() / 3600
                }, status=status.HTTP_200_OK)
            else:
                if jeton.utilise:
                    message = 'Jeton déjà utilisé'
                    detail = f'Utilisé le {jeton.date_utilisation.strftime("%d/%m/%Y à %H:%M")}'
                elif timezone.now() > jeton.date_expiration:
                    message = 'Jeton expiré'
                    detail = f'Expiré le {jeton.date_expiration.strftime("%d/%m/%Y à %H:%M")}'
                else:
                    message = 'Jeton invalide'
                    detail = 'Le statut de la demande ne permet pas l\'utilisation'
                
                return Response({
                    'valide': False,
                    'message': message,
                    'detail': detail
                }, status=status.HTTP_200_OK)
                
        except JetonAutorisation.DoesNotExist:
            return Response({
                'valide': False,
                'message': 'Jeton introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


class PermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les permissions d'autorisation
    
    Endpoints disponibles:
    - list: Liste toutes les permissions (admin only)
    - create: Créer une permission (admin only)
    - retrieve: Détails d'une permission
    - update/partial_update: Modifier une permission (admin only)
    - destroy: Supprimer une permission (admin only)
    - mes_permissions: Liste les permissions de l'utilisateur connecté
    - approbateurs: Liste les approbateurs par type d'opération
    """
    queryset = PermissionModel.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAdminUser]  # Par défaut, admin only
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_operation', 'actif', 'utilisateur']
    search_fields = ['utilisateur__username', 'utilisateur__email', 'utilisateur__name']
    ordering_fields = ['created_at', 'type_operation']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """Permissions selon l'action"""
        if self.action in ['mes_permissions', 'approbateurs']:
            return [IsAuthenticated()]
        return super().get_permissions()
    
    def get_queryset(self):
        """Optimise les requêtes"""
        return PermissionModel.objects.select_related('utilisateur').all()
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mes_permissions(self, request):
        """
        Liste les permissions de l'utilisateur connecté
        
        GET /api/autorisations/permissions/mes_permissions/
        """
        permissions = PermissionModel.objects.filter(
            utilisateur=request.user
        ).select_related('utilisateur')
        
        serializer = self.get_serializer(permissions, many=True)
        return Response({
            'nombre': permissions.count(),
            'resultats': serializer.data,
            'peut_approuver': permissions.filter(actif=True).exists()
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def approbateurs(self, request):
        """
        Liste les approbateurs par type d'opération
        
        GET /api/autorisations/permissions/approbateurs/
        Query params: ?type_operation=ANNUL_ENC
        """
        type_op = request.query_params.get('type_operation')
        
        if type_op:
            approbateurs = PermissionModel.obtenir_approbateurs(type_op)
            serializer = UserSerializer(approbateurs, many=True)
            return Response({
                'type_operation': type_op,
                'nombre': approbateurs.count(),
                'approbateurs': serializer.data
            })
        else:
            # Retourner tous les approbateurs groupés par type
            from .models import TypeOperation
            resultats = {}
            
            for type_choice in TypeOperation.choices:
                type_code = type_choice[0]
                type_label = type_choice[1]
                approbateurs = PermissionModel.obtenir_approbateurs(type_code)
                
                resultats[type_code] = {
                    'libelle': type_label,
                    'nombre': approbateurs.count(),
                    'approbateurs': [
                        {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'full_name': user.get_full_name() or user.username
                        }
                        for user in approbateurs
                    ]
                }
            
            return Response(resultats)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def utilisateurs(self, request):
        """
        Liste les utilisateurs actifs
        
        GET /api/autorisations/permissions/utilisateurs/
        Query params: ?type_operation=ANNUL_ENC
        """
        users = User.objects.filter(is_active=True)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
          