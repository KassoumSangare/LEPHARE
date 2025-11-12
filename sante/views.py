from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Q
from rest_framework import generics

from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication

from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import status

from rest_framework.generics import get_object_or_404


from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)


from .serializers import *
from production.serializers import DataInsertionSerializer
from production.models import Devis
from .models import *
from .utils import (
    save_quotation_sante,
    enregistrer_adherent_sante,
    enregistrer_affilie_sante,
    enregistrer_filiale_sante,
    get_quotation_id,
    get_saisie_sante_en_cours,
    import_insured,
    get_liste_affilie_sante,
)


# Create your views here.
class FilialeSanteViewSet(viewsets.ModelViewSet):
    queryset = FilialeSante.objects.filter(Q(devis__gte=1))
    serializer_class = FilialeSanteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class AdherentViewSet(viewsets.ModelViewSet):
    queryset = Adherent.objects.filter(Q(devis__gte=1))
    serializer_class = AdherentSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class AffilieViewSet(viewsets.ModelViewSet):
    queryset = Affilie.objects.filter(Q(devis__gte=1))
    serializer_class = AffilieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ImportationAffilieViewSet(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        messages = []
        serializer_class = ImportationAffilieSerializer(data=request.data)
        if "fichier_excel" not in request.FILES or not serializer_class.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            (error_count, messages) = import_insured(
                request.FILES["fichier_excel"],
                request.user.id,
                request.POST["id_devis"],
                request.POST["date_effet"],
                request.POST["id_filiale"],
            )
            if error_count == 0:
                return Response(data=messages, status=status.HTTP_202_ACCEPTED)
            else:
                return Response(data=messages, status=status.HTTP_400_BAD_REQUEST)


class AdherentEnSaisieView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, pk=None, format=None) -> Response:
        adherent = get_object_or_404(Adherent.objects.all(), pk=pk)
        serializer = AdherentSerializer(adherent)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdherentListeEnSaisieView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddevis=None, format=None) -> Response:
        adherents = Adherent.objects.filter(
            Q(operateur=request.user) & Q(devis=iddevis)
        )
        serializer = AdherentSerializer(adherents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AffilieEnSaisieView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, pk=None, format=None) -> Response:
        affilie = get_object_or_404(Affilie.objects.all(), pk=pk)
        serializer = AffilieSerializer(affilie)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AffilieListeEnSaisieView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddevis=None, format=None) -> Response:
        affilies = Affilie.objects.filter(Q(operateur=request.user) & Q(devis=iddevis))
        serializer = AffilieSerializer(affilies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FilialeEnSaisieView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, pk=None, format=None) -> Response:
        filiale = get_object_or_404(FilialeSante.objects.all(), pk=pk)
        serializer = FilialeSanteSerializer(filiale)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FilialeListeEnSaisieView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddevis=None, format=None) -> Response:
        filiales = FilialeSante.objects.filter(
            Q(operateur=request.user) & Q(devis=iddevis)
        )
        serializer = FilialeSanteSerializer(filiales, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NumeroSaisieSanteView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, format=None) -> Response:
        (msg, iddevis) = get_quotation_id(request.user.id)
        if iddevis == 0:
            return Response(
                {"status": "échec", "message": msg, "devis": iddevis},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"status": "succès", "message": msg, "devis": iddevis},
            status=status.HTTP_200_OK,
        )


class SaisieDevisSanteEnCoursView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, format=None) -> Response:
        (msg, qryset) = get_saisie_sante_en_cours(request.user.id)
        if not msg:
            serializer = SaisieDevisSanteEnCoursSerializer(qryset, many=True)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"status": "échec", "message": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )

class ListeAffilieSanteView(APIView):
    permission_classes = [permissions.IsAuthenticated,]

    def get(self, request, iddevis, format=None) -> Response:
        (msg, qryset) = get_liste_affilie_sante(iddevis=iddevis)
        if not msg:
            serializer = AffilieFnSerializer(qryset, many=True)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"status": "échec", "message": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )
# Create a new quotation (Health Insurance)
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation_sante(request):
    enregistrementdevis_data = JSONParser().parse(request)
    print("JSON de la requête:", enregistrementdevis_data)
    enregistrementdevis_serializer = EnregistrementDevisSanteSerializer(
        data=enregistrementdevis_data
    )
    if enregistrementdevis_serializer.is_valid():
        (err, qryset) = save_quotation_sante(request.user.id, enregistrementdevis_data)
        data_insertion_serializer = DataInsertionSerializer(qryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        enregistrementdevis_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


###########################################################################
# Créer un nouvel adhérent Santé
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def saisir_adherent_sante(request):
    # Implementation future
    fichier_piece = None
    if "fichierpiece" in request.FILES:
        if request.FILES["fichierpiece"]:
            fichier_piece = request.FILES["fichierpiece"]

    #adherent_data = JSONParser().parse(request)
    adherent_data = request.POST
    #serializer = AdherentSaisieSerializer(data=adherent_data)

    #if serializer.is_valid():
    user_id = request.user.id
    (err, qryset) = enregistrer_adherent_sante(user_id, adherent_data, fichier_piece)
        # Implementation future
        # (err, qryset) = enregistrer_adherent_sante(user_id, fichier_piece, request.POST)
    data_insertion_serializer = AdherentSanteInsertionSerializer(qryset, many=True)
    st = status.HTTP_201_CREATED
    if err:
        st = status.HTTP_400_BAD_REQUEST
    return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    #return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def annuler_saisie_objet_sante(request, type_objet):
    if type_objet not in ["AFF", "ADH", "FIL"]:
        return JsonResponse(
            {
                "statut": "Echec",
                "message": "Erreur logicielle: type d'objet incorrect!",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    objet_data = JSONParser().parse(request)
    # print("JSON de la requête:", objet_data)
    serializer = AnnulationSaisieObjetSanteSerializer(data=objet_data)
    if serializer.is_valid():
        try:
            user_id = request.user.id
            id_devis = int(objet_data["id_devis"])
            devis = Devis.objects.get(pk=id_devis)
            if devis.confirme:
                return JsonResponse(
                    {
                        "statut": "Echec",
                        "message": "Devis dejà confirmé. Opération impossible!",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif devis.produit.pk != 5:
                return JsonResponse(
                    {
                        "statut": "Echec",
                        "message": "Erreur logicielle. Ce devis n'a pas été produit en Santé!",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            id_objet = int(objet_data["id_objet"])
            if type_objet == "AFF":
                affilie = Affilie.objects.get(pk=id_objet)
                if affilie.lien == "A":
                    return JsonResponse(
                        {
                            "statut": "Echec",
                            "message": "Cet affilié est un chef de famille. Opération impossible!",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                res_del = affilie.delete()
            elif type_objet == "ADH":
                adherent = Adherent.objects.get(pk=id_objet)
                affilies = Affilie.objects.filter(
                    Q(adherent=adherent) & Q(devis=id_devis)
                )
                if affilies.count() > 0:
                    affilies.delete()
                res_del = adherent.delete()
            elif type_objet == "FIL":
                filiale = FilialeSante.objects.get(pk=id_objet)
                adherents = Adherent.objects.filter(
                    Q(filiale=filiale) & Q(devis=id_devis)
                )
                for adh in adherents:
                    affilies = Affilie.objects.filter(
                        Q(adherent=adh) & Q(devis=id_devis)
                    )
                    if affilies.count() > 0:
                        affilies.delete()
                adherents.delete()
                res_del = filiale.delete()
            if res_del[0] > 0:
                return JsonResponse(
                    {"statut": "Succès", "message": "Suppression réalisée avec succès"},
                    status=status.HTTP_200_OK,
                )

        except Devis.DoesNotExist as error_devis:
            print(error_devis)
            return JsonResponse(
                {"statut": "Echec", "message": "Devis inexistant!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Affilie.DoesNotExist as error_affilie:
            print(error_affilie)
            return JsonResponse(
                {"statut": "Echec", "message": "Affilié inexistant!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Adherent.DoesNotExist as error_adherent:
            print(error_adherent)
            return JsonResponse(
                {"statut": "Echec", "message": "Adhérent inexistant!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except FilialeSante.DoesNotExist as error_filiale:
            print(error_filiale)
            return JsonResponse(
                {"statut": "Echec", "message": "Filiale inexistante!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as error:
            print(error)
            return JsonResponse(
                {"statut": "Echec", "message": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


###########################################################################
# Supprimer un affilie Santé d'un devis en cours de saisie
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def annuler_saisie_affilie(request):
    return annuler_saisie_objet_sante(request, "AFF")


###########################################################################
# Supprimer un adhérent Santé d'un devis en cours de saisie
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def annuler_saisie_adherent(request):
    return annuler_saisie_objet_sante(request, "ADH")


###########################################################################
# Supprimer une filiale Santé d'un devis en cours de saisie
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def annuler_saisie_filiale(request):
    return annuler_saisie_objet_sante(request, "FIL")


###########################################################################
# Créer un nouvel affilié Santé
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def saisir_affilie_sante(request):
    #affilie_data = JSONParser().parse(request)
    # print("JSON de la requête:", affilie_data)
    # Implementation future
    fichier_piece = None
    if "fichierpiece" in request.FILES:
        if request.FILES["fichierpiece"]:
            fichier_piece = request.FILES["fichierpiece"]

    affilie_data = request.POST
    # print("JSON de la requête:", affilie_data)
    user_id = request.user.id
    #serializer = AffilieSaisieSerializer(data=affilie_data)
    #if serializer.is_valid():
    (err, qryset) = enregistrer_affilie_sante(user_id, affilie_data, fichier_piece)
    data_insertion_serializer = AffilieSanteInsertionSerializer(qryset, many=True)
    st = status.HTTP_201_CREATED
    if err:
        st = status.HTTP_400_BAD_REQUEST
    return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    #return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#####################################################################################
# Créer une nouvelle filiale Santé
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def saisir_filiale_sante(request):
    filiale_data = JSONParser().parse(request)
    # print("JSON de la requête:", filiale_data)
    serializer = FilialeSanteSaisieSerializer(data=filiale_data)
    if serializer.is_valid():
        user_id = request.user.id
        (err, qryset) = enregistrer_filiale_sante(user_id, filiale_data)
        data_insertion_serializer = FilialeSanteInsertionSerializer(qryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

