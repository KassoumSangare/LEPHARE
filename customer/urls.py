from django.urls import include, path

from rest_framework import routers

from .views import *

router = routers.DefaultRouter()
router.register(r"client", ClientViewSet)
router.register(r"clientrestreint", ClientRestreintViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path(
        r"clientrecherche/<str:champrecherche>",
        ClientRechercheView.as_view(),
        name="client_recherche",
    ),
]
