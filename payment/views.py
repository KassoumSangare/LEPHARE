from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .serializers import DistripayTransactionSerializer, InitiationPaiementSerializer
from .models import (
    DistripayTransaction,
)

from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from .distripay import DistripayAPIClient


class DistripayTransactionViewSet(viewsets.ModelViewSet):
    queryset = DistripayTransaction.objects.all()
    serializer_class = DistripayTransactionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    # def get(self, request, *args, **kwargs):
    #     transaction_id = None
    #     if bool(request.query_params):
    #         if len(request.query_params) == 1:
    #             transaction_id = request.query_params[request.query_params.keys()[0]]

    #     if transaction_id is not None:
    #         instance = get_object_or_404(DistripayTransaction, pk=transaction_id)
    #         serializer = DistripayTransactionSerializer(instance)
    #     else:
    #         queryset = DistripayTransaction.objects.all()
    #         serializer = DistripayTransactionSerializer(queryset, many=True)
    #     return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        raise PermissionDenied("Creation d'objets non autorisée.")

    def update(self, request, *args, **kwargs):
        raise PermissionDenied("Mise à jour d'objets non autorisée.")

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied("Mise à jour partielle d'objets non autorisée.")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Suppression d'objets non autorisée.")


class PaiementMobileInfoView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idtransaction):
        distripay_api_client = DistripayAPIClient()
        paiement_info = distripay_api_client.check_transaction_status(idtransaction)
        if "status_code" in paiement_info:
            status_code = paiement_info["status_code"]
            del paiement_info["status_code"]
            if status_code == 200:
                if "code" in paiement_info and paiement_info["code"] == "00":
                    return JsonResponse(
                        paiement_info, status=status.HTTP_200_OK, safe=False
                    )
        return JsonResponse(
            paiement_info, status=status.HTTP_400_BAD_REQUEST, safe=False
        )


# Initiate a mobile payment
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def initiate_mobile_payment(request):
    initiationpaiement_data = JSONParser().parse(request)
    ##print("JSON de la requête:", finalisationdevis_data)
    initiationpaiement_serializer = InitiationPaiementSerializer(
        data=initiationpaiement_data
    )
    if initiationpaiement_serializer.is_valid():
        distripay_api_client = DistripayAPIClient()
        montant = 0
        if "montant" in initiationpaiement_data:
            montant = int(initiationpaiement_data["montant"])
        description = ""
        if "description" in initiationpaiement_data:
            description = str(initiationpaiement_data["description"])
        idclient = 0
        if "idclient" in initiationpaiement_data:
            if initiationpaiement_data["idclient"]:
                idclient = int(initiationpaiement_data["idclient"])
        resp = distripay_api_client.initiate_transaction(
            amount=montant, description=description, customer_id=idclient
        )
        if int(resp["status_code"]) == 200 and resp["code"] == "201":
            st = status.HTTP_201_CREATED
        else:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(resp, status=st, safe=False)
    return JsonResponse(
        initiationpaiement_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


# Initiate a mobile payment
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def verify_mobile_payment(request):
    pass
