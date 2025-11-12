from django.urls import include, path
from rest_framework import routers
from .views import (
    CertificateApplicationViewSet,
    CertificateStatusUpdateViewset,
    RetrieveApplicationInfoViewset,
    CheckApplicationStatusViewset,
    RetourDemAttestationViewSet,
    DetailRetourDemAttestationViewSet,
    CertificateDbApplicationViewSet,
)

router = routers.DefaultRouter()

router.register(
    r"asaci/demandeattestationexcel",
    CertificateApplicationViewSet,
    basename="demandeattestationexcel",
)
router.register(
    r"asaci/demandeattestationdb",
    CertificateDbApplicationViewSet,
    basename="demandeattestationdb",
)

router.register(
    r"asaci/majstatutattestation",
    CertificateStatusUpdateViewset,
    basename="majstatutattestation",
)
router.register(
    r"asaci/obtentioninfo",
    RetrieveApplicationInfoViewset,
    basename="obtentioninfo",
)
router.register(
    r"asaci/verificationstatutdemande",
    CheckApplicationStatusViewset,
    basename="verificationstatutdemande",
)

router.register(
    r"asaci/retourdemandeattestation",
    RetourDemAttestationViewSet,
    # basename="retourdemandeattestation",
)

router.register(
    r"asaci/detailretourdemandeattestation",
    DetailRetourDemAttestationViewSet,
    # basename="detailretourdemandeattestation",
)

urlpatterns = [
    path("", include(router.urls)),
]
