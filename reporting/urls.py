from django.urls import include, path

from rest_framework import routers

from .views import EtatDecisionnelViewSet, EtatCimaE1View, EtatCimaE2View
from .views import get_emission_for_bordereau_recap, EtatDecisionnelContenuView


router = routers.DefaultRouter()
router.register(r"etatdecisionnel", EtatDecisionnelViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        r"bordereaurecapemission",
        get_emission_for_bordereau_recap,
        name="bordereau_recap_emission",
    ),
    path(
        r"cimaetate1/<int:exercice>",
        EtatCimaE1View.as_view(),
        name="emissions_encaissements_commissions",
    ),
    path(
        r"cimaetate2/<int:exercice>",
        EtatCimaE2View.as_view(),
        name="arrieres_encaissements_annulations",
    ),
    path(
        r"etatdecisionnel/<int:pk>/contenu",
        EtatDecisionnelContenuView.as_view(),
        name="etat_decisionnel_contenu",
    ),
]
