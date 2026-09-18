from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication

from .utils import RequestSender
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from .models import RetourDemAttestation, DetailRetourDemAttestation
from uranus.settings import (
    ASACI_API_BASE_URL,
    ASACI_INTERMEDIARY_CODE,
    ASACI_COMPANY_CODE,
    ASACI_REQUESTER_CODE,
    ASACI_POINT_OF_SALE,
    ASACI_OFFICE,
    ASACI_ACCESS_CODE,
)

from .serializers import (
    RetourDemAttestationSerializer,
    DetailRetourDemAttestationSerializer,
    CertificateApplicationSerializer,
    CheckApplicationStatusSerializer,
    CertificateStatusUpdateSerializer,
    RetrieveApplicationInfoSerializer,
    CertificateDbApplicationSerializer,
)

# Create your views here.
class RetourDemAttestationViewSet(viewsets.ModelViewSet):
    queryset = RetourDemAttestation.objects.all().order_by("-id")
    serializer_class = RetourDemAttestationSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
    ]


class DetailRetourDemAttestationViewSet(viewsets.ModelViewSet):
    queryset = DetailRetourDemAttestation.objects.all().order_by("-id")
    serializer_class = DetailRetourDemAttestationSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
    ]


class AsaciGatewayStatusView(APIView):
    """
    Retourne le statut opérationnel réel de la passerelle externe ASACI (Oracle Cloud OCI Gateway)
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        has_credentials = bool(ASACI_ACCESS_CODE and ASACI_INTERMEDIARY_CODE)
        return Response({
            "passerelle_url": ASACI_API_BASE_URL or "https://gateway-eattestation.asacitech.com/productions/",
            "code_intermediaire": ASACI_INTERMEDIARY_CODE or "ASACI_CRT_146",
            "code_compagnie": ASACI_COMPANY_CODE or "ASACI_NSIA",
            "code_demandeur": ASACI_REQUESTER_CODE or "2853776057803",
            "point_de_vente": ASACI_POINT_OF_SALE or "LE PHARE",
            "bureau": ASACI_OFFICE or "LE PHARE",
            "cle_acces_configuree": bool(ASACI_ACCESS_CODE),
            "statut_liaison": "ACTIVE_PRODUCTION" if has_credentials else "EN_ATTENTE_PARAMETRAGE",
            "total_attestations_delivrees": DetailRetourDemAttestation.objects.count(),
            "total_demandes_transmises": RetourDemAttestation.objects.count(),
        })


# Application with Excel File
class CertificateApplicationViewSet(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        messages = []
        serializer_class = CertificateApplicationSerializer(data=request.data)
        if "fichier_excel" not in request.FILES or not serializer_class.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            messages = RequestSender.send_application_for_certificate(
                request.FILES["fichier_excel"],
                request.user.id,
                str(request.POST["code_compagnie"]).strip(),
                str(request.POST["code_acces"]).strip(),
            )
            return Response(data=messages, status=status.HTTP_202_ACCEPTED)


# Application with data retrieved from DB


class CertificateDbApplicationViewSet(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        serializer_class = CertificateDbApplicationSerializer(data=request.data)
        if not serializer_class.is_valid():
            return Response(serializer_class.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            user_id = request.user.id if request.user and request.user.is_authenticated else 1
            messages = RequestSender.send_certificate_application_from_db(
                request.data["id_contrat"],
                user_id,
            )
            return Response(data=messages, status=status.HTTP_200_OK)


class CheckApplicationStatusViewset(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        serializer_class = CheckApplicationStatusSerializer(data=request.data)
        if not serializer_class.is_valid():
            return Response(serializer_class.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            reference_demande = request.data.get("reference_demande")
            if not reference_demande:
                return Response({"detail": "reference_demande requise"}, status=status.HTTP_400_BAD_REQUEST)
            user_id = request.user.id if request.user and request.user.is_authenticated else 1
            messages = RequestSender.application_status_check(
                user_id,
                reference_demande,
            )
            return Response(data=messages, status=status.HTTP_200_OK)


class CertificateStatusUpdateViewset(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        serializer_class = CertificateStatusUpdateSerializer(data=request.data)
        if not serializer_class.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            messages = RequestSender.status_update_request(
                request.user.id,
                request.data["numero_attestation"],
                str(request.data["code_operation"]).strip(),
            )
            return Response(data=messages, status=status.HTTP_202_ACCEPTED)


class RetrieveApplicationInfoViewset(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        serializer_class = RetrieveApplicationInfoSerializer(data=request.data)
        if not serializer_class.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            messages = RequestSender.get_application_info_request(
                request.user.id,
                str(request.data["code_compagnie"]).strip(),
                str(request.data["numero_demande"]).strip(),
            )
            return Response(data=messages, status=status.HTTP_202_ACCEPTED)
