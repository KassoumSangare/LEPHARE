"""
Vues Django REST Framework pour l'API de gestion des commissions
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import (
       Sum, Count, Avg, F, Q, Case, When,
       DecimalField,
       OuterRef, Subquery, Max, Value
   )
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

from .models import (
    PaiementCommission,
    DetailPaiementCommission,
    AnnulationPaiementCommission,
    NotificationCommission,
    SnapshotCommission,
)
from .serializers import (
    PaiementCommissionSerializer,
    DetailPaiementCommissionEnrichedSerializer,
    PaiementCommissionBatchSerializer,
    AnnulationPaiementCommissionSerializer,
    AnnulerSelectionSerializer,
    RechercheAffairePourPaiementSerializer,
    NotificationCommissionSerializer,
    SnapshotCommissionListSerializer,
    SnapshotCommissionSerializer,
)
from .services import (
    CommissionCalculService,
    CommissionCacheService,
    AffaireCommissionService,
    PaiementCommissionService
)


# =====================================================
# ViewSets pour Paiements
# =====================================================

class PaiementCommissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les paiements de commission
    """
    queryset = PaiementCommission.objects.select_related(
        'compagnie', 'created_by'
    ).prefetch_related('details__quittance__contrat')
    serializer_class = PaiementCommissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'notes']
    ordering_fields = ['date_paiement', 'montant_total', 'created_at']
    ordering = ['-date_paiement']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtres
        statut = self.request.query_params.get('statut')
        compagnie_id = self.request.query_params.get('compagnie')
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        
        if statut:
            queryset = queryset.filter(statut=statut)
        if compagnie_id:
            queryset = queryset.filter(compagnie_id=compagnie_id)
        if date_debut:
            queryset = queryset.filter(date_paiement__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date_paiement__lte=date_fin)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        """Valider un paiement de commission"""
        paiement = self.get_object()
        
        if paiement.statut == 'VALIDE':
            return Response({
                'erreur': 'Ce paiement est déjà validé'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        paiement.statut = 'VALIDE'
        paiement.save()
        
        # Invalider le cache des dashboards
        CommissionCacheService.invalider_cache()
        
        serializer = self.get_serializer(paiement)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """Statistiques sur les paiements de commissions"""
        queryset = self.get_queryset()
        
        stats = queryset.aggregate(
            total_paiements=Count('pk'),
            montant_total=Sum('montant_total'),
            montant_en_attente=Sum(
                'montant_total',
                filter=Q(statut='EN_ATTENTE')
            ),
            montant_traite=Sum(
                'montant_total',
                filter=Q(statut='TRAITE')
            ),
            montant_valide=Sum(
                'montant_total',
                filter=Q(statut='VALIDE')
            )
        )
        
        # Convertir les Decimal en string
        for key, value in stats.items():
            if isinstance(value, Decimal):
                stats[key] = str(value) if value else '0.00'
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def rapport(self, request, pk=None):
        """Générer un rapport détaillé du paiement"""
        paiement = self.get_object()
        
        details = paiement.details.filter(
            est_annule=False
        ).select_related(
            'quittance__client',
            'detail_reversement'
        ).values(
            'id',
            'quittance__numeroquittance',
            'quittance__police',
            'quittance__client__Nom',
            'quittance__client__Prenoms',
            'montant_prime_reversee',
            'taux_commission',
            'montant_commission_du',
            'montant_commission_paye',
            'reference_affaire'
        )
        
        total_commissions = paiement.details.filter(
            est_annule=False
        ).aggregate(
            total=Sum('montant_commission_paye')
        )['total'] or Decimal('0.00')
        
        return Response({
            'paiement': PaiementCommissionSerializer(paiement).data,
            'details': list(details),
            'resume': {
                'nombre_affaires': details.count(),
                'total_commissions': str(total_commissions)
            }
        })


class PaiementCommissionBatchViewSet(viewsets.ViewSet):
    """
    ViewSet pour l'enregistrement de paiements par lot
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def create(self, request):
        """
        Enregistrer un paiement de commissions par lot
        """
        serializer = PaiementCommissionBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Créer le paiement via le service
        paiement = PaiementCommissionService.creer_paiement_batch(
            serializer.validated_data,
            request.user
        )
        
        # Invalider le cache
        CommissionCacheService.invalider_cache()
        
        # Retourner le paiement créé
        output_serializer = PaiementCommissionSerializer(paiement)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )


# =====================================================
# ViewSets pour Détails de Paiement
# =====================================================

class DetailPaiementCommissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les détails de paiement individuels
    """
    serializer_class = DetailPaiementCommissionEnrichedSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'quittance__numeroquittance',
        'quittance__police',
        'quittance__client__Nom',
        'quittance__client__Prenoms',
        'reference_affaire'
    ]
    ordering_fields = [
        'paiement__date_paiement',
        'montant_commission_paye',
        'created_at'
    ]
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = DetailPaiementCommission.objects.select_related(
            'paiement__compagnie',
            'quittance__client',
            'quittance__contrat__idcompagnie',
            'detail_reversement'
        ).prefetch_related('annulation')
        
        # Filtres
        est_annule = self.request.query_params.get('est_annule')
        compagnie_id = self.request.query_params.get('compagnie')
        paiement_id = self.request.query_params.get('paiement')
        date_paiement_debut = self.request.query_params.get('date_paiement_debut')
        date_paiement_fin = self.request.query_params.get('date_paiement_fin')
        peut_etre_annule = self.request.query_params.get('peut_etre_annule')
        
        if est_annule is not None:
            queryset = queryset.filter(est_annule=est_annule.lower() == 'true')
        
        if compagnie_id:
            queryset = queryset.filter(paiement__compagnie_id=compagnie_id)
        
        if paiement_id:
            queryset = queryset.filter(paiement_id=paiement_id)
        
        if date_paiement_debut:
            queryset = queryset.filter(paiement__date_paiement__gte=date_paiement_debut)
        
        if date_paiement_fin:
            queryset = queryset.filter(paiement__date_paiement__lte=date_paiement_fin)
        
        if peut_etre_annule and peut_etre_annule.lower() == 'true':
            queryset = queryset.filter(
                est_annule=False,
                paiement__statut__in=['EN_ATTENTE', 'TRAITE']
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def annulables(self, request):
        """Liste des détails de paiement qui peuvent être annulés"""
        queryset = self.get_queryset().filter(
            est_annule=False,
            paiement__statut__in=['EN_ATTENTE', 'TRAITE']
        )
        
        queryset = self.filter_queryset(queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def annuler_selection(self, request):
        """Annuler une sélection de lignes de paiement"""
        serializer = AnnulerSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return self._process_annulation(
            serializer.validated_data,
            request.user
        )
    
    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        """Annuler une seule ligne de paiement"""
        detail = self.get_object()
        
        if detail.est_annule:
            return Response(
                {'error': 'Ce paiement est déjà annulé'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if detail.paiement.statut == 'VALIDE':
            return Response(
                {'error': 'Impossible d\'annuler un paiement validé'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        motif = request.data.get('motif')
        if not motif:
            return Response(
                {'error': 'Le motif est obligatoire'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer l'annulation
        return self._process_annulation(
            {
                'reference': f'ANN-{detail.id}-{timezone.now().strftime("%Y%m%d%H%M%S")}',
                'motif': motif,
                'details_paiement_ids': [detail.id],
                'commentaires': {str(detail.id): request.data.get('commentaire', '')}
            },
            request.user
        )
    
    @transaction.atomic
    def _process_annulation(self, data, user):
        """Traite l'annulation des paiements"""
        # Vérifier que tous les détails peuvent être annulés
        details = DetailPaiementCommission.objects.filter(
            id__in=data['details_paiement_ids']
        ).select_related('paiement')
        
        errors = []
        for detail in details:
            if detail.est_annule:
                errors.append(f"Ligne {detail.id}: déjà annulée")
            if detail.paiement.statut == 'VALIDE':
                errors.append(f"Ligne {detail.id}: paiement validé, annulation impossible")
        
        if errors:
            return Response(
                {'errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer l'annulation via le service
        annulation = PaiementCommissionService.annuler_paiements(data, user)
        
        # Invalider le cache
        CommissionCacheService.invalider_cache()
        
        # Retourner l'annulation créée
        output_serializer = AnnulationPaiementCommissionSerializer(annulation)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def verifier_selection(self, request):
        """Vérifier si une sélection de lignes peut être annulée"""
        detail_ids = request.data.get('detail_ids', [])
        
        if not detail_ids:
            return Response(
                {'erreur': 'Aucune ligne sélectionnée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        details = DetailPaiementCommission.objects.filter(
            id__in=detail_ids
        ).select_related('paiement', 'quittance')
        
        if details.count() != len(detail_ids):
            return Response(
                {'error': 'Certaines lignes n\'existent pas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier chaque ligne
        results = []
        total_annulable = Decimal('0.00')
        
        for detail in details:
            peut_annuler = not detail.est_annule and detail.paiement.statut != 'VALIDE'
            
            if peut_annuler:
                total_annulable += detail.montant_commission_paye
            
            results.append({
                'detail_id': detail.id,
                'quittance_numero': detail.quittance.numeroquittance,
                'montant': str(detail.montant_commission_paye),
                'peut_annuler': peut_annuler,
                'raison': self._get_raison_non_annulable(detail) if not peut_annuler else None
            })
        
        return Response({
            'details': results,
            'nombre_total': len(detail_ids),
            'nombre_annulable': sum(1 for r in results if r['peut_annuler']),
            'montant_total_annulable': str(total_annulable)
        })
    
    def _get_raison_non_annulable(self, detail):
        """Retourne la raison pour laquelle un détail ne peut pas être annulé"""
        if detail.est_annule:
            return "Déjà annulé"
        if detail.paiement.statut == 'VALIDE':
            return "Paiement validé"
        return "Raison inconnue"


# =====================================================
# ViewSets pour Annulations
# =====================================================

class AnnulationPaiementCommissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les annulations de paiements de commission
    """
    queryset = AnnulationPaiementCommission.objects.prefetch_related(
        'details_annules__quittance__contrat'
    )
    serializer_class = AnnulationPaiementCommissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'motif']
    ordering = ['-date_annulation']
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Récupérer les détails d'une annulation"""
        from .models import DetailAnnulation
        
        annulation = self.get_object()
        
        details_annulation = DetailAnnulation.objects.filter(
            annulation=annulation
        ).select_related(
            'detail_paiement__quittance__contrat',
            'detail_paiement__paiement'
        )
        
        data = [
            {
                'detail_paiement_id': da.detail_paiement.id,
                'quittance_numero': da.detail_paiement.quittance.numeroquittance,
                'contrat_numero': da.detail_paiement.quittance.police,
                'montant_annule': str(da.detail_paiement.montant_commission_paye),
                'paiement_reference': da.detail_paiement.paiement.reference,
                'commentaire': da.commentaire
            }
            for da in details_annulation
        ]
        
        return Response({
            'annulation': AnnulationPaiementCommissionSerializer(annulation).data,
            'details': data
        })


# =====================================================
# ViewSets pour Affaires
# =====================================================

class AffaireCommissionViewSet(viewsets.ViewSet):
    """
    ViewSet pour gérer l'affichage des affaires selon leur statut de commission
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def eligibles_paiement(self, request):
        """Liste des affaires éligibles au paiement de commission"""
        filtres = {
            'compagnie_id': request.query_params.get('compagnie'),
            'client_nom': request.query_params.get('nom_client'),
            'date_reversement_debut': request.query_params.get('date_reversement_debut'),
            'date_reversement_fin': request.query_params.get('date_reversement_fin'),
            'montant_restant_min': request.query_params.get('montant_min'),
            'statut': request.query_params.get('statut'),
        }
        
        # Supprimer les filtres None
        filtres = {k: v for k, v in filtres.items() if v is not None}
        
        queryset = AffaireCommissionService.get_affaires_eligibles(filtres)
        
        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            data = [AffaireCommissionService.serialiser_affaire(item) for item in page]
            return paginator.get_paginated_response(data)
        
        data = [AffaireCommissionService.serialiser_affaire(item) for item in queryset]
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def rechercher_pour_paiement(self, request):
        """Recherche avancée pour la sélection d'affaires à payer"""
        serializer = RechercheAffairePourPaiementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        criteria = serializer.validated_data
        
        queryset = AffaireCommissionService.get_affaires_eligibles(criteria)
        
        data = [AffaireCommissionService.serialiser_affaire(item) for item in queryset]
        
        # Ajouter un résumé
        resume = queryset.aggregate(
            nombre_affaires=Count('pk'),
            montant_total_restant=Sum('montant_commission_restant')
        )
        
        return Response({
            'affaires': data,
            'resume': {
                'nombre_affaires': resume['nombre_affaires'],
                'montant_total_restant': str(resume['montant_total_restant'] or Decimal('0.00'))
            }
        })
    
    @action(detail=False, methods=['get'])
    def resume_eligibles(self, request):
        """Résumé des affaires éligibles au paiement par compagnie"""
        from django.db.models import OuterRef, Subquery, Coalesce
        from .models import DetailReversement
        
        montant_paye_subquery = CommissionCalculService.get_montant_paye_subquery()
        
        resume = DetailReversement.objects.values(
            'quittance__contrat__compagnie__IdCompagnie',
            'quittance__contrat__compagnie__RaisonSociale'
        ).annotate(
            montant_commission_du_total=Sum(
                F('montant_reverse') * F('taux_commission') / 100
            ),
            montant_commission_paye_total=Sum(
                Coalesce(
                    Subquery(montant_paye_subquery),
                    Decimal('0.00'),
                    output_field=DecimalField(max_digits=15, decimal_places=2)
                )
            )
        ).annotate(
            montant_commission_restant_total=F('montant_commission_du_total') - F('montant_commission_paye_total')
        ).filter(
            montant_commission_restant_total__gt=0
        ).annotate(
            nombre_affaires=Count('pk')
        )
        
        # Convertir en liste avec Decimal en string
        result = []
        for item in resume:
            result.append({
                'compagnie_id': item['quittance__contrat__idcompagnie__IdCompagnie'],
                'compagnie_nom': item['quittance__contrat__idcompagnie__RaisonSociale'],
                'montant_commission_du_total': str(item['montant_commission_du_total'] or Decimal('0.00')),
                'montant_commission_paye_total': str(item['montant_commission_paye_total'] or Decimal('0.00')),
                'montant_commission_restant_total': str(item['montant_commission_restant_total'] or Decimal('0.00')),
                'nombre_affaires': item['nombre_affaires']
            })
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def payees(self, request):
        """Liste des affaires dont les commissions ont été entièrement payées"""
        queryset = CommissionCalculService.get_affaires_annotees().filter(
            statut_paiement='PAYE'
        )
        
        # Filtres
        compagnie_id = request.query_params.get('compagnie')
        nom_client = request.query_params.get('nom_client')
        date_paiement_debut = request.query_params.get('date_paiement_debut')
        date_paiement_fin = request.query_params.get('date_paiement_fin')
        
        if compagnie_id:
            queryset = queryset.filter(quittance__contrat__idcompagnie_IdCompagnie=compagnie_id)
        
        if nom_client:
            queryset = queryset.filter(
                Q(quittance__client__Nom__icontains=nom_client) |
                Q(quittance__client__Prenoms__icontains=nom_client)
            )
        
        if date_paiement_debut or date_paiement_fin:
            # Annoter avec la date du dernier paiement
            queryset = queryset.annotate(
            derniere_date_paiement=Max(
                'details_commission__paiement__date_paiement',
                filter=Q(details_commission__est_annule=False)
            )
        )
            if date_paiement_debut:
                queryset = queryset.filter(
                derniere_date_paiement__gte=date_paiement_debut
            )
            if date_paiement_fin:
                queryset = queryset.filter(
                derniere_date_paiement__lte=date_paiement_fin
            )
        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            data = [AffaireCommissionService.serialiser_affaire(item) for item in page]
            return paginator.get_paginated_response(data)
        
        data = [AffaireCommissionService.serialiser_affaire(item) for item in queryset]
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def non_payees_ou_partielles(self, request):
        """Liste des affaires non ou partiellement payées"""
        queryset = CommissionCalculService.get_affaires_annotees().filter(
            statut_paiement__in=['NON_PAYE', 'PARTIELLEMENT_PAYE']
        )
        
        # Filtres
        nom_client = request.query_params.get('nom_client')
        compagnie_id = request.query_params.get('compagnie')
        
        if nom_client:
            queryset = queryset.filter(
                Q(quittance__client__Nom__icontains=nom_client) |
                Q(quittance__client__Prenoms__icontains=nom_client)
            )
        
        if compagnie_id:
            queryset = queryset.filter(quittance__contrat__idcompagnie_IdCompagnie=compagnie_id)
        
        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            data = [AffaireCommissionService.serialiser_affaire(item) for item in page]
            return paginator.get_paginated_response(data)
        
        data = [AffaireCommissionService.serialiser_affaire(item) for item in queryset]
        return Response(data)


# =====================================================
# ViewSets pour Dashboard
# =====================================================

class DashboardCommissionViewSet(viewsets.ViewSet):
    """
    ViewSet principal pour tous les tableaux de bord
    """
    permission_classes = [IsAuthenticated]
    
    def _parse_date(self, date_str):
        """Parse une date depuis une string"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None
    
    @action(detail=False, methods=['get'])
    def kpi_global(self, request):
        """KPI globaux"""
        date_debut = self._parse_date(request.query_params.get('date_debut'))
        date_fin = self._parse_date(request.query_params.get('date_fin'))
        force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
        
        cle_cache = f'kpi_global_{date_debut}_{date_fin}'
        
        if force_refresh:
            from .models import CacheDashboard
            CacheDashboard.objects.filter(cle=cle_cache).delete()
        
        kpi = CommissionCacheService.get_or_calculate(
            cle_cache,
            CommissionCalculService.calculer_kpi_global,
            duree_minutes=30,
            date_debut=date_debut,
            date_fin=date_fin
        )
        
        kpi['periode_debut'] = date_debut
        kpi['periode_fin'] = date_fin
        kpi['date_calcul'] = timezone.now().isoformat()
        
        return Response(kpi)
    
    @action(detail=False, methods=['get'])
    def par_compagnie(self, request):
        """Statistiques par compagnie"""
        date_debut = self._parse_date(request.query_params.get('date_debut'))
        date_fin = self._parse_date(request.query_params.get('date_fin'))
        ordre = request.query_params.get('ordre', 'commissions_dues')
        
        cle_cache = f'stats_compagnie_{date_debut}_{date_fin}'
        
        stats = CommissionCacheService.get_or_calculate(
            cle_cache,
            CommissionCalculService.calculer_statistiques_par_compagnie,
            duree_minutes=30,
            date_debut=date_debut,
            date_fin=date_fin
        )
        
        # Trier selon le critère
        if ordre == 'taux_recouvrement':
            stats = sorted(stats, key=lambda x: Decimal(x['taux_recouvrement']), reverse=True)
        elif ordre == 'commissions_payees':
            stats = sorted(stats, key=lambda x: Decimal(x['commissions_payees']), reverse=True)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def evolution_mensuelle(self, request):
        """Évolution mensuelle des commissions"""
        annee = int(request.query_params.get('annee', timezone.now().year))
        
        cle_cache = f'evolution_mensuelle_{annee}'
        
        evolution = CommissionCacheService.get_or_calculate(
            cle_cache,
            CommissionCalculService.calculer_evolution_mensuelle,
            duree_minutes=60,
            annee=annee
        )
        
        return Response(evolution)
    
    @action(detail=False, methods=['get'])
    def par_anciennete(self, request):
        """Répartition des commissions en attente par ancienneté"""
        cle_cache = f'par_anciennete_{timezone.now().date()}'
        
        repartition = CommissionCacheService.get_or_calculate(
            cle_cache,
            CommissionCalculService.calculer_commissions_par_anciennete,
            duree_minutes=60
        )
        
        return Response(repartition)
    
    @action(detail=False, methods=['get'])
    def top_affaires(self, request):
        """Top des affaires"""
        limite = int(request.query_params.get('limite', 10))
        critere = request.query_params.get('critere', 'commission_due')
        
        cle_cache = f'top_affaires_{limite}_{critere}'
        
        top = CommissionCacheService.get_or_calculate(
            cle_cache,
            CommissionCalculService.calculer_top_affaires,
            duree_minutes=30,
            limite=limite,
            critere=critere
        )
        
        return Response(top)
    
    @action(detail=False, methods=['get'])
    def performance_paiement(self, request):
        """Performance de paiement (délais par compagnie)"""
        cle_cache = 'performance_paiement'
        
        performance = CommissionCacheService.get_or_calculate(
            cle_cache,
            CommissionCalculService.calculer_performance_paiement,
            duree_minutes=60
        )
        
        return Response(performance)
    
    @action(detail=False, methods=['get'])
    def taux_conformite(self, request):
        """Taux de conformité des paiements"""
        cle_cache = 'taux_conformite'
        
        conformite = CommissionCacheService.get_or_calculate(
            cle_cache,
            CommissionCalculService.calculer_taux_conformite,
            duree_minutes=30
        )
        
        return Response(conformite)
    
    @action(detail=False, methods=['get'])
    def dashboard_complet(self, request):
        """Dashboard complet avec tous les indicateurs"""
        date_debut = self._parse_date(request.query_params.get('date_debut'))
        date_fin = self._parse_date(request.query_params.get('date_fin'))
        
        # Si pas de période, utiliser l'année en cours
        if not date_debut or not date_fin:
            aujourd_hui = timezone.now().date()
            date_debut = datetime(aujourd_hui.year, 1, 1).date()
            date_fin = aujourd_hui
        
        cle_cache = f'dashboard_complet_{date_debut}_{date_fin}'
        
        # Vérifier le cache
        from .models import CacheDashboard
        donnees_cache = CacheDashboard.get_cache(cle_cache)
        if donnees_cache:
            return Response(donnees_cache)
        
        # Calculer tous les indicateurs
        dashboard = {
            'kpi_global': CommissionCalculService.calculer_kpi_global(date_debut, date_fin),
            'par_compagnie': CommissionCalculService.calculer_statistiques_par_compagnie(date_debut, date_fin),
            'par_anciennete': CommissionCalculService.calculer_commissions_par_anciennete(),
            'top_affaires': CommissionCalculService.calculer_top_affaires(limite=10),
            'performance_paiement': CommissionCalculService.calculer_performance_paiement(),
            'taux_conformite': CommissionCalculService.calculer_taux_conformite(),
            'date_generation': timezone.now().isoformat(),
            'periode': {
                'debut': date_debut.isoformat() if date_debut else None,
                'fin': date_fin.isoformat() if date_fin else None
            }
        }
        
        # Sérialiser et mettre en cache
        dashboard_serialise = CommissionCacheService._serialiser_decimals(dashboard)
        CacheDashboard.set_cache(cle_cache, dashboard_serialise, duree_minutes=30)
        
        return Response(dashboard_serialise)
    
    @action(detail=False, methods=['post'])
    def invalider_cache(self, request):
        """Invalide le cache des dashboards"""
        pattern = request.data.get('pattern')
        
        CommissionCacheService.invalider_cache(pattern)
        
        return Response({
            'message': 'Cache invalidé avec succès',
            'pattern': pattern or 'all'
        })


# =====================================================
# ViewSets pour Snapshots
# =====================================================

class SnapshotCommissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour consulter les snapshots historiques
    
    Endpoints:
    - GET /api/commissions/snapshots/ : Liste des snapshots
    - GET /api/commissions/snapshots/{id}/ : Détail d'un snapshot
    - GET /api/commissions/snapshots/latest/ : Dernier snapshot
    - GET /api/commissions/snapshots/evolution/ : Évolution sur une période
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date_snapshot']
    ordering = ['-date_snapshot']
    
    def get_serializer_class(self):
        """Utiliser un serializer simplifié pour la liste"""
        if self.action == 'list':
            return SnapshotCommissionListSerializer
        return SnapshotCommissionSerializer
    
    def get_queryset(self):
        queryset = SnapshotCommission.objects.prefetch_related(
            'details_compagnie__compagnie'
        )
        
        # Filtres
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        
        if date_debut:
            queryset = queryset.filter(date_snapshot__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date_snapshot__lte=date_fin)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Récupère le dernier snapshot disponible"""
        snapshot = self.get_queryset().first()
        
        if not snapshot:
            return Response(
                {'erreur': 'Aucun snapshot disponible'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(snapshot)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def evolution(self, request):
        """
        Retourne l'évolution des KPI sur une période
        
        Paramètres:
        - date_debut (requis): Date de début (YYYY-MM-DD)
        - date_fin (requis): Date de fin (YYYY-MM-DD)
        """
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        
        if not date_debut or not date_fin:
            return Response(
                {'erreur': 'date_debut et date_fin sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            date_snapshot__gte=date_debut,
            date_snapshot__lte=date_fin
        ).order_by('date_snapshot')
        
        serializer = SnapshotCommissionListSerializer(queryset, many=True)
        
        return Response({
            'periode': {
                'debut': date_debut,
                'fin': date_fin
            },
            'nombre_snapshots': queryset.count(),
            'evolution': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def comparaison(self, request):
        """
        Compare deux périodes
        
        Paramètres:
        - periode1_debut, periode1_fin
        - periode2_debut, periode2_fin
        """
        p1_debut = request.query_params.get('periode1_debut')
        p1_fin = request.query_params.get('periode1_fin')
        p2_debut = request.query_params.get('periode2_debut')
        p2_fin = request.query_params.get('periode2_fin')
        
        if not all([p1_debut, p1_fin, p2_debut, p2_fin]):
            return Response(
                {'erreur': 'Toutes les dates sont requises'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Période 1
        snapshots_p1 = self.get_queryset().filter(
            date_snapshot__gte=p1_debut,
            date_snapshot__lte=p1_fin
        )
        
        # Période 2
        snapshots_p2 = self.get_queryset().filter(
            date_snapshot__gte=p2_debut,
            date_snapshot__lte=p2_fin
        )
        
        # Calculer les moyennes
        def calculer_moyennes(snapshots):
            if not snapshots.exists():
                return None
            
            aggregations = snapshots.aggregate(
                avg_commissions_dues=Avg('commissions_dues_total'),
                avg_commissions_payees=Avg('commissions_payees_total'),
                avg_taux_recouvrement=Avg('taux_recouvrement'),
                avg_delai_paiement=Avg('delai_moyen_paiement_jours'),
            )
            
            return {
                'commissions_dues_moyenne': str(aggregations['avg_commissions_dues'] or 0),
                'commissions_payees_moyenne': str(aggregations['avg_commissions_payees'] or 0),
                'taux_recouvrement_moyen': str(aggregations['avg_taux_recouvrement'] or 0),
                'delai_moyen_paiement': aggregations['avg_delai_paiement'] or 0,
                'nombre_snapshots': snapshots.count()
            }
        
        return Response({
            'periode1': {
                'dates': {'debut': p1_debut, 'fin': p1_fin},
                'statistiques': calculer_moyennes(snapshots_p1)
            },
            'periode2': {
                'dates': {'debut': p2_debut, 'fin': p2_fin},
                'statistiques': calculer_moyennes(snapshots_p2)
            }
        })

# =====================================================
# ViewSets pour Notifications
# =====================================================

class NotificationCommissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les notifications
    """
    serializer_class = NotificationCommissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Filtrer par utilisateur connecté
        return NotificationCommission.objects.filter(
            utilisateur=self.request.user
        )
    
    @action(detail=False, methods=['get'])
    def non_lues(self, request):
        """Liste des notifications non lues"""
        notifications = self.get_queryset().filter(lue=False)
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def marquer_lue(self, request, pk=None):
        """Marquer une notification comme lue"""
        notification = self.get_object()
        notification.marquer_comme_lue()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def marquer_toutes_lues(self, request):
        """Marquer toutes les notifications comme lues"""
        self.get_queryset().filter(lue=False).update(
            lue=True,
            date_lecture=timezone.now()
        )
        return Response({'message': 'Toutes les notifications ont été marquées comme lues'})