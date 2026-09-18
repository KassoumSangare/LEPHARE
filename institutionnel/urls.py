from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CrmLeadViewSet,
    CrmInteractionViewSet,
    Customer360View,
    SinistreDelegueViewSet,
    ConventionAssureurViewSet,
    DocumentGEDViewSet,
    AuditLogCimaViewSet,
    QuittanceCimaViewSet,
    BordereauReversementViewSet,
)

router = DefaultRouter()
router.register(r"crm/leads", CrmLeadViewSet, basename="crm-leads")
router.register(r"crm/interactions", CrmInteractionViewSet, basename="crm-interactions")
router.register(r"sinistres", SinistreDelegueViewSet, basename="sinistres-delegues")
router.register(r"conventions", ConventionAssureurViewSet, basename="conventions-assureurs")
router.register(r"ged/documents", DocumentGEDViewSet, basename="ged-documents")
router.register(r"compliance/audit-trail", AuditLogCimaViewSet, basename="compliance-audit")
router.register(r"quittances-cima", QuittanceCimaViewSet, basename="quittances-cima")
router.register(r"reversements-cima", BordereauReversementViewSet, basename="reversements-cima")

urlpatterns = [
    path("", include(router.urls)),
    path("crm/clients/<int:client_id>/360/", Customer360View.as_view(), name="customer-360-detail"),
    path("crm/clients/360/", Customer360View.as_view(), name="customer-360-default"),
]
