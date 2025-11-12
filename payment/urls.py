from django.urls import include, path

from rest_framework import routers

from .views import DistripayTransactionViewSet, PaiementMobileInfoView

from .views import initiate_mobile_payment

router = routers.DefaultRouter()
router.register(r"distripaytransaction", DistripayTransactionViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path(
        r"initiationpaiementmobile",
        initiate_mobile_payment,
        name="inititiation_paiement_mobile",
    ),
    # path(
    #     r"verificationpaiementmobile",
    #     verify_mobile_payment,
    #     name="verification_paiement_mobile",
    # ),
    path(
        r"paiementmobileinfo/<slug:idtransaction>",
        PaiementMobileInfoView.as_view(),
        name="paiement_mobile_info",
    ),
]
