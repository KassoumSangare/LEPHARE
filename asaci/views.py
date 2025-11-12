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
class RetourDemAttestationViewSet(viewsets.ViewSet):
    queryset = RetourDemAttestation.objects.all()
    serializer_class = RetourDemAttestationSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class DetailRetourDemAttestationViewSet(viewsets.ViewSet):
    queryset = DetailRetourDemAttestation.objects.all()
    serializer_class = DetailRetourDemAttestationSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


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
        messages = []
        serializer_class = CertificateDbApplicationSerializer(data=request.data)
        if not serializer_class.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            messages = RequestSender.send_certificate_application_from_db(
                request.data["id_contrat"],
                request.user.id,
            )
            return Response(data=messages, status=status.HTTP_202_ACCEPTED)


class CheckApplicationStatusViewset(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        serializer_class = CheckApplicationStatusSerializer(data=request.data)
        if not serializer_class.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            reference_demande = request.data["reference_demande"]
            if not reference_demande:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            messages = RequestSender.application_status_check(
                request.user.id,
                reference_demande,
            )
            return Response(data=messages, status=status.HTTP_202_ACCEPTED)


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
