from django.urls import path, include
from .views import (
    ArolitecSMSAckView,
    ArolitecSMSMoView,
)

from rest_framework import routers


router = routers.DefaultRouter()

urlpatterns = [
    path(
        r"messaging/arolitec/smsack",
        ArolitecSMSAckView.as_view(),
        name="arolitec_sms_acknowlegment",
    ),
    path(
        r"messaging/arolitec/smsmo", ArolitecSMSMoView.as_view(), name="arolitec_sms_mo"
    ),
    path("", include(router.urls)),
]
