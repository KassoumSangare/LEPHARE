from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, date
from django.conf import settings
from django.db.models import Q, F, Prefetch
from rest_framework import generics
from django.shortcuts import get_object_or_404
from core.date_parser import parse_date_string
from typing import cast


from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication
from .tasks import send_sms_enregistrement_contrat, send_sms_encaissement_contrat
from customer.models import Client
from .serializers import (
    DevisDetGarantieSerializer,
    DevisDetailSerializer,
    DevisSerializer,
    DevisClientSerializer,
    TarifEcranSerializer,
    ContratSerializer,
    ContratDetailSerializer,
    EnregistrementDevisAutoSerializer,
    OperationSurDevisSerializer,
    DataInsertionSerializer,
    QuotationInsertionSerializer,
    ContratDetGarantieSerializer,
    QuittancePropositionSerializer,
    QuittanceContratSerializer,
    CreationAyantDroitIaSerializer,
    EnregistrementDevisIaSerializer,
    AyantDroitIaSerializer,
    EnregistrementDevisVoyageSerializer,
    ExtendedQuotationInfoSerializer,
    EnregistrementDevisMrhSerializer,
    QuittanceSerializer,
    DetailQuittanceSerializer,
    EncaissementSerializer,
    DetailEncaissementSerializer,
    NumeroSerializer,
    FinalisationDevisFlotteSerializer,
    OperationSurDevisDetailSerializer,
    GarantieContratFlotteSerializer,
    VehiculeContratSerializer,
    ContractForPremiumCollectionSerializer,
    EnregistrementEncaissementSerializer,
    DemandeContratPourEncaissementSerializer,
    EncaissementGroupeQuittanceSerializer,
    ReversementCompagnieSerializer,
    DetailReversementSerializer,
    ReversementGroupePrimeSerializer,
    ReversementGroupePrimeValidateSerializer,
    ReversementGroupePrimeInsertSerializer,
    PremiumCollectionInfoSerializer,
    PremiumRemittanceInfoSerializer,
    EnregistrementDevisTRInfoSerializer,
    EnregistrementDevisGlobaleDeBanqueSerializer,
    QuotationIaInsertionSerializer,
    AssureIaInfoSerializer,
    AssureIaParDevisOuContratSerializer,
    GarantieSouscriteSerializer,
    ChangementImmatriculationSerializer,
    AvenantAnlRenSerializer,
    InfoVehiculeSerializer,
    AnnulationEncaissementSerializer,
    LogRecordSerializer,
    EnregistrementDevisRCSerializer,
    ImportationAssureIaSerializer,
    ImportationTransportSerializer,
    CertificatTransportSerializer,
    CorrectionDevisSerializer,
    PrimeUpdateSerializer,
    ConsolidationDevisClientSerializer,
)

from .models import (
    Devis,
    DevisDetail,
    DevisDetGarantie,
    TarifEcran,
    Contrat,
    ContratDetail,
    ContratDetGarantie,
    QuittanceFn,
    AyantDroitIa,
    Quittance,
    DetailQuittance,
    Encaissement,
    DetailEncaissement,
    Numero,
    ContractForPremiumCollection,
    ReversementCompagnie,
    DetailReversement,
    LogRecord,
    CertificatTransport,
)


from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone

from autorisations.serializers import AnnulerAvecJetonSerializer
from autorisations.models import JetonAutorisation
from autorisations.models import DemandeAutorisation, TypeOperation
from autorisations.tasks import envoyer_notification_nouvelle_demande
from django.contrib.contenttypes.models import ContentType


# Import du service de calcul de prime MRH
from .services.mrh_calcul_service import MRHCalculService



# Import du module de calcul du résumé financier
from .services.resume_financier_devis import obtenir_resume_financier_devis

# Import du serializer
from .serializers import ResumeFinancierDevisSerializer

# Import des modèles MRH
from configuration_api.models import (
    UsageHabitation,
    SousGarantieMRH,
    ParametresCalcul,
    Option,
    SousGarantieForfait,
)

from configuration_api.serializers import (
    # Serializers lecture
    UsageHabitationSerializer,
    SousGarantieMRHSerializer,
    OptionSerializer,
    SousGarantieForfaitSerializer,
    ParametresCalculSerializer,
)
# Import des serializers
from .serializers import (
    # Serializers requêtes
    MaisonCalculRequestSerializer,
    DevisMRHCreateRequestSerializer,
    MaisonAjoutRequestSerializer,
    
    # Serializers réponses
    DevisMRHResponseSerializer,
    MaisonCalculeeSerializer,
    DevisMRHCalculeResponseSerializer,
    MaisonAjouteeResponseSerializer,
    ErrorSerializer,
)

from .exceltopostgresql import export_excel

from .database import (
    save_quotation,
    save_quotation_ia,
    save_quotation_voyage,
    save_quotation_mrh,
    save_quotation_tousrisquesinfo,
    save_contract,
    get_quotation_info,
    get_contract_info,
    enregistrer_ayant_droit,
    get_extended_quotation_info,
    quotation_completion,
    archive_quote,
    cancel_car_input,
    get_contract_coverage,
    get_contract_car_list,
    get_contract_list_for_pc,
    save_premium_collection,
    save_premium_collection_cancellation,
    get_contract_premium_remittance,
    save_premium_remittance,
    premium_remittance_validation,
    get_info_encaissement,
    get_info_reversement,
    get_info_vehicule,
    save_insured_ia,
    get_assure_ia,
    save_quotation_globaledebanque,
    save_quotation_rc,
    get_liste_assure_ia,
    get_taux_reduction_flotte,
    get_garantie_souscrite,
    save_plate_number,
    policy_modification,
    unarchive_quote,
    get_encaissement_recherche,
    get_contract_list_for_customer,
    get_certificat_transport,
    correction_devis,
    execute_maj_manuelle_primes,
    consolider_devis_db,
    offre_mrh_compatible,
)
from .utils import import_ia_insured
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from configuration_api.models import OffreAutomobileBoisee, Produit
import logging

logger = logging.getLogger(__name__)


# Create your views here.
def stored_procedure_result(
    request, post_serializer_cls, stored_proc_caller, qry_res_serializer_cls
):
    json_data = JSONParser().parse(request)
    print("JSON de la requête:", json_data)
    post_serializer = post_serializer_cls(data=json_data)
    if post_serializer.is_valid():
        (err, qryset) = stored_proc_caller(json_data)
        qry_res_serializer = qry_res_serializer_cls(qryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(qry_res_serializer.data, status=st, safe=False)
    return JsonResponse(post_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ContractForPremiumCollectionView(generics.ListCreateAPIView):
    serializer_class = ContractForPremiumCollectionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        reference_client = self.request.query_params.get("referenceclient", None)
        reference_contrat = self.request.query_params.get("referencecontrat", None)
        if reference_client:
            reference_client = str(reference_client)
        if reference_contrat:
            reference_contrat = str(reference_contrat)
        (msg, item) = get_contract_list_for_pc(reference_client, reference_contrat)
        if not msg:
            return item
        else:
            return ContractForPremiumCollection.objects.none()


class EncaissementRechercheView(generics.ListCreateAPIView):
    queryset = Encaissement.objects.filter(~Q(piece_annulee=True)).order_by(
        "-dateencaissement"
    )[:1000]
    serializer_class = EncaissementSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        reference_client = self.request.query_params.get("referenceclient", None)
        reference_contrat = self.request.query_params.get("referencecontrat", None)
        if reference_client or reference_contrat:
            if reference_client:
                reference_client = str(reference_client)
            if reference_contrat:
                reference_contrat = str(reference_contrat)
            (msg, item) = get_encaissement_recherche(
                reference_client, reference_contrat
            )
            if not msg:
                return item
            else:
                return Encaissement.objects.none()
        return super().get_queryset()


class DevisViewSet(viewsets.ModelViewSet):
    queryset = Devis.objects.annotate(
        offreboisee=OffreAutomobileBoisee(F("offre__IdOffre"))
    ).all()
    serializer_class = DevisSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class CertificatTransportView(generics.ListCreateAPIView):
    queryset = CertificatTransport.objects.all().order_by("-date_fin_periode")[:1000]
    serializer_class = CertificatTransportSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        start_date = self.request.query_params.get("datedebutperiode", None)
        end_date = self.request.query_params.get("datefinperiode", None)
        customer_id = self.request.query_params.get("idclient", None)

        return get_certificat_transport(start_date, end_date, customer_id)


class DevisClientView(generics.ListAPIView):
    queryset = Devis.objects.filter(confirme=True, archive=False)
    serializer_class = DevisClientSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        id_client = self.request.query_params.get("idclient", None)
        nom_client = self.request.query_params.get("nomclient", None)
        id_produit = self.request.query_params.get("idproduit", None)
        devis_qs = Devis.objects.filter(confirme=False, archive=False)
        try:
            if nom_client:
                clients = Client.objects.filter(
                    Q(Nom__istartswith=nom_client) | Q(Prenoms__istartswith=nom_client)
                )
                if clients:
                    devis_qs = devis_qs.filter(client__in=clients)
            if id_client:
                client = Client.objects.get(pk=id_client)
                devis_qs = devis_qs.filter(client=client)
            if id_produit:
                produit = Produit.objects.get(pk=id_produit)
                devis_qs = devis_qs.filter(produit=produit)
        except Client.DoesNotExist as ec:
            print(ec)
            devis_qs = devis_qs.filter(iddevis=0)
        except Produit.DoesNotExist as eq:
            print(eq)
            devis_qs = devis_qs.filter(iddevis=0)
        devis_qs = devis_qs.prefetch_related(
            Prefetch(
                "details", queryset=DevisDetail.objects.filter(iddevis__in=devis_qs)
            )
        )
        return devis_qs


class ConsolidationDevisView(APIView):
    """
    Vue pour consolider plusieurs devis en un seul.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        # Validation du format de données
        serializer = ConsolidationDevisClientSerializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response(
                {"erreur": "Format de données invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extraction des IDs de devis
        devis_ids = [item["iddevis"] for item in serializer.validated_data]

        # Vérification du nombre minimum de devis
        if len(devis_ids) < 2:
            return Response(
                {
                    "erreur": (
                        "Au minimum 2 devis sont requis pour la " "consolidation."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupération des devis depuis la base de données
        devis_list = Devis.objects.filter(iddevis__in=devis_ids)

        # Vérification que tous les devis existent
        if devis_list.count() != len(devis_ids):
            return Response(
                {"erreur": "Un ou plusieurs devis n'existent pas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérification que tous les devis sont mono
        if devis_list.filter(flotte=True).count() > 0:
            return Response(
                {"erreur": "Tous les devis doivent être mono."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérification que tous les devis sont non confirmés et non archivés
        if devis_list.filter(Q(archive=True) | Q(confirme=True)).count() > 0:
            return Response(
                {
                    "erreur": "Tous les devis doivent être non confirmés et non archivés."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérification que tous les devis appartiennent au même client
        clients = devis_list.values_list("client", flat=True).distinct()
        if len(clients) > 1:
            return Response(
                {"erreur": "Tous les devis doivent appartenir au même client."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérification que tous les devis concernent le même produit
        produits = devis_list.values_list("produit", flat=True).distinct()
        if len(produits) > 1:
            return Response(
                {"erreur": "Tous les devis doivent concerner le même produit."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérification que tous les devis concernent la compagnie
        compagnies = devis_list.values_list("compagnie", flat=True).distinct()
        if len(compagnies) > 1:
            return Response(
                {
                    "erreur": "Tous les devis doivent être produits sur la même compagnie."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérification que tous les devis concernent le même intermediaire
        intermediaires = devis_list.values_list("intermediaire", flat=True).distinct()
        if len(intermediaires) > 1:
            return Response(
                {
                    "erreur": "Tous les devis doivent être produits pour le même intermédiaire."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérification que tous les devis concernent le même assuré
        assures = devis_list.values_list("assure", flat=True).distinct()
        if len(assures) > 1:
            return Response(
                {"erreur": "Tous les devis doivent concerner le même assuré."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérification que tous les devis concernent le même avenant
        avenants = devis_list.values_list("avenant", flat=True).distinct()
        if len(avenants) > 1:
            return Response(
                {"erreur": "Tous les devis doivent avoir le même avenant."},
                status=status.HTTP_403_FORBIDDEN,
            )
        dates_effet = devis_list.values_list("dateeffet", flat=True).distinct()
        if len(dates_effet) > 1:
            return Response(
                {"erreur": "Tous les devis doivent avoir la même date d'effet."},
                status=status.HTTP_403_FORBIDDEN,
            )
        dates_expiration = devis_list.values_list(
            "dateexpiration", flat=True
        ).distinct()
        if len(dates_expiration) > 1:
            return Response(
                {"erreur": "Tous les devis doivent avoir la même date d'expiration."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Appel de la fonction utilitaire pour consolider les devis
        try:
            id_devis_consolide = consolider_devis_db(user_id, devis_ids)

            return Response(
                {
                    "iddevis": id_devis_consolide,
                    "message": "Devis consolidés avec succès.",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"erreur": f"Erreur lors de la consolidation: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DevisDetailViewSet(viewsets.ModelViewSet):
    queryset = DevisDetail.objects.all()
    serializer_class = DevisDetailSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class DevisDetGarantieViewSet(viewsets.ModelViewSet):
    queryset = DevisDetGarantie.objects.filter(~Q(IdGarantie=0))
    serializer_class = DevisDetGarantieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class TarifEcranViewSet(viewsets.ModelViewSet):
    queryset = TarifEcran.objects.all()
    serializer_class = TarifEcranSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ContratViewSet(viewsets.ModelViewSet):
    queryset = Contrat.objects.filter(Q(idcontratannulation=0))
    serializer_class = ContratSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ContratRestreintViewSet(viewsets.ModelViewSet):
    queryset = Contrat.objects.filter(Q(idcontratannulation=0)).order_by(
        "-dateemission"
    )[:500]
    serializer_class = ContratSerializer
    permission_classes = [permissions.IsAuthenticated]


class ContratDetailViewSet(viewsets.ModelViewSet):
    queryset = ContratDetail.objects.all()
    serializer_class = ContratDetailSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ContratDetGarantieViewSet(viewsets.ModelViewSet):
    queryset = ContratDetGarantie.objects.filter(~Q(idgarantie=0))
    serializer_class = ContratDetGarantieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class AyantDroitMineneView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, numeropolice):
        numeropolice = str(numeropolice).strip()
        assures = Client.objects.filter(Adresse2=numeropolice)
        idassure = -1
        if assures:
            idassure = assures.first().IdClient
        ayant_droits_queryset = AyantDroitIa.objects.filter(id_assure=idassure)
        serializer = AyantDroitIaSerializer(ayant_droits_queryset, many=True)
        # print(serializer.data)
        return Response(
            {"Status": "Succès", "ayantdroits": serializer.data},
            status=status.HTTP_200_OK,
        )


class AyantDroitIaView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idassure):
        # if idassure:
        ayant_droits_queryset = AyantDroitIa.objects.filter(id_assure=idassure)
        # else:
        #    ayant_droits_queryset = AyantDroitIa.objects.all()
        serializer = AyantDroitIaSerializer(ayant_droits_queryset, many=True)
        # print(serializer.data)
        return Response(
            {"Status": "Succès", "ayantdroits": serializer.data},
            status=status.HTTP_200_OK,
        )


class ImportationAssureIaViewSet(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        message = {}
        error_count = 0
        id_devis = 0
        errors = []
        serializer_class = ImportationAssureIaSerializer(data=request.data)
        if "FichierExcel" not in request.FILES or not serializer_class.is_valid():
            if "IdDevis" in request.POST:
                if request.POST["IdDevis"]:
                    id_devis = int(request.POST["IdDevis"])
            message["IdDevis"] = id_devis
            message["messages"] = [
                "Paramètres non conformes",
            ]
            return Response(data=message, status=status.HTTP_400_BAD_REQUEST)
        else:
            (error_count, id_devis, errors) = import_ia_insured(
                request.FILES["FichierExcel"], request.user.id, request.POST
            )
            message["IdDevis"] = id_devis
            if error_count == 0:
                message["messages"] = [
                    "Importation des assurés réalisée avec succès.",
                ]
                return Response(data=message, status=status.HTTP_202_ACCEPTED)
            else:
                message["messages"] = errors
                return Response(data=message, status=status.HTTP_400_BAD_REQUEST)


class LogRecordView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request):
        msg = request.query_params.get("msg", "")
        level_name = request.query_params.get("levelname", "")
        serializer = LogRecordSerializer(LogRecord(msg=msg, level_name=level_name))
        print(serializer.data)
        return Response(
            {"Status": "Succès", "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class QuittanceViewSet(viewsets.ModelViewSet):
    queryset = Quittance.objects.all()
    serializer_class = QuittanceSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class DetailQuittanceViewSet(viewsets.ModelViewSet):
    queryset = DetailQuittance.objects.all()
    serializer_class = DetailQuittanceSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class EncaissementViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    
    def get_queryset(self):
        if self.action in ['list', 'retrieve', 'annuler']:
            return Encaissement.objects.select_related('modepaiement', 'banque').prefetch_related("details").filter(Q(piece_annulee=False)).order_by("-dateencaissement")
        
        else:
            return Encaissement.objects.none()

    def list(self, request):
        queryset = self.get_queryset()[:1000]
        serializer = EncaissementSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = self.get_queryset()
        encaissement = get_object_or_404(queryset, pk=pk)
        serializer = EncaissementSerializer(encaissement)
        return Response(serializer.data)

    def create(self, request):
        pass

    def update(self, request, pk=None):
        pass

    def partial_update(self, request, pk=None):
        pass

    def destroy(self, request, pk=None):
        pass
    
        
    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        """
        🆕 Endpoint pour annuler un encaissement avec un jeton d'autorisation
        
        POST /api/encaissement/{id}/annuler/
        Body: {
            "jeton": "ABC12345"
        }
        """
        encaissement = cast(Encaissement, self.get_object())
        
        # Vérifier que l'encaissement n'est pas déjà annulé
        if encaissement.piece_annulee:
            return Response({
                'erreur': 'Cet encaissement est déjà annulé'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validation avec le serializer d'autorisation
        serializer = AnnulerAvecJetonSerializer(
            data=request.data,
            context={'request': request, 'objet': encaissement}
        )
        serializer.is_valid(raise_exception=True)
        
        # Récupérer le jeton validé
        jeton_obj = cast(JetonAutorisation, serializer.validated_data['jeton_obj'])
        
        # Transaction atomique pour garantir la cohérence
        try:
            with transaction.atomic():
                # Utiliser le jeton
                jeton_obj.utiliser(
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Annuler l'encaissement
                cancellation_data = {"id_encaissement":encaissement.idencaissement, "date_annulation":timezone.now().date(), "motif_annulation":jeton_obj.demande.motif}
                (err, qryset) = save_premium_collection_cancellation(request.user.id, cancellation_data)
                data_insertion_serializer = DataInsertionSerializer(qryset, many=True,)
                st = status.HTTP_201_CREATED
                if err:
                    transaction.set_rollback(True) 
                    st = status.HTTP_400_BAD_REQUEST
                return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
        except Exception as error:
            return JsonResponse({"ObjectId":encaissement.idencaissement, "OutputMessage":str(error).split("\n")[0]}, status=status.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def get_client_ip(request):
        """Récupère l'adresse IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=True, methods=['post'])
    def demander_annulation(self, request, pk=None):
        """
        🆕 Raccourci pour créer directement une demande d'annulation
        
        POST /api/encaissement/{id}/demander_annulation/
        Body: {
            "motif": "Erreur de saisie du montant"
        }
        """
        
        encaissement = cast(Encaissement, self.get_object())
        
        if encaissement.piece_annulee:
            return Response({
                'erreur': 'Cet encaissement est déjà annulé'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        motif = request.data.get('motif')
        if not motif or len(motif) < 10:
            return Response({
                'erreur': 'Le motif doit contenir au moins 10 caractères'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer la demande
        content_type = ContentType.objects.get_for_model(Encaissement)
        demande = DemandeAutorisation.objects.create(
            demandeur=request.user,
            type_operation=TypeOperation.ANNULATION_ENCAISSEMENT,
            objet=f"Annulation encaissement {encaissement.numeropiece}",
            motif=motif,
            content_type=content_type,
            object_id=encaissement.idencaissement,
            metadata={
                'reference': encaissement.numeropiece,
                'montant': str(encaissement.montantencaissement),
            }
        )
        
        envoyer_notification_nouvelle_demande.delay(demande.id)
        
        return Response({
            'message': 'Demande d\'annulation créée avec succès',
            'demande_id': demande.id
        }, status=status.HTTP_201_CREATED)


class DetailEncaissementViewSet(viewsets.ModelViewSet):
    queryset = DetailEncaissement.objects.all()
    serializer_class = DetailEncaissementSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

class ContractListView(APIView):
    def get(self, request, format=None):
        # Get query params
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        # Default: current year if not provided
        current_year = date.today().year
        if not start_date_str or not end_date_str:
            start_date = date(current_year, 1, 1)
            end_date = date(current_year, 12, 31)
        else:
            start_date = parse_date_string(start_date_str)
            end_date = parse_date_string(end_date_str)
            if not start_date or not end_date:
                return Response(
                    {"error": "Format de date invalide"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate range
            if end_date < start_date:
                return Response(
                    {"erreur": "La date de fin doit être postérieure à la date de début."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        contracts = (
            Contrat.objects
            .filter(
                    dateemission__range=(start_date, end_date),)
            .filter(Q(idcontratannulation__isnull=True) | Q(idcontratannulation=0))
            .select_related("idclient", "iddevis")
            .annotate(client=F("idclient__Nom"),numerodevis=F("iddevis__numerodevis"))
            .values(
                "client",
                "idcontrat",
                "numerodevis",
                "numeropolice",
                "dateemission",
                "dateeffet",
                "dateexpiration",
                "primenette",
                "accessoire",
                "taxe",
                "primettc",
            )
        )

        return Response(list(contracts))


class ReversementCompagnieNonValideViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    def list(self, request):
        queryset = ReversementCompagnie.objects.filter(Q(valide=False)).select_related("compagnie", "banque").prefetch_related("details").order_by("-date_reversement")[:1000]
        serializer = ReversementCompagnieSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        queryset = ReversementCompagnie.objects.filter(Q(valide=False)).select_related("compagnie", "banque").prefetch_related("details").order_by("-date_reversement")
        reversement = get_object_or_404(queryset, pk=pk)
        serializer = ReversementCompagnieSerializer(reversement)
        return Response(serializer.data)
    
    def create(self, request):
        pass

    def update(self, request, pk=None):
        pass

    def partial_update(self, request, pk=None):
        pass

    def destroy(self, request, pk=None):
        pass
        
    
class ReversementCompagnieViewSet(viewsets.ModelViewSet):    
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def list(self, request):
        queryset = (
            ReversementCompagnie.objects.filter(Q(valide=True)).select_related('compagnie', 'mode_reversement', 'banque').prefetch_related("details").filter(Q(piece_annulee=False))
            .order_by("-date_reversement")[:1000]
        )
        serializer = ReversementCompagnieSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = ReversementCompagnie.objects.filter(Q(valide=True)).select_related('compagnie', 'mode_reversement', 'banque').prefetch_related("details").filter(Q(piece_annulee=False))
        reversement = get_object_or_404(queryset, pk=pk)
        serializer = ReversementCompagnieSerializer(reversement)
        return Response(serializer.data)

    def create(self, request):
        pass

    def update(self, request, pk=None):
        pass

    def partial_update(self, request, pk=None):
        pass

    def destroy(self, request, pk=None):
        pass



class DetailReversementViewSet(viewsets.ModelViewSet):
    queryset = DetailReversement.objects.all()
    serializer_class = DetailReversementSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class NumeroViewSet(viewsets.ModelViewSet):
    queryset = Numero.objects.all()
    serializer_class = NumeroSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


# Create a new quotation (Car Insurance)
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation(request):
    return stored_procedure_result(
        request,
        EnregistrementDevisAutoSerializer,
        save_quotation,
        QuotationInsertionSerializer,
    )
    # enregistrementdevis_data = JSONParser().parse(request)
    # #print("JSON de la requête:", enregistrementdevis_data)
    # enregistrementdevis_serializer = EnregistrementDevisAutoSerializer(
    #     data=enregistrementdevis_data
    # )
    # if enregistrementdevis_serializer.is_valid():
    #     (err, queryset) = save_quotation(enregistrementdevis_data)
    #     data_insertion_serializer = QuotationInsertionSerializer(queryset, many=True)
    #     st = status.HTTP_201_CREATED
    #     if err:
    #         st = status.HTTP_400_BAD_REQUEST
    #     return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    # return JsonResponse(
    #     enregistrementdevis_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    # )


# Finalize a quotation (Car & Personal Accident Insurance)
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def finalize_quotation_flotte(request):
    finalisationdevis_data = JSONParser().parse(request)
    ##print("JSON de la requête:", finalisationdevis_data)
    finalisationdevis_serializer = FinalisationDevisFlotteSerializer(
        data=finalisationdevis_data
    )
    if finalisationdevis_serializer.is_valid():
        (err, qryset) = quotation_completion(finalisationdevis_data)
        data_insertion_serializer = DataInsertionSerializer(qryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        finalisationdevis_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


# Cancel_car_fleet_input
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def quote_archival(request):
    inputcancelation_data = JSONParser().parse(request)
    ##print("JSON de la requête:", inputcancelation_data)
    inputcancelation_serializer = OperationSurDevisSerializer(
        data=inputcancelation_data
    )
    if inputcancelation_serializer.is_valid():
        (err, qryset) = archive_quote(inputcancelation_data, request.user.id)
        data_insertion_serializer = DataInsertionSerializer(qryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST

        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        inputcancelation_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


# Unarchive Quote
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def quote_unarchival(request):
    input_data = JSONParser().parse(request)
    input_serializer = OperationSurDevisSerializer(data=input_data)
    if input_serializer.is_valid():
        (err, qryset) = unarchive_quote(input_data, request.user.id)
        data_insertion_serializer = DataInsertionSerializer(qryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST

        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)

    return JsonResponse(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Car input cancelation
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def car_input_cancelation(request):
    inputcancelation_data = JSONParser().parse(request)
    ##print("JSON de la requête:", inputcancelation_data)
    inputcancelation_serializer = OperationSurDevisDetailSerializer(
        data=inputcancelation_data
    )
    if inputcancelation_serializer.is_valid():
        (err, qryset) = cancel_car_input(inputcancelation_data)
        data_insertion_serializer = DataInsertionSerializer(qryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        inputcancelation_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


# Creation a new quotation (Life Insurance)
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation_ia(request):
    enregistrementdevis_ia_data = JSONParser().parse(request)
    # #print("JSON de la requête:", enregistrementdevis_ia_data)
    enregistrementdevis_ia_serializer = EnregistrementDevisIaSerializer(
        data=enregistrementdevis_ia_data
    )
    if enregistrementdevis_ia_serializer.is_valid():
        (error, queryset) = save_quotation_ia(enregistrementdevis_ia_data)
        data_insertion_serializer = QuotationIaInsertionSerializer(queryset, many=True)
        st = status.HTTP_201_CREATED
        if error:
            st = status.HTTP_400_BAD_REQUEST

        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)

    return JsonResponse(
        enregistrementdevis_ia_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


#############################################################################
# Register an Insured (Personal Accident Insurance)
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_insured_ia(request):
    enregistrementassure_ia_data = JSONParser().parse(request)
    # #print("JSON de la requête:", enregistrementassure_ia_data)
    enregistrement_serializer = EnregistrementDevisIaSerializer(
        data=enregistrementassure_ia_data
    )
    if enregistrement_serializer.is_valid():
        (err, qryset) = save_insured_ia(enregistrementassure_ia_data)
        data_insertion_serializer = DataInsertionSerializer(qryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        enregistrement_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


#############################################################################
# Create a new quotation - Travel Insurance
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation_voyage(request):
    enregistrementdevis_voyage_data = JSONParser().parse(request)
    print("JSON de la requête:", enregistrementdevis_voyage_data)
    enregistrementdevis_voyage_serializer = EnregistrementDevisVoyageSerializer(
        data=enregistrementdevis_voyage_data
    )
    if enregistrementdevis_voyage_serializer.is_valid():
        (err, queryset) = save_quotation_voyage(enregistrementdevis_voyage_data)
        data_insertion_serializer = DataInsertionSerializer(queryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        enregistrementdevis_voyage_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


###########################################################################
# Create new quotation - House Insurance
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation_mrh(request):
    enregistrementdevis_mrh_data = JSONParser().parse(request)
    # #print("JSON de la requête:", enregistrementdevis_mrh_data)
    enregistrementdevis_mrh_serializer = EnregistrementDevisMrhSerializer(
        data=enregistrementdevis_mrh_data
    )
    if enregistrementdevis_mrh_serializer.is_valid():
        (err, queryset) = save_quotation_mrh(
            request.user.id, enregistrementdevis_mrh_data
        )
        data_insertion_serializer = DataInsertionSerializer(queryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        enregistrementdevis_mrh_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


###########################################################################
# Create new quotation - IT Insurance
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation_tousrisquesinfo(request):
    enregistrementdevis_tri_data = JSONParser().parse(request)
    # #print("JSON de la requête:", enregistrementdevis_tri_data)
    enregistrementdevis_tri_serializer = EnregistrementDevisTRInfoSerializer(
        data=enregistrementdevis_tri_data
    )
    if enregistrementdevis_tri_serializer.is_valid():
        (err, queryset) = save_quotation_tousrisquesinfo(
            request.user.id, enregistrementdevis_tri_data
        )
        data_insertion_serializer = DataInsertionSerializer(
            queryset,
            many=True,
        )
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        enregistrementdevis_tri_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


###########################################################################
# Create new quotation - RC
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation_rc(request):
    enregistrementdevis_rc_data = JSONParser().parse(request)
    print("JSON de la requête:", enregistrementdevis_rc_data)
    enregistrementdevis_rc_serializer = EnregistrementDevisRCSerializer(
        data=enregistrementdevis_rc_data
    )
    if enregistrementdevis_rc_serializer.is_valid():
        (err, queryset) = save_quotation_rc(
            request.user.id, enregistrementdevis_rc_data
        )
        data_insertion_serializer = DataInsertionSerializer(
            queryset,
            many=True,
        )
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        enregistrementdevis_rc_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


###########################################################################
# Bank Risk Insurance
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation_globaledebanque(request):
    enregistrementdevis_gdb_data = JSONParser().parse(request)
    # #print("JSON de la requête:", enregistrementdevis_gdb_data)
    enregistrementdevis_gdb_serializer = EnregistrementDevisGlobaleDeBanqueSerializer(
        data=enregistrementdevis_gdb_data
    )
    if enregistrementdevis_gdb_serializer.is_valid():
        (err, queryset) = save_quotation_globaledebanque(
            request.user.id, enregistrementdevis_gdb_data
        )
        data_insertion_serializer = DataInsertionSerializer(
            queryset,
            many=True,
        )
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        enregistrementdevis_gdb_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


###########################################################################
# Creation a new beneficiary IA
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def creer_ayant_droit_ia(request):
    creationayantdroit_data = JSONParser().parse(request)
    # #print("JSON de la requête:", creationayantdroit_data)
    creationayantdroit_serializer = CreationAyantDroitIaSerializer(
        data=creationayantdroit_data
    )
    if creationayantdroit_serializer.is_valid():
        data_insertion_serializer = DataInsertionSerializer(
            enregistrer_ayant_droit(creationayantdroit_data), many=True
        )
        return JsonResponse(
            data_insertion_serializer.data, status=status.HTTP_201_CREATED, safe=False
        )
    return JsonResponse(
        creationayantdroit_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


# Change quotation into contract
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_contract(request):
    confirmationdevis_data = JSONParser().parse(request)
    # print("JSON de la requête:", confirmationdevis_data)
    confirmationdevis_serializer = OperationSurDevisSerializer(
        data=confirmationdevis_data
    )
    if confirmationdevis_serializer.is_valid():
        (err, qryset) = save_contract(confirmationdevis_data)
        data_insertion_serializer = DataInsertionSerializer(qryset, many=True)
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        elif not settings.DEBUG and settings.URANUS_IN_PRODUCTION:
            send_sms_enregistrement_contrat.delay(
                int(data_insertion_serializer.data[0]["ObjectId"])
            )
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)

    return JsonResponse(
        confirmationdevis_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


class AssureIaParDevisView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddevis):
        (msg, assures) = get_liste_assure_ia(id=iddevis, statut="DEV")
        if not msg:
            serializer = AssureIaParDevisOuContratSerializer(assures, many=True)
            # print(serializer)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)
        else:
            return JsonResponse(
                {"Status": "Echec", "Data": msg}, status=status.HTTP_400_BAD_REQUEST
            )


class AssureIaParContratView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcontrat):
        (msg, assures) = get_liste_assure_ia(id=idcontrat, statut="CNT")
        if not msg:
            serializer = AssureIaParDevisOuContratSerializer(assures, many=True)
            # print(serializer.data)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)
        else:
            return JsonResponse(
                {"Status": "Echec", "Data": msg}, status=status.HTTP_400_BAD_REQUEST
            )


class AssureIaInfoView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddevis):
        (msg, assureiainfo) = get_assure_ia(iddevis)
        if not msg:
            serializer = AssureIaInfoSerializer(assureiainfo, many=True)
            # print(serializer.data)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)
        else:
            return JsonResponse(
                {"Status": "Echec", "Data": msg}, status=status.HTTP_400_BAD_REQUEST
            )


class DevisDetailInfoView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddevis):
        r_status = status.HTTP_200_OK
        devisdetail = DevisDetail.objects.none()
        try:
            devis = Devis.objects.get(pk=iddevis)
            if devis:
                devisdetail = DevisDetail.objects.filter(iddevis=devis)
                if not devisdetail.exists():
                    r_status = status.HTTP_404_NOT_FOUND
        except Devis.DoesNotExist as e_not_exists:
            print(e_not_exists)
            r_status = status.HTTP_404_NOT_FOUND
        except Exception as error:
            print(error)
            r_status = status.HTTP_400_BAD_REQUEST

        serializer = DevisDetailSerializer(devisdetail, many=True)
        return JsonResponse(serializer.data, status=r_status, safe=False)


class ContratDetailInfoView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcontrat):
        contratdetail = ContratDetail.objects.filter(idcontrat=idcontrat)
        serializer = ContratDetailSerializer(contratdetail, many=True)
        # print(serializer.data)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)


class QuittancePropositionView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddevis):
        (msg, item) = get_quotation_info(iddevis=iddevis)
        if not msg:
            serializer = QuittancePropositionSerializer(item, many=True)
            # print(serializer.data)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


###########################################
### Quittance Contrat
class QuittanceContratView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcontrat):
        (msg, item) = get_contract_info(idcontrat=idcontrat)
        if not msg:
            serializer = QuittanceContratSerializer(item, many=True)
            # print(serializer.data)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


###########################################
### Garantie Contrat
class GarantieContratView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcontrat):
        (msg, item) = get_contract_coverage(idcontrat=idcontrat)
        if not msg:
            serializer = GarantieContratFlotteSerializer(item, many=True)
            # print(serializer.data)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


def get_liste_vehicule(id, contrat=True):
    (msg, item) = get_contract_car_list(id=id, contrat=contrat)
    if not msg:
        serializer = VehiculeContratSerializer(item, many=True)
        # print(serializer.data)
        return Response(
            {"status": "succès", "data": serializer.data},
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {"status": "Echec", "data": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )


###########################################
### Liste Vehicule Contrat
class ListeVehiculeContratView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcontrat):
        return get_liste_vehicule(id=idcontrat)


###########################################
### Liste Vehicule Devis
class ListeVehiculeDevisView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddevis):
        return get_liste_vehicule(id=iddevis, contrat=False)


###########################################
### Liste des quittances à reverser
class ListeContratReversementView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcompagnie):
        (msg, item) = get_contract_premium_remittance(idcompagnie=idcompagnie)
        if not msg:
            serializer = ContractForPremiumCollectionSerializer(item, many=True)
            # print(serializer.data)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


####################################################################
# fn_info_encaissement
#################################################################
class InfoEncaissementView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddetailencaissement):
        (msg, item) = get_info_encaissement(detailencaissement=iddetailencaissement)
        if not msg:
            serializer = PremiumCollectionInfoSerializer(item, many=True)
            # print(serializer.data)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


# fn_get_info_vehicule
class InfoVehiculeView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcontrat):
        (msg, item) = get_info_vehicule(idcontrat=idcontrat)
        if not msg:
            serializer = InfoVehiculeSerializer(item, many=True)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


####################################################################
# fn_info_reversement
#################################################################
class InfoReversementView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idreversement):
        (msg, item) = get_info_reversement(reversement=idreversement)
        if not msg:
            serializer = PremiumRemittanceInfoSerializer(item, many=True)
            # print(serializer.data)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


#########################################################
class DetailEncaissementListView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idencaissement):
        try:
            encaissement = Encaissement.objects.get(pk=idencaissement)
        except Encaissement.DoesNotExist:
            return Response(
                {"status": "Aucune donnée", "data": ""},
                status=status.HTTP_204_NO_CONTENT,
            )
        else:
            details = DetailEncaissement.objects.filter(encaissement=encaissement)
            if details.exists():
                serializer = DetailEncaissementSerializer(details, many=True)
                # print(serializer.data)
                return Response(
                    {"status": "Succès", "data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "status": "Echec",
                        "data": "Incohérence: encaissement sans détails.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )


#########################################################
class DetailReversementListView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idreversement):
        try:
            reversement = ReversementCompagnie.objects.get(pk=idreversement)
        except ReversementCompagnie.DoesNotExist:
            return Response(
                {"status": "Aucune donnée", "data": ""},
                status=status.HTTP_204_NO_CONTENT,
            )
        else:
            details = DetailReversement.objects.filter(reversement=reversement)
            if details.exists():
                serializer = DetailReversementSerializer(details, many=True)
                # print(serializer.data)
                return Response(
                    {"status": "Succès", "data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "status": "Echec",
                        "data": "Incohérence: reversement sans détails.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )


# class EncaissementRechercheView(APIView):
#     permission_classes = [
#         permissions.IsAuthenticated,
#     ]


#     def get(self, request, champrecherche):
#         criteria = str(champrecherche).strip()
# (msg, qryset)
# if valid_email_address(criteria):
#     clientrecherche = Client.objects.filter(Q(Email=criteria) & ~Q(IdClient=0))
# else:
#     phone_number_part = valid_phone_number(criteria)
#     if phone_number_part:
#         clientrecherche = Client.objects.filter(
#             (
#                 Q(Mobile__contains=phone_number_part)
#                 | Q(Telephone__contains=phone_number_part)
#                 | Q(Fixe__contains=phone_number_part)
#             )
#             & ~Q(IdClient=0)
#         )
#     else:
#         clientrecherche = Client.objects.filter(
#             Q(Nom__contains=criteria) & ~Q(IdClient=0)
#         )
# serializer = ClientSerializer(clientrecherche, many=True)
# print(serializer.data)
# return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)


class ImportationFichierGUCEViewSet(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        messages = []
        serializer_class = ImportationTransportSerializer(data=request.data)
        if "fichier_excel" not in request.FILES or not serializer_class.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            (error_occured, messages) = export_excel(
                request.FILES["fichier_excel"],
                request.user.id,
                request.POST["debut_periode"],
                request.POST["fin_periode"],
            )
            data_insertion_serializer = DataInsertionSerializer(messages, many=True)
            if not error_occured:
                return Response(
                    data=data_insertion_serializer.data, status=status.HTTP_202_ACCEPTED
                )
            else:
                return Response(
                    data=data_insertion_serializer.data,
                    status=status.HTTP_400_BAD_REQUEST,
                )


class ExtendedQuotationInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, idproduit):
        # Récupération des paramètres de pagination de l'URL
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        nom_client = request.query_params.get('nom_client', '')
        numero_police = request.query_params.get('numero_police', '')
        
        # Calcul de l'offset
        limit = page_size
        offset = (page - 1) * page_size
        
        (msg, devis_list, total_count) = get_extended_quotation_info(
            0, numero_police, nom_client, None, None, idproduit, limit=limit, offset=offset
        )
        
        if not msg:
            serializer = ExtendedQuotationInfoSerializer(devis_list, many=True)
            
            # Réponse structurée avec données et méta-pagination
            return Response(
                {
                    "status": "succès", 
                    "data": serializer.data,
                    "pagination": {
                        "total_items": total_count,
                        "page_size": limit,
                        "current_page": page,
                        "total_pages": (total_count + limit - 1) // limit
                    }
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )

class ExtendedQuotationInfoRechercheView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, champrecherche):
        parameters = str(champrecherche).strip().split("_")
        (id_devis, numero_devis, nom_client, date_debut, date_fin) = (
            0,
            "",
            "",
            None,
            None,
        )
        try:
            if len(parameters) == 5:
                if parameters[0]:
                    id_devis = int(parameters[0])
                if parameters[1]:
                    numero_devis = str(parameters[1])
                if parameters[2]:
                    nom_client = str(parameters[2])
                if parameters[3]:  # "%d-%m-%Y"
                    date_debut = datetime.strptime(
                        str(parameters[3]), "%Y-%m-%d"
                    ).date()
                if parameters[4]:
                    date_fin = datetime.strptime(str(parameters[4]), "%Y-%m-%d").date()
        except Exception as error:
            return Response(
                {"status": "Echec", "data": str(error).split(":")[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            (msg, item) = get_extended_quotation_info(
                id_devis, numero_devis, nom_client, date_debut, date_fin
            )
            if not msg:
                serializer = ExtendedQuotationInfoSerializer(item, many=True)
                # print(serializer.data)
                return Response(
                    {"status": "succès", "data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"status": "Echec", "data": msg},
                    status=status.HTTP_400_BAD_REQUEST,
                )


class ReductionFlotteDevisView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, iddevis):
        taux_reduction_flotte = get_taux_reduction_flotte(iddevis)
        (statut_msg, statut_code) = (
            ("Succès", status.HTTP_200_OK)
            if taux_reduction_flotte >= 0
            else ("Echec", status.HTTP_400_BAD_REQUEST)
        )
        return Response(
            {"Status": statut_msg, "TauxReduction": str(taux_reduction_flotte)},
            status=statut_code,
        )


class GarantieSouscriteView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_garantie(self, id_entite, type_entite):
        msg, garanties = get_garantie_souscrite(id_entite, type_entite)
        if not msg:
            serializer = GarantieSouscriteSerializer(garanties, many=True)
            return Response(
                {"Status": "Succès", "Data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"Status": "Echec", "Data": msg}, status=status.HTTP_400_BAD_REQUEST
            )


class GarantieSouscriteContratView(GarantieSouscriteView):
    def get(self, request, idcontrat):
        return self.get_garantie(idcontrat, "CNT")


class GarantieSouscriteDevisView(GarantieSouscriteView):
    def get(self, request, iddevis):
        return self.get_garantie(iddevis, "DEV")


# Save Premium collection
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def collect_premium(request):
    enregistrementencaissement_data = JSONParser().parse(request)
    print("JSON de la requête:", enregistrementencaissement_data)
    enregistrementencaissement_serializer = EncaissementGroupeQuittanceSerializer(
        data=enregistrementencaissement_data
    )
    if enregistrementencaissement_serializer.is_valid():
        (err, qryset) = save_premium_collection(
            request.user.id, enregistrementencaissement_data
        )

        data_insertion_serializer = DataInsertionSerializer(
            qryset,
            many=True,
        )
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        elif not settings.DEBUG and settings.URANUS_IN_PRODUCTION:
            send_sms_encaissement_contrat.delay(
                int(data_insertion_serializer.data[0]["ObjectId"])
            )

        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        enregistrementencaissement_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


# Cancel Premium collection
# @api_view(["POST"])
# @authentication_classes([TokenAuthentication, BasicAuthentication])
# @permission_classes([permissions.IsAuthenticated])
# def cancel_premium_collection(request):
#     annulationencaissement_data = JSONParser().parse(request)
#     # print("JSON de la requête:", enregistrementencaissement_data)
#     annulationencaissement_serializer = AnnulationEncaissementSerializer(
#         data=annulationencaissement_data
#     )
#     if annulationencaissement_serializer.is_valid():
#         (err, qryset) = save_premium_collection_cancellation(
#             request.user.id, annulationencaissement_data
#         )

#         data_insertion_serializer = QuotationInsertionSerializer(
#             qryset,
#             many=True,
#         )
#         st = status.HTTP_201_CREATED
#         if err:
#             st = status.HTTP_400_BAD_REQUEST

#         return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
#     return JsonResponse(
#         annulationencaissement_serializer.errors, status=status.HTTP_400_BAD_REQUEST
#     )


##################################################################################
# Save Premium Remittance
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def remit_premium(request):
    enregistrement_data = JSONParser().parse(request)
    # print("JSON de la requête:", enregistrement_data)
    reversement_serializer = ReversementGroupePrimeInsertSerializer(
        data=enregistrement_data
    )
    if reversement_serializer.is_valid():
        validated_data = reversement_serializer.validated_data
        data_insertion_serializer = DataInsertionSerializer(
            save_premium_remittance(request.user.id, validated_data),
            many=True,
        )
        return JsonResponse(
            data_insertion_serializer.data, status=status.HTTP_201_CREATED, safe=False
        )
    return JsonResponse(
        reversement_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


##################################################################################
# Save Premium Remittance
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def validate_premium_remittance(request):
    enregistrement_data = JSONParser().parse(request)
    reversement_serializer = ReversementGroupePrimeValidateSerializer(
        data=enregistrement_data
    )
    if reversement_serializer.is_valid():
        validated_data = reversement_serializer.validated_data
        error, queryset = premium_remittance_validation(request.user.id, validated_data)
        data_insertion_serializer = DataInsertionSerializer(queryset,
            many=True,
        )
        resp_status = status.HTTP_201_CREATED
        if error:
            resp_status = status.HTTP_400_BAD_REQUEST
        return JsonResponse(
            data_insertion_serializer.data, status=resp_status, safe=False
        )
    return JsonResponse(
        reversement_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


##################################################################################
# Change Plate Number
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def change_plate_number(request):
    chgplatenumber_data = JSONParser().parse(request)
    # print("JSON de la requête:", chgplatenumber_data)
    chgplatenumber_serializer = ChangementImmatriculationSerializer(
        data=chgplatenumber_data
    )
    if chgplatenumber_serializer.is_valid():
        (err, qryset) = save_plate_number(request.user.id, chgplatenumber_data)
        data_insertion_serializer = DataInsertionSerializer(
            qryset,
            many=True,
        )
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        chgplatenumber_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


##################################################################################
# Cancel Policy, Renew Policy or Change Effective Date
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def modify_policy(request):
    cancelpolicy_data = JSONParser().parse(request)
    print("JSON de la requête:", cancelpolicy_data)
    cancelpolicy_serializer = AvenantAnlRenSerializer(data=cancelpolicy_data)
    if cancelpolicy_serializer.is_valid():
        (err, qryset) = policy_modification(request.user.id, cancelpolicy_data)
        data_insertion_serializer = DataInsertionSerializer(
            qryset,
            many=True,
        )
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
    return JsonResponse(
        cancelpolicy_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


##################################################################################
# Renew Policy
# @api_view(["POST"])
# @authentication_classes([TokenAuthentication, BasicAuthentication])
# @permission_classes([permissions.IsAuthenticated])
# def renew_policy(request):
#     renewpolicy_data = JSONParser().parse(request)
#     #print("JSON de la requête:", renewpolicy_data)
#     renewpolicy_serializer = AvenantAnlRenSerializer(data=renewpolicy_data)
#     if renewpolicy_serializer.is_valid():
#         (err, qryset) = policy_cancellation_or_renewal(
#             request.user.id, renewpolicy_data
#         )
#         data_insertion_serializer = DataInsertionSerializer(
#             qryset,
#             many=True,
#         )
#         st = status.HTTP_201_CREATED
#         if err:
#             st = status.HTTP_400_BAD_REQUEST
#         return JsonResponse(data_insertion_serializer.data, status=st, safe=False)
#     return JsonResponse(
#         renewpolicy_serializer.errors, status=status.HTTP_400_BAD_REQUEST
#     )
class ListeContratClientView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, *args, **kwargs):
        idproduit = request.query_params.get("idproduit")
        idclient = request.query_params.get("idclient")
        nomclient = request.query_params.get("nomclient")
        telephoneclient = request.query_params.get("telephoneclient")
        numeropolice = request.query_params.get("numeropolice")
        if idproduit is None:
            idproduit = 0
        if idclient is None:
            idclient = 0

        (msg, item) = get_contract_list_for_customer(
            nom_client=nomclient,
            telephone_client=telephoneclient,
            numero_police=numeropolice,
            id_produit=idproduit,
            id_client=idclient,
        )
        if not msg:
            serializer = ContractForPremiumCollectionSerializer(item, many=True)
            # print(serializer.data)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


#################################################################################
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_contracts_for_pc(request):
    contratdemande_data = JSONParser().parse(request)
    contratdemande_serializer = DemandeContratPourEncaissementSerializer(
        data=contratdemande_data
    )
    if contratdemande_serializer.is_valid():
        referenceclient = str(contratdemande_data["referenceclient"])
        referencecontrat = str(contratdemande_data["referencecontrat"])
        (msg, item) = get_contract_list_for_pc(referenceclient, referencecontrat)
        if not msg:
            serializer = ContractForPremiumCollectionSerializer(item, many=True)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return JsonResponse(
        contratdemande_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


class CorrectionDevisViewSet(viewsets.ViewSet):
    """
    API endpoint pour corriger les devis.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        """
        Traite la requête POST pour corriger un devis déjà existant.
        """
        serializer = CorrectionDevisSerializer(data=request.data)
        if serializer.is_valid():
            result = correction_devis(serializer.validated_data)
            if result["success"]:
                return Response(
                    {"message": "Devis corrigé avec succès."},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": result["message"]},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PrimeUpdateAPIView(APIView):
    """
    Endpoint to manually update prime values by calling the PL/pgSQL stored procedure.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request, *args, **kwargs):
        serializer = PrimeUpdateSerializer(data=request.data)

        if serializer.is_valid():
            # Extract validated data
            validated_data = serializer.validated_data

            p_numero_devis = validated_data["numero_devis"]
            p_prime_annuelle = validated_data["prime_annuelle"]
            p_prime_nette = validated_data["prime_nette"]
            p_accessoire = validated_data["accessoire"]
            p_taxe = validated_data["taxe"]
            p_fga = validated_data["fga"]
            p_cedeao = validated_data["cedeao"]
            p_prime_ttc = validated_data["prime_ttc"]

            try:
                # Call the utility function to execute the stored procedure
                execute_maj_manuelle_primes(
                    p_numero_devis,
                    p_prime_annuelle,
                    p_prime_nette,
                    p_accessoire,
                    p_taxe,
                    p_fga,
                    p_cedeao,
                    p_prime_ttc,
                )

                return Response(
                    {
                        "message": "Mise à jour des primes effectuée avec succès.",
                        "numero_devis": p_numero_devis,
                    },
                    status=status.HTTP_200_OK,
                )

            except Exception as e:
                # Handle database or execution errors
                return Response(
                    {"message": "Error executing stored procedure.", "details": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# ============================================================================
# SECTION 1 : ENDPOINTS DE RÉFÉRENCE (LECTURE SEULE)
# ============================================================================

class UsageHabitationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour lister les usages habitation disponibles.
    
    GET /api/mrh/usages/
    GET /api/mrh/usages/{code}/
    """
    queryset = UsageHabitation.objects.filter(actif=True).order_by('libelle')
    serializer_class = UsageHabitationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'code'
    
    @action(detail=True, methods=['get'])
    def parametres(self, request, code=None):
        """
        Retourne les paramètres de calcul pour un usage spécifique.
        
        GET /api/mrh/usages/{code}/parametres/
        """
        usage = cast(UsageHabitation, self.get_object())
        
        try:
            parametres = usage.parametres
            serializer = ParametresCalculSerializer(parametres)
            return Response(serializer.data)
        except ParametresCalcul.DoesNotExist:
            return Response(
                {'erreur': f'Paramètres de calcul non trouvés pour {code}'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def garanties(self, request, code=None):
        """
        Retourne les sous-garanties (obligatoires et optionnelles) pour un usage.
        
        GET /api/mrh/usages/{code}/garanties/
        """
        usage = cast(UsageHabitation, self.get_object())
        
        # Garanties obligatoires
        sous_garanties_oblig = usage.sous_garanties_liees.filter(
            obligatoire=True,
            actif=True
        ).select_related('sous_garantie').order_by('ordre_affichage')
        
        # Garanties optionnelles
        sous_garanties_opt = usage.sous_garanties_liees.filter(
            obligatoire=False,
            actif=True
        ).select_related('sous_garantie').order_by('ordre_affichage')
        
        return Response({
            'obligatoires': [
                {
                    'code': gu.sous_garantie.code,
                    'libelle': gu.sous_garantie.libelle,
                    'taux_repartition': gu.taux_repartition,
                }
                for gu in sous_garanties_oblig
            ],
            'optionnelles': [
                {
                    'code': gu.sous_garantie.code,
                    'libelle': gu.sous_garantie.libelle,
                }
                for gu in sous_garanties_opt
            ]
        })
    
    @action(detail=True, methods=['get'])
    def offres(self, request, code=None):
        """
        Retourne les offres pour un usage.
        
        GET /api/mrh/usages/{code}/offres/
        """
        usage = cast(UsageHabitation, self.get_object())
        
        offre_mrh_liee = usage.offre
        return Response({

                    'id_offre': offre_mrh_liee.IdOffre if offre_mrh_liee else "",
                    'libelle_offre': offre_mrh_liee.LibelleOffre if offre_mrh_liee else "",

        }, status = status.HTTP_200_OK)
    
    
    
    @action(detail=True, methods=['get'])
    def options(self, request, code=None):
        """
        Retourne les options applicables à un usage.
        
        GET /api/mrh/usages/{code}/options/
        """
        usage = self.get_object()
        
        options = Option.objects.filter(
            usages_applicables__usage=usage,
            usages_applicables__actif=True,
            actif=True
        ).distinct().order_by('type_option', 'libelle')
        
        serializer = OptionSerializer(options, many=True)
        return Response(serializer.data)


class SousGarantieMRHViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour lister les sous-garanties MRH.
    
    GET /api/mrh/sous-garanties/
    GET /api/mrh/sous-garanties/{code}/
    """
    queryset = SousGarantieMRH.objects.filter(actif=True).order_by('type', 'libelle')
    serializer_class = SousGarantieMRHSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'code'


class SousGarantieForfaitViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour lister les garanties optionnelles à forfait.
    
    GET /api/mrh/sous-garanties-forfait/
    """
    queryset = SousGarantieForfait.objects.filter(actif=True).select_related('sous_garantie')
    serializer_class = SousGarantieForfaitSerializer
    permission_classes = [IsAuthenticated]


class OptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour lister les options disponibles.
    
    GET /api/mrh/options/
    GET /api/mrh/options/{code}/
    """
    queryset = Option.objects.filter(actif=True).order_by('type_option', 'libelle')
    serializer_class = OptionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'code'


# ============================================================================
# MISE A JOUR DU DEVIS
# ============================================================================
class MiseAJourDevis (APIView):
    @action(detail=True, methods=['post'])
    def garanties(self, request, pk=None):
        """
        Met à jour un devis avec les informations.
        
        GET /api/mrh/devis//garanties/
        """
        usage = cast(UsageHabitation, self.get_object())
        
        # Garanties obligatoires
        sous_garanties_oblig = usage.sous_garanties_liees.filter(
            obligatoire=True,
            actif=True
        ).select_related('sous_garantie').order_by('ordre_affichage')
        
        # Garanties optionnelles
        sous_garanties_opt = usage.sous_garanties_liees.filter(
            obligatoire=False,
            actif=True
        ).select_related('sous_garantie').order_by('ordre_affichage')
        
        return Response({
            'obligatoires': [
                {
                    'code': gu.sous_garantie.code,
                    'libelle': gu.sous_garantie.libelle,
                    'taux_repartition': gu.taux_repartition,
                }
                for gu in sous_garanties_oblig
            ],
            'optionnelles': [
                {
                    'code': gu.sous_garantie.code,
                    'libelle': gu.sous_garantie.libelle,
                }
                for gu in sous_garanties_opt
            ]
        })

# ============================================================================
# SECTION 2 : ENDPOINT DE CALCUL (SANS ENREGISTREMENT)
# ============================================================================

class CalculMaisonView(APIView):
    """
    Calcule la prime d'une maison SANS l'enregistrer.
    Utile pour des simulations ou devis rapides.
    
    POST /api/mrh/calcul/maison/
    
    Body:
    {
        "code_usage": "proprietaire_occupant_total",
        "valeur_batiment": 50000000,
        "valeur_contenu": 10000000,
        "options": ["presence_gardien"],
        "sous_garanties_optionnelles": ["RC_MEMBRE"]
    }
    
    Response:
    {
        "code_usage": "proprietaire_occupant_total",
        "libelle_usage": "Propriétaire Occupant Total",
        "prime_base": 152000.00,
        "prime_nette_totale": 153680.00,
        "taxe_totale": 27869.60,
        "prime_ttc_totale": 181549.60,
        "sous_garanties": [...],
        "options_appliquees": [...]
    }
    """
    permission_classes = [IsAuthenticated]
                                    
    def post(self, request):
        # Valider les données d'entrée
        serializer = MaisonCalculRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        service = MRHCalculService()
        
        try:
            # Calculer la prime
            resultat = service.calculer_maison(
                code_usage=data['code_usage'],
                valeur_batiment=data.get('valeur_batiment'),
                valeur_contenu=data.get('valeur_contenu'),
                loyer_mensuel=data.get('loyer_mensuel'),
                capital_rvt=data.get('capital_rvt'),
                options=[opt['code_option'] for opt in data.get('options', [])],
                sous_garanties_optionnelles=[
                    gar['code_sous_garantie'] for gar in data.get('sous_garanties_optionnelles', [])
                ],
                adresse=data.get('adresse'),
                description=data.get('description'),
            )
            
            # Sérialiser la réponse
            response_serializer = MaisonCalculeeSerializer(resultat)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# SECTION 3 : ENDPOINTS DE GESTION DE DEVIS
# ============================================================================

class DevisMRHViewSet(viewsets.ViewSet):
    """
    ViewSet pour la gestion des devis MRH.
    
    POST /api/mrh/devis/ - Créer un devis vide
    GET /api/mrh/devis/{id}/ - Récupérer un devis
    PATCH /api/mrh/devis/{id}/finalisation
    GET /api/mrh/devis/ - Lister les devis
    DELETE /api/mrh/devis/{id}/ - Supprimer un devis
    """
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        """
        Crée un nouveau devis MRH vide.
        
        POST /api/mrh/devis/
        
        Body:
        {
            "idintermediaire": 1,
            "idcompagnie": 1,
            "idproduit": 4,
            "idtarif": 81
            "idoffre": 10,
            "idclient": 123,
            "dateeffet": "2024-01-01T00:00:00Z",
            "observation": "Devis MRH Villa Cocody"
        }
        """
        serializer = DevisMRHCreateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        service = MRHCalculService()
        
        try:
            # Créer le devis
            id_devis = service.creer_devis(
                idintermediaire=data['idintermediaire'],
                idcompagnie=data['idcompagnie'],
                idproduit=data['idproduit'],
                idtarif=data['idtarif'],
                idoffre=data['idoffre'],
                idclient=data['idclient'],
                dateeffet=data['dateeffet'],
                **{k: v for k, v in data.items() if k not in [
                    'idintermediaire', 'idcompagnie', 'idproduit', 'idtarif',
                    'idoffre', 'idclient', 'dateeffet'
                ]}
            )
            
            # Retourner la réponse
            from .models import Devis  # Import local
            devis = Devis.objects.get(iddevis=id_devis)
            
            response_data = {
                'devis_id': id_devis,
                'numero_devis': devis.numerodevis or '',
                'statut': 'success',
                'message': 'Devis créé avec succès',
                'date_creation': devis.dateemission,
            }
            
            response_serializer = DevisMRHResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    def partial_update(self, request, pk=None):
        mrh_devis = get_object_or_404(Devis, pk=pk)
        from customer.models import Client
        idassure = request.data.get("idassure", 0)
        idclient = request.data.get("idclient", 0)
        numero_telephone_assure = request.data.get("numerotelephoneassure", "")
        
        # Pass update_data instead of request.data
        try:
            with transaction.atomic():
                if idclient:
                    mrh_devis.client_id = idclient
                if idassure:
                    mrh_devis.assure_id = idassure
                mrh_devis.save()
                if numero_telephone_assure and idassure:
                        assure = Client.objects.filter(IdClient=idassure).first()
                        assure.Mobile = numero_telephone_assure
                        assure.save()
                
                return Response({"message":"Devis enregistré avec succès"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"erreur":str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        """
        Récupère les détails d'un devis avec toutes ses maisons.
        
        GET /api/mrh/devis/{id}/
        """
        from .models import Devis, DevisDetail  # Import local
        
        try:
            devis = Devis.objects.get(iddevis=pk)
            maisons = DevisDetail.objects.filter(iddevis_id=pk)
            
            # Construire la réponse
            response_data = {
                'devis_id': devis.iddevis,
                'numero_devis': devis.numerodevis,
                'statut': 'success',
                'message': 'Devis récupéré avec succès',
                'prime_nette_totale': devis.primenette,
                'taxe_totale': devis.taxe,
                'accessoires': devis.accessoire,
                'prime_ttc_totale': devis.primettc,
                'maisons': [
                    {
                        'maison_id': str(m.iddevisdetail),
                        'code_usage': m.observation[:30] if m.observation else '',  # Approximatif
                        'libelle_usage': m.observation[:30] if m.observation else '',
                        'parametres': {
                            'valeur_batiment': m.valeurneuve,
                            'valeur_contenu': m.valeurvenale,
                        },
                        'prime_nette_totale': m.primenette,
                        'prime_annuelle_totale': m.primeannuelle,
                        'taxe_totale': m.taxeenregistrement,
                        'prime_ttc_totale': m.primenette + m.taxeenregistrement,
                        'sous_garanties': [],  # Peut être enrichi si besoin
                        'options_appliquees': [],
                        'adresse': m.observation[33:] if len(m.observation or '') > 33 else '',
                    }
                    for m in maisons
                ],
                'nombre_maisons': maisons.count(),
                'date_calcul': devis.dateemission,
            }
            
            
            serializer = DevisMRHCalculeResponseSerializer(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Devis.DoesNotExist:
            return Response(
                {'error': f'Devis {pk} non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request):
        """
        Liste les devis (avec filtres optionnels).
        
        GET /api/mrh/devis/?client={id}&statut={statut}
        """
        from .models import Devis  # Import local
        
        queryset = Devis.objects.all().order_by('-dateemission')
        
        # Filtres optionnels
        client_id = request.query_params.get('client', None)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        statut = request.query_params.get('statut', None)
        if statut:
            queryset = queryset.filter(statut=statut)
        
        # Pagination simple
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        devis_list = queryset[start:end]
        
        data = [
            {
                'devis_id': d.iddevis,
                'numero_devis': d.numerodevis,
                'client': d.client_id,
                'date_effet': d.dateeffet,
                'prime_ttc': d.primettc,
                'statut': d.statut,
            }
            for d in devis_list
        ]
        
        return Response({
            'count': queryset.count(),
            'page': page,
            'page_size': page_size,
            'results': data
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, pk=None):
        """
        Supprime un devis (et toutes ses maisons en cascade).
        
        DELETE /api/mrh/devis/{id}/
        """
        from .models import Devis  # Import local
        
        try:
            devis = Devis.objects.get(iddevis=pk)
            
            # Vérifier que le devis n'est pas confirmé
            if devis.confirme:
                return Response(
                    {'error': 'Impossible de supprimer un devis confirmé'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            devis.delete()
            
            return Response(
                {'message': f'Devis {pk} supprimé avec succès'},
                status=status.HTTP_204_NO_CONTENT
            )
        
        except Devis.DoesNotExist:
            return Response(
                {'error': f'Devis {pk} non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# SECTION 4 : ENDPOINTS DE GESTION DE MAISONS
# ============================================================================

class MaisonViewSet(viewsets.ViewSet):
    """
    ViewSet pour la gestion des maisons dans un devis.
    
    POST /api/mrh/devis/{devis_id}/maisons/ - Ajouter une maison
    DELETE /api/mrh/devis/{devis_id}/maisons/{maison_id}/ - Supprimer une maison
    """
    permission_classes = [IsAuthenticated]
    
    def create(self, request, devis_id=None):
        """
        Ajoute une maison à un devis existant.
        Calcule la prime et enregistre dans la base.
        Met à jour automatiquement les totaux du devis.
        
        POST /api/mrh/devis/{devis_id}/maisons/
        
        Body:
        {
            "maison": {
                "code_usage": "proprietaire_occupant_total",
                "id_tarif":81,
                "id_offre": 10,
                "valeur_batiment": 50000000,
                "valeur_contenu": 10000000,
                "options": ["presence_gardien"],
                "sous_garanties_optionnelles": ["RC_MEMBRE"],
                "adresse": "Cocody, Angré"
            }
        }
        """
        from .models import Devis
        
        # Vérifier que le devis existe
        try:
            devis = Devis.objects.get(iddevis=devis_id)
        except Devis.DoesNotExist:
            return Response(
                {'erreur': f'Devis {devis_id} non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Valider les données
        serializer = MaisonAjoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data['maison']
        service = MRHCalculService()
        
        if not offre_mrh_compatible(data["id_offre"], data["code_usage"]):
            return Response(
                {'erreur': "Offre incompatible avec l'usage"},
                status=status.HTTP_400_BAD_REQUEST
            )
         
        try:
            # Calculer et enregistrer la maison
            resultat = service.calculer_et_enregistrer_maison(
                id_devis=devis_id,
                id_produit=devis.produit_id,
                id_compagnie=devis.compagnie_id,
                id_tarif=data.get('id_tarif'),
                id_offre=data.get('id_offre'),
                code_usage=data['code_usage'],
                valeur_batiment=data.get('valeur_batiment'),
                valeur_contenu=data.get('valeur_contenu'),
                loyer_mensuel=data.get('loyer_mensuel'),
                capital_rvt=data.get('capital_rvt'),
                options=[opt['code_option'] for opt in data.get('options', [])],
                sous_garanties_optionnelles=[
                    gar['code_sous_garantie'] for gar in data.get('sous_garanties_optionnelles', [])
                ],
                adresse=data.get('adresse'),
                description=data.get('description'),
            )
            
            # Construire la réponse
            response_data = {
                'devis_id': devis_id,
                'maison_id': resultat['id_maison'],
                'statut': 'success',
                'message': 'Maison ajoutée avec succès',
                'calcul': resultat['calcul'],
            }
            
            response_serializer = MaisonAjouteeResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, devis_id=None, pk=None):
        """
        Supprime une maison d'un devis.
        Met à jour automatiquement les totaux du devis.
        
        DELETE /api/mrh/devis/{devis_id}/maisons/{maison_id}/
        """
        from .models import Devis, DevisDetail  # Import local
        
        try:
            # Vérifier que le devis existe
            devis = Devis.objects.get(iddevis=devis_id)
            
            # Vérifier que la maison existe et appartient bien au devis
            maison = DevisDetail.objects.get(
                iddevisdetail=pk,
                iddevis_id=devis_id
            )
            
            # Supprimer la maison (les garanties seront supprimées en cascade)
            maison.delete()
            
            # Mettre à jour les totaux du devis
            service = MRHCalculService()
            totaux = service.mettre_a_jour_totaux_devis(
                id_devis=devis_id,
                id_produit=devis.produit_id,
                id_compagnie=devis.compagnie_id,
                inclure_accessoires=True
            )
            
            return Response(
                {
                    'message': f'Maison {pk} supprimée avec succès',
                    'totaux_devis': totaux
                },
                status=status.HTTP_200_OK
            )
        
        except Devis.DoesNotExist:
            return Response(
                {'error': f'Devis {devis_id} non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except DevisDetail.DoesNotExist:
            return Response(
                {'error': f'Maison {pk} non trouvée dans le devis {devis_id}'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# SECTION 5 : ENDPOINTS UTILITAIRES
# ============================================================================

class ValidateParametersView(APIView):
    """
    Valide les paramètres pour un usage donné sans faire de calcul.
    Utile pour validation côté frontend.
    
    POST /api/mrh/validate-parameters/
    
    Body:
    {
        "code_usage": "proprietaire_occupant_total",
        "valeur_batiment": 50000000,
        "valeur_contenu": 10000000
    }
    
    Response:
    {
        "valid": true,
        "errors": {}
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = MaisonCalculRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            return Response({
                'valid': True,
                'errors': {}
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'valid': False,
                'errors': serializer.errors
            }, status=status.HTTP_200_OK)


class RecalculerDevisView(APIView):
    """
    Recalcule les totaux d'un devis (utile après modification manuelle).
    
    POST /api/mrh/devis/{devis_id}/recalculer/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, devis_id):
        from .models import Devis  # Import local
        
        try:
            devis = Devis.objects.get(iddevis=devis_id)
            
            service = MRHCalculService()
            totaux = service.mettre_a_jour_totaux_devis(
                id_devis=devis_id,
                id_produit=devis.produit_id,
                id_compagnie=devis.compagnie_id,
                inclure_accessoires=True
            )
            
            return Response({
                'message': 'Devis recalculé avec succès',
                'totaux': totaux
            }, status=status.HTTP_200_OK)
        
        except Devis.DoesNotExist:
            return Response(
                {'erreur': f'Devis {devis_id} non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'erreur': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


"""
Vue pour l'endpoint de résumé financier des devis MRH
======================================================
"""

class ResumeFinancierDevisView(APIView):
    """
    Endpoint pour obtenir le résumé financier complet d'un devis MRH.
    
    GET /api/mrh/devis/{devis_id}/resume-financier/
    
    Retourne :
    - Prime nette totale (après options)
    - Prime annuelle (avant options)
    - Accessoires
    - Taxe totale (garanties + accessoire)
    - Prime TTC
    - Liste des garanties acquises avec prime nette et taxe
    
    Permissions :
    - Utilisateur authentifié
    
    Exemples d'utilisation :
    
    curl http://localhost:8000/api/mrh/devis/456/resume-financier/
    
    Réponse :
    {
        "id_devis": 456,
        "numero_devis": "DEV-MRH-2024-00456",
        "prime_nette_totale": 153680.00,
        "prime_annuelle": 153680.00,
        "accessoire": 5000.00,
        "taxe_totale": 28594.60,
        "prime_ttc": 187274.60,
        "taxe_sous_garanties": 27869.60,
        "taxe_accessoire": 725.00,
        "accessoire_details": {...},
        "statistiques": {...},
        "sous_garanties_acquises": [...]
    }
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, devis_id):
        """
        Récupère le résumé financier complet du devis.
        
        Args:
            request: Requête HTTP
            devis_id: ID du devis
        
        Returns:
            Response avec le résumé financier complet
        """
        try:
            # Calculer le résumé financier
            resume = obtenir_resume_financier_devis(devis_id)
            
            # Sérialiser la réponse
            serializer = ResumeFinancierDevisSerializer(resume)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except ValueError as e:
            # Devis non trouvé
            return Response(
                {
                    'erreur': str(e),
                    'code': 'DEVIS_INTROUVABLE'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            # Erreur interne
            return Response(
                {
                    'erreur': f"Erreur lors du calcul du résumé financier : {str(e)}",
                    'code': 'ERREUR_INTERNE'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )