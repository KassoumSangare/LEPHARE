from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Q
from rest_framework import generics
from django.shortcuts import get_object_or_404

from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication

from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import status
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
)
from .serializers import (
    BordereauEmissionInputSerializer,
    BordereauEmissionResultSetSerializer,
    EtatDecisionnelSerializer,
    EtatCimaE1Serializer,
    EtatCimaE2Serializer,
)
from .models import EtatDecisionnel
from .utils import (
    get_bordereau_recap_emission,
    get_arrieres_encaissements_annulations,
    get_emissions_encaissements_commissions,
    get_etat_decisionnel_contenu,
)


# Create your views here.


##################################################################################
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_emission_for_bordereau_recap(request):
    emission_request_data = JSONParser().parse(request)
    print("JSON de la requête:", emission_request_data)
    input_serializer = BordereauEmissionInputSerializer(data=emission_request_data)
    if input_serializer.is_valid():
        (msg, emission) = get_bordereau_recap_emission(emission_request_data)
        if not msg:
            output_serializer = BordereauEmissionResultSetSerializer(
                emission, many=True
            )
            print(output_serializer.data)
            return JsonResponse(
                output_serializer.data, status=status.HTTP_200_OK, safe=False
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return JsonResponse(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EtatDecisionnelViewSet(viewsets.ModelViewSet):
    queryset = EtatDecisionnel.objects.all().order_by("code_etat")
    serializer_class = EtatDecisionnelSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    @action(detail=True, methods=["get"], url_path="contenu")
    def contenu(self, request, pk=None):
        etat = self.get_object()
        date_debut = request.query_params.get("date_debut")
        date_fin = request.query_params.get("date_fin")
        type_etat = request.query_params.get("type_etat")
        (msg, dossiers) = get_etat_decisionnel_contenu(
            etat.code_etat, etat.libelle_etat, date_debut, date_fin, type_etat
        )
        if not msg:
            return Response(
                {
                    "Status": "Succès",
                    "Etat": EtatDecisionnelSerializer(etat).data,
                    "Data": dossiers,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"Status": "Echec", "Data": msg}, status=status.HTTP_400_BAD_REQUEST
        )


class EtatDecisionnelContenuView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, pk):
        etat = get_object_or_404(EtatDecisionnel, pk=pk)
        date_debut = request.query_params.get("date_debut")
        date_fin = request.query_params.get("date_fin")
        type_etat = request.query_params.get("type_etat")

        (msg, dossiers) = get_etat_decisionnel_contenu(
            etat.code_etat, etat.libelle_etat, date_debut, date_fin, type_etat
        )
        if not msg:
            return Response(
                {
                    "Status": "Succès",
                    "Etat": EtatDecisionnelSerializer(etat).data,
                    "Data": dossiers,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"Status": "Echec", "Data": msg}, status=status.HTTP_400_BAD_REQUEST
        )


class GarantieSouscriteView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_garantie(self, id_entite, type_entite):
        try:
            from production.database import get_garantie_souscrite
            msg, garanties = get_garantie_souscrite(id_entite, type_entite)
            if not msg:
                return Response(
                    {"Status": "Succès", "Data": garanties}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"Status": "Echec", "Data": msg}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {"Status": "Echec", "Data": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class EtatCimaE1View(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, exercice):
        (msg, emissions_encaissments) = get_emissions_encaissements_commissions(
            exercice
        )
        if not msg:
            serializer = EtatCimaE1Serializer(emissions_encaissments, many=True)
            return Response(
                {"Status": "Succès", "Data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"Status": "Echec", "Data": msg}, status=status.HTTP_400_BAD_REQUEST
            )


class EtatCimaE2View(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, exercice):
        (msg, arrieres_encaissments) = get_arrieres_encaissements_annulations(exercice)
        if not msg:
            serializer = EtatCimaE2Serializer(arrieres_encaissments, many=True)
            return Response(
                {"Status": "Succès", "Data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"Status": "Echec", "Data": msg}, status=status.HTTP_400_BAD_REQUEST
            )
