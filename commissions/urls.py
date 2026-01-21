# commissions/urls.py
"""
Configuration des URLs pour l'API de gestion des commissions
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaiementCommissionViewSet,
    PaiementCommissionBatchViewSet,
    DetailPaiementCommissionViewSet,
    AnnulationPaiementCommissionViewSet,
    AffaireCommissionViewSet,
    DashboardCommissionViewSet,
    SnapshotCommissionViewSet,
    NotificationCommissionViewSet
)

# Configuration du router
router = DefaultRouter()

# Enregistrement des ViewSets
router.register(
    r'paiements-commission',
    PaiementCommissionViewSet,
    basename='paiement-commission'
)

router.register(
    r'paiements-batch',
    PaiementCommissionBatchViewSet,
    basename='paiement-batch'
)

router.register(
    r'details-paiement-commission',
    DetailPaiementCommissionViewSet,
    basename='detail-paiement-commission'
)

router.register(
    r'annulations-commission',
    AnnulationPaiementCommissionViewSet,
    basename='annulation-commission'
)

router.register(
    r'affaires-commission',
    AffaireCommissionViewSet,
    basename='affaire-commission'
)

router.register(
    r'dashboard',
    DashboardCommissionViewSet,
    basename='dashboard-commission'
)

router.register(
    r'snapshots',
    SnapshotCommissionViewSet,
    basename='snapshot-commission'
)

router.register(
    r'notifications',
    NotificationCommissionViewSet,
    basename='notification-commission'
)

# URLs de l'application
urlpatterns = [
    path('', include(router.urls)),
]