from django.http.response import JsonResponse

from rest_framework import viewsets, filters
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework import status

from .serializers import ClientSerializer
from .models import Client
from django.db.models import Q
import re
import phonenumbers as pn
from core.views import ResultsOnlyPagination


def valid_email_address(email):
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    return re.fullmatch(regex, email)


def valid_phone_number(phone_candidate):
    national_number = ""
    try:
        z = pn.parse(phone_candidate, "CI")
    except pn.phonenumberutil.NumberParseException as error:
        national_number = ""
    else:
        if pn.is_valid_number(z):
            national_number = z.national_number
    return national_number


# Create your views here.


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.filter(~Q(IdClient=0)).order_by("Nom", "Prenoms")
    serializer_class = ClientSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["Nom", "Prenoms"]
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.IsAuthenticated]


class ClientRestreintViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.filter(~Q(IdClient=0)).order_by("Nom", "Prenoms")[:5000]
    serializer_class = ClientSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["Nom", "Prenoms"]
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.IsAuthenticated]


class ClientRechercheView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, champrecherche):
        criteria = str(champrecherche).strip()
        if valid_email_address(criteria):
            clientrecherche = Client.objects.filter(Q(Email=criteria) & ~Q(IdClient=0))
        else:
            phone_number_part = valid_phone_number(criteria)
            if phone_number_part:
                clientrecherche = Client.objects.filter(
                    (
                        Q(Mobile__contains=phone_number_part)
                        | Q(Telephone__contains=phone_number_part)
                        | Q(Fixe__contains=phone_number_part)
                    )
                    & ~Q(IdClient=0)
                )
            else:
                clientrecherche = Client.objects.filter(
                    Q(Nom__icontains=criteria) & ~Q(IdClient=0)
                )
        if clientrecherche:
            clientrecherche = clientrecherche.order_by("Nom", "Prenoms")

        serializer = ClientSerializer(clientrecherche, many=True)

        return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)
