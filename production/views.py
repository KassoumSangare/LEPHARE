import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import cast

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F, Prefetch, Q
from django.http import FileResponse, Http404
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django_filters import rest_framework as filters
from knox.auth import TokenAuthentication
from rest_framework import generics, permissions, status, viewsets
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from autorisations.models import (
    DemandeAutorisation,
    JetonAutorisation,
    TypeOperation,
)
from autorisations.serializers import AnnulerAvecJetonSerializer
from autorisations.tasks import envoyer_notification_nouvelle_demande

# Import des modèles MRH
from configuration_api.models import (
    OffreAutomobileBoisee,
    Option,
    ParametresCalcul,
    Produit,
    SousGarantieForfait,
    SousGarantieMRH,
    UsageHabitation,
)
from configuration_api.serializers import (  # Serializers lecture
    OptionSerializer,
    ParametresCalculSerializer,
    SousGarantieForfaitSerializer,
    SousGarantieMRHSerializer,
    UsageHabitationSerializer,
)
from core.date_parser import parse_date_string
from core.services import ServiceError
from customer.models import Client

from .anti_doublons.importateur import importer_assures_anti_doublons
from .anti_doublons.rapport import ConfigurationImport
from .database import (
    archive_quote,
    cancel_car_input,
    consolider_devis_db,
    correction_devis,
    enregistrer_ayant_droit,
    execute_maj_manuelle_primes,
    get_assure_ia,
    get_certificat_transport,
    get_contract_car_list,
    get_contract_coverage,
    get_contract_info,
    get_contract_list_for_customer,
    get_contract_list_for_pc,
    get_contract_premium_remittance,
    get_encaissement_recherche,
    get_extended_quotation_info,
    get_garantie_souscrite,
    get_info_encaissement,
    get_info_reversement,
    get_info_vehicule,
    get_liste_assure_ia,
    get_quotation_info,
    get_taux_reduction_flotte,
    offre_mrh_compatible,
    policy_modification,
    premium_remittance_validation,
    quotation_completion,
    save_contract,
    save_insured_ia,
    save_plate_number,
    save_premium_collection,
    save_premium_collection_cancellation,
    save_premium_remittance,
    save_quotation,
    save_quotation_globaledebanque,
    save_quotation_ia,
    save_quotation_mrh,
    save_quotation_risques_divers,
    save_quotation_tousrisquesinfo,
    save_quotation_voyage,
    unarchive_quote,
)
from .exceltopostgresql import export_excel
from .import_assures import import_ia_insured, insert_new_assure
from sante.models import Adherent, Affilie
from .models import (
    AyantDroitIa,
    CertificatTransport,
    Cheque,
    ContractForPremiumCollection,
    Contrat,
    ContratDetail,
    ContratDetGarantie,
    DetailEncaissement,
    DetailQuittance,
    DetailReversement,
    Devis,
    DevisDetail,
    DevisDetGarantie,
    Encaissement,
    ImpositionPrime,
    LogRecord,
    Numero,
    PieceJointe,
    Quittance,
    ReversementCompagnie,
    TarifEcran,
)
from .serializers import (  # Serializers requêtes; Serializers réponses
    AssureIaInfoSerializer,
    AssureIaParDevisOuContratSerializer,
    AvenantAnlRenSerializer,
    AyantDroitIaSerializer,
    CertificatTransportSerializer,
    ChangementImmatriculationSerializer,
    ChequeOperationSerializer,
    ChequeSerializer,
    ConsolidationDevisClientSerializer,
    ContractForPremiumCollectionSerializer,
    ContratDetailSerializer,
    ContratDetGarantieSerializer,
    ContratSerializer,
    CorrectionDevisSerializer,
    CreationAyantDroitIaSerializer,
    DataInsertionSerializer,
    DemandeContratPourEncaissementSerializer,
    DetailEncaissementSerializer,
    DetailMaisonSerializer,
    DetailQuittanceSerializer,
    DetailReversementSerializer,
    DevisClientSerializer,
    DevisDetailGarantieSerializer,
    DevisDetailSerializer,
    DevisDetGarantieSerializer,
    DevisMRHCalculeResponseSerializer,
    DevisMRHCreateRequestSerializer,
    DevisMRHResponseSerializer,
    DevisSerializer,
    EncaissementGroupeQuittanceSerializer,
    EncaissementResponseSerializer,
    EncaissementSerializer,
    EnregistrementDevisAutoSerializer,
    EnregistrementDevisGlobaleDeBanqueSerializer,
    EnregistrementDevisIaSerializer,
    EnregistrementDevisMrhSerializer,
    EnregistrementDevisRisqquesDiversSerializer,
    EnregistrementDevisTRInfoSerializer,
    EnregistrementDevisVoyageSerializer,
    ExtendedQuotationInfoSerializer,
    FinalisationDevisFlotteSerializer,
    GarantieContratFlotteSerializer,
    GarantieSouscriteSerializer,
    ImportationAssureIaSerializer,
    ImportationTransportSerializer,
    ImpositionPrimeDevisRequestSerializer,
    ImpositionPrimeMaisonRequestSerializer,
    InfoVehiculeSerializer,
    LeveeImpositionRequestSerializer,
    LogRecordSerializer,
    MaisonAjouteeResponseSerializer,
    MaisonAjoutRequestSerializer,
    MaisonCalculeeSerializer,
    MaisonCalculRequestSerializer,
    MaisonModificationRequestSerializer,
    NumeroSerializer,
    OperationSurDevisDetailSerializer,
    OperationSurDevisSerializer,
    PieceJointeSerializer,
    PremiumCollectionInfoSerializer,
    PremiumRemittanceInfoSerializer,
    PrimeUpdateSerializer,
    QuittanceContratSerializer,
    QuittancePropositionSerializer,
    QuittanceSerializer,
    QuotationIaInsertionSerializer,
    QuotationInsertionSerializer,
    ResumeFinancierDevisSerializer,
    ReversementCompagnieSerializer,
    ReversementGroupePrimeInsertSerializer,
    ReversementGroupePrimeValidateSerializer,
    TarifEcranSerializer,
    TransformerSanteEnIASerializer,
    VehiculeContratSerializer,
)
from .services.mrh_calcul_service import MRHCalculService
from .services.resume_financier_devis import obtenir_resume_financier_devis
from .tasks import send_sms_enregistrement_contrat

logger = logging.getLogger(__name__)


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
    return JsonResponse(
        post_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


class ContractForPremiumCollectionView(generics.ListCreateAPIView):
    serializer_class = ContractForPremiumCollectionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        reference_client = self.request.query_params.get(
            "referenceclient", None
        )
        reference_contrat = self.request.query_params.get(
            "referencecontrat", None
        )
        if reference_client:
            reference_client = str(reference_client)
        if reference_contrat:
            reference_contrat = str(reference_contrat)
        (msg, item) = get_contract_list_for_pc(
            reference_client, reference_contrat
        )
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
        reference_client = self.request.query_params.get(
            "referenceclient", None
        )
        reference_contrat = self.request.query_params.get(
            "referencecontrat", None
        )
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


class PieceJointeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les pièces jointes
    """

    queryset = PieceJointe.objects.all()
    serializer_class = PieceJointeSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    parser_classes = [MultiPartParser, FormParser]

    def perform_destroy(self, instance):
        """Supprimer la pièce jointe et le fichier associé"""
        instance.delete()


class DevisViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = (
        Devis.objects.prefetch_related("piece_jointe")
        .annotate(offreboisee=OffreAutomobileBoisee(F("offre__IdOffre")))
        .all()
    )
    serializer_class = DevisSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=True, methods=["get"], url_path="garanties")
    def get_garanties(self, request, pk=None):
        """
        Retourne toutes les garanties d'un devis donné, sans duplication.
        """
        devis = cast(Devis, self.get_object())
        garanties = DevisDetGarantie.objects.filter(
            IdDevisDet__iddevis=devis
        ).distinct("IdGarantie_id")
        serializer = DevisDetailGarantieSerializer(garanties, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def attacher_piece_jointe(self, request, pk=None):
        """
        Attacher une pièce jointe à un devis

        Body (multipart/form-data):
        - fichier: Le fichier à joindre (PDF, JPG, PNG)
        """
        devis = self.get_object()

        if "fichier" not in request.FILES:
            return Response(
                {"erreur": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Créer la pièce jointe
        piece_serializer = PieceJointeSerializer(
            data={"fichier": request.FILES["fichier"]},
            context={"request": request},
        )

        if piece_serializer.is_valid():
            piece_jointe = piece_serializer.save()

            # Attacher au devis
            devis.piece_jointe = piece_jointe
            devis.save()

            # Retourner le devis mis à jour
            devis_serializer = DevisSerializer(
                devis, context={"request": request}
            )
            return Response(devis_serializer.data, status=status.HTTP_200_OK)

        return Response(
            piece_serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["get"])
    def telecharger_piece_jointe(self, request, pk=None):
        devis = cast(Devis, self.get_object())
        if not devis.piece_jointe or not devis.piece_jointe.fichier:
            raise Http404("Pas de pièce jointe")

        return FileResponse(
            open(devis.piece_jointe.fichier.path, "rb"),
            as_attachment=True,
            filename=devis.piece_jointe.fichier.name,
        )

    # @action(detail=True, methods=["get"], url_path="piece-jointe")
    @action(detail=True, methods=["get"])
    def obtenir_url_piece_jointe(self, request, pk=None):
        try:
            devis = cast(Devis, self.get_object())
            if not devis.piece_jointe or not devis.piece_jointe.fichier:
                raise Http404("Pas de pièce jointe pour ce devis")

            # Retourner uniquement l’URL sécurisée
            return Response(
                {
                    "id": devis.piece_jointe.pk,
                    "nom_fichier": devis.piece_jointe.fichier.name,
                    "url": devis.piece_jointe.fichier.url,
                }
            )
        except Devis.DoesNotExist:
            raise Http404("Devis introuvable")


class CertificatTransportView(generics.ListCreateAPIView):
    queryset = CertificatTransport.objects.all().order_by("-date_fin_periode")[
        :1000
    ]
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
        from django.db.models import Count

        id_client = self.request.query_params.get("idclient", None)
        nom_client = self.request.query_params.get("nomclient", None)
        id_produit = self.request.query_params.get("idproduit", None)
        devis_qs = Devis.objects.annotate(
            nombre_objets=Count("details")
        ).filter(confirme=False, archive=False, flotte=False, nombre_objets=1)
        try:
            if nom_client:
                clients = Client.objects.filter(
                    Q(Nom__istartswith=nom_client)
                    | Q(Prenoms__istartswith=nom_client)
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
                "details",
                queryset=DevisDetail.objects.filter(iddevis__in=devis_qs),
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
        serializer = ConsolidationDevisClientSerializer(
            data=request.data, many=True
        )
        if not serializer.is_valid():
            return Response(
                {"erreur": "Format de données invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extraction des IDs de devis
        devis_ids = [item["iddevis"] for item in serializer.validated_data]

        # Vérification du nombre minimum de devis. Il en faut au moins deux.
        if len(devis_ids) < 2:
            return Response(
                {
                    "erreur": (
                        "Au minimum 2 devis sont requis pour la "
                        "consolidation."
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
                {
                    "erreur": "Tous les devis doivent appartenir au même client."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vérification que tous les devis concernent le même produit
        produits = devis_list.values_list("produit", flat=True).distinct()
        if len(produits) > 1:
            return Response(
                {
                    "erreur": "Tous les devis doivent concerner le même produit."
                },
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
        intermediaires = devis_list.values_list(
            "intermediaire", flat=True
        ).distinct()
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
                {
                    "erreur": "Tous les devis doivent avoir la même date d'effet."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        dates_expiration = devis_list.values_list(
            "dateexpiration", flat=True
        ).distinct()
        if len(dates_expiration) > 1:
            return Response(
                {
                    "erreur": "Tous les devis doivent avoir la même date d'expiration."
                },
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


class ContratViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Contrat.objects.prefetch_related("piece_jointe").filter(
        Q(idcontratannulation=0)
    )
    serializer_class = ContratSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=True, methods=["get"], url_path="garanties")
    def get_garanties(self, request, pk=None):
        """
        Retourne toutes les garanties d'un contrat
        donné, sans duplication.
        """
        contrat = cast(Contrat, self.get_object())
        garanties = ContratDetGarantie.objects.filter(
            idcontratdetail__idcontrat=contrat
        ).distinct("idgarantie_id")
        serializer = ContratDetGarantieSerializer(garanties, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def attacher_piece_jointe(self, request, pk=None):
        """
        Attacher une pièce jointe à un contrat

        Body (multipart/form-data):
        - fichier: Le fichier à joindre (PDF, JPG, PNG)
        """
        contrat = self.get_object()

        if "fichier" not in request.FILES:
            return Response(
                {"error": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Créer la pièce jointe
        piece_serializer = PieceJointeSerializer(
            data={"fichier": request.FILES["fichier"]},
            context={"request": request},
        )

        if piece_serializer.is_valid():
            piece_jointe = piece_serializer.save()

            # Attacher au contrat
            contrat.piece_jointe = piece_jointe
            contrat.save()

            # Retourner le contrat mis à jour
            contrat_serializer = ContratSerializer(
                contrat, context={"request": request}
            )
            return Response(contrat_serializer.data, status=status.HTTP_200_OK)

        return Response(
            piece_serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["get"])
    def telecharger_piece_jointe(self, request, pk=None):
        contrat = cast(Contrat, self.get_object())
        if not contrat.piece_jointe or not contrat.piece_jointe.fichier:
            raise Http404("Pas de pièce jointe")

        return FileResponse(
            open(contrat.piece_jointe.fichier.path, "rb"),
            as_attachment=True,
            filename=contrat.piece_jointe.fichier.name,
        )

    @action(detail=True, methods=["get"])
    def obtenir_url_piece_jointe(self, request, pk=None):
        try:
            contrat = cast(Contrat, self.get_object())
            if not contrat.piece_jointe or not contrat.piece_jointe.fichier:
                raise Http404("Pas de pièce jointe pour ce devis")

            # Retourner uniquement l’URL sécurisée
            return Response(
                {
                    "id": contrat.piece_jointe.pk,
                    "nom_fichier": contrat.piece_jointe.fichier.name,
                    "url": contrat.piece_jointe.fichier.url,
                }
            )
        except Devis.DoesNotExist:
            raise Http404("Devis introuvable")


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


class AdherentsSantePourDevisIAView(APIView):
    """
    Retourne les adhérents actifs du contrat Santé MINENE lié au devis IA.
    Utilise le champ numero_police_connexe du devis IA pour retrouver le contrat Santé.
    Chaque adhérent est retourné avec ses affiliés actifs.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id_devis_ia):
        try:
            devis_ia = Devis.objects.get(pk=id_devis_ia)
        except Devis.DoesNotExist:
            return Response(
                {"Status": "Erreur", "message": "Devis IA introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        numeropolice_sante = devis_ia.numero_police_connexe
        if not numeropolice_sante:
            return Response(
                {"Status": "Erreur", "message": "Aucun numéro de police Santé connexe sur ce devis IA."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contrat_sante = Contrat.objects.filter(numeropolice=numeropolice_sante).first()
        if not contrat_sante:
            return Response(
                {"Status": "Erreur", "message": f"Aucun contrat Santé trouvé pour la police '{numeropolice_sante}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        iddevis_sante = contrat_sante.iddevis_id
        adherents = Adherent.objects.filter(devis=iddevis_sante, actif=True)

        result = []
        for adherent in adherents:
            affilies = list(
                Affilie.objects.filter(adherent=adherent, actif=True).values(
                    "idaffilie", "nom", "prenom", "lien", "date_naissance", "sexe"
                )
            )
            result.append({
                "idadherent": adherent.idadherent,
                "nom": adherent.nom,
                "prenom": adherent.prenom,
                "sexe": adherent.sexe,
                "date_naissance": adherent.datenaissanceadherent,
                "affilies": affilies,
            })

        return Response(
            {"Status": "Succès", "adherents": result, "numeropolice_sante": numeropolice_sante},
            status=status.HTTP_200_OK,
        )


class TransformerSanteEnIAView(APIView):
    """
    Transforme les adhérents du contrat Santé MINENE en assurés du devis IA MINENE,
    et les affiliés Santé MINENE en ayants-droits IA MINENE.

    Chaque adhérent actif → Client (assuré IA) lié au devis IA via sp_creation_assure_ia.
    Chaque affilié actif → ayant-droit via sp_saisie_ayant_droit_ia.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TransformerSanteEnIASerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        id_devis_ia = serializer.validated_data["id_devis_ia"]
        capital_deces = serializer.validated_data["capital_deces"]
        capital_ipp = serializer.validated_data["capital_ipp"]
        frais_traitement = serializer.validated_data["frais_traitement"]
        affilies_qualites = serializer.validated_data.get("affilies_qualites", [])
        qualites_map = {item["idaffilie"]: item["id_qualite"] for item in affilies_qualites}

        try:
            devis_ia = Devis.objects.get(pk=id_devis_ia)
        except Devis.DoesNotExist:
            return Response(
                {"Status": "Erreur", "message": "Devis IA introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        numeropolice_sante = devis_ia.numero_police_connexe
        if not numeropolice_sante:
            return Response(
                {"Status": "Erreur", "message": "Aucun numéro de police Santé connexe sur ce devis IA."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contrat_sante = Contrat.objects.filter(numeropolice=numeropolice_sante).first()
        if not contrat_sante:
            return Response(
                {"Status": "Erreur", "message": f"Aucun contrat Santé trouvé pour la police '{numeropolice_sante}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        iddevis_sante = contrat_sante.iddevis_id
        adherents = Adherent.objects.filter(devis=iddevis_sante, actif=True)

        assures_crees = []
        ayants_droits_crees = []
        erreurs = []

        for adherent in adherents:
            # 1. Créer un Client (assuré IA) à partir de l'adhérent Santé
            donnee_assure = {
                "Nom": adherent.nom,
                "Prenoms": adherent.prenom or adherent.nom,
                "Sexe": adherent.sexe,
                "DateNaissance": adherent.datenaissanceadherent,  # date object, accepté par Client.objects.create()
                "LieuNaissance": "",
                "NumeroCNI": adherent.numerocni or "",
                "Email": adherent.email or "",
                "NumeroTelephone": adherent.mobile1 or "",
                "NumeroMobile": adherent.mobile1 or "",
                "AdressePostale": adherent.adresseadherent or "",
                "AdresseGeographique": adherent.adresseadherent or "",
                "Fonction": "",
            }
            try:
                client = insert_new_assure(donnee_assure)
            except Exception as e:
                erreurs.append({"type": "adherent", "idadherent": adherent.idadherent, "message": str(e)})
                continue

            # 2. Lier ce client au devis IA (créer l'enregistrement assuré IA)
            date_naissance_str = (
                adherent.datenaissanceadherent.strftime("%d-%m-%Y")
                if adherent.datenaissanceadherent
                else "01-01-1990"
            )
            insured_data = {
                "IdAssure": client.IdClient,
                "IdOffre": devis_ia.offre_id,
                "DateEffet": devis_ia.dateeffet.strftime("%d-%m-%Y"),
                "DateExpiration": devis_ia.dateexpiration.strftime("%d-%m-%Y"),
                "DateEmission": devis_ia.dateemission.strftime("%d-%m-%Y"),
                "CapitalDeces": str(capital_deces),
                "CapitalIpp": str(capital_ipp),
                "FraisTraitement": str(frais_traitement),
                "TauxReduction": "0",
                "CodeActivite": "01",
                "DateNaissance": date_naissance_str,
                "IdDevis": id_devis_ia,
                "IdDevisDetail": 0,
            }
            (err_ia, result_ia) = save_insured_ia(insured_data)
            if err_ia or not result_ia or result_ia[0].ObjectId <= 0:
                msg = result_ia[0].OutputMessage if result_ia else "Erreur inconnue."
                erreurs.append({"type": "assure", "idadherent": adherent.idadherent, "message": msg})
            else:
                assures_crees.append({"idadherent": adherent.idadherent, "id_assure": client.IdClient})

            id_assure_ia = client.IdClient

            # 3. Créer les ayants-droits à partir des affiliés de cet adhérent
            affilies = Affilie.objects.filter(adherent=adherent, actif=True)
            for affilie in affilies:
                id_qualite = qualites_map.get(affilie.idaffilie)
                if not id_qualite:
                    erreurs.append({
                        "type": "ayant_droit",
                        "idaffilie": affilie.idaffilie,
                        "message": "Qualité non fournie pour cet affilié.",
                    })
                    continue

                ayant_droit_data = {
                    "IdAssure": id_assure_ia,
                    "IdQualiteAyantDroit": id_qualite,
                    "NomAyantDroit": affilie.nom,
                    "PrenomsAyantDroit": affilie.prenom or affilie.nom,
                    "Part": 0,
                }
                result_ad = enregistrer_ayant_droit(ayant_droit_data)
                if result_ad and result_ad[0].ObjectId > 0:
                    ayants_droits_crees.append({
                        "idaffilie": affilie.idaffilie,
                        "id_ayant_droit": result_ad[0].ObjectId,
                    })
                else:
                    msg = result_ad[0].OutputMessage if result_ad else "Erreur inconnue."
                    erreurs.append({"type": "ayant_droit", "idaffilie": affilie.idaffilie, "message": msg})

        return Response(
            {
                "Status": "Succès",
                "assures_crees": len(assures_crees),
                "ayants_droits_crees": len(ayants_droits_crees),
                "erreurs": len(erreurs),
                "details_erreurs": erreurs,
            },
            status=status.HTTP_200_OK,
        )


def import_assures_view(request):
    if request.method == "POST":
        fichier = request.FILES["FichierExcel"]

        # Sauvegarder temporairement
        temp_path = f"/tmp/{fichier.name}"
        with open(temp_path, "wb+") as f:
            for chunk in fichier.chunks():
                f.write(chunk)

        # Configuration
        config = ConfigurationImport()

        # Import avec anti-doublons
        erreur, id_devis, rapport = importer_assures_anti_doublons(
            filepath=temp_path,
            user_id=request.user.id,
            request_post_data=request.POST.dict(),
            config=config,
        )

        # Nettoyer
        import os

        os.remove(temp_path)

        # Messages
        if not erreur:
            messages.success(
                request,
                f"✓ Import réussi! {len(rapport.assures_nouveaux)} créés, "
                f"{len(rapport.assures_ignores)} ignorés",
            )
        else:
            messages.error(request, f"✗ Erreur: {rapport.details_erreur}")

        return redirect("import_resultat")

    return render(request, "import_form.html")


class ImportationAssureIaViewSet(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        message = {}
        id_devis = 0
        serializer_class = ImportationAssureIaSerializer(data=request.data)
        if (
            "FichierExcel" not in request.FILES
            or not serializer_class.is_valid()
        ):
            if "IdDevis" in request.POST:
                if request.POST["IdDevis"]:
                    id_devis = int(request.POST["IdDevis"])
            message["IdDevis"] = id_devis
            message["messages"] = [
                "Paramètres non conformes",
            ]
            return Response(data=message, status=status.HTTP_400_BAD_REQUEST)
        else:
            (error_ocurred, id_devis) = import_ia_insured(
                request.FILES["FichierExcel"], request.user.id, request.POST
            )
            message["IdDevis"] = id_devis
            if not error_ocurred:
                message["messages"] = [
                    "Importation des assurés réalisée avec succès.",
                ]
                return Response(data=message, status=status.HTTP_202_ACCEPTED)
            else:
                message["messages"] = [
                    "Echec de l'importation des assurés.",
                ]
                return Response(
                    data=message, status=status.HTTP_400_BAD_REQUEST
                )


class LogRecordView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request):
        msg = request.query_params.get("msg", "")
        level_name = request.query_params.get("levelname", "")
        serializer = LogRecordSerializer(
            LogRecord(msg=msg, level_name=level_name)
        )
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
        if self.action in ["list", "retrieve", "annuler"]:
            return (
                Encaissement.objects.select_related("modepaiement", "banque")
                .prefetch_related("details")
                .filter(Q(piece_annulee=False))
                .order_by("-dateencaissement")
            )

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

    @action(detail=True, methods=["post"])
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
            return Response(
                {"erreur": "Cet encaissement est déjà annulé"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validation avec le serializer d'autorisation
        serializer = AnnulerAvecJetonSerializer(
            data=request.data,
            context={"request": request, "objet": encaissement},
        )
        serializer.is_valid(raise_exception=True)

        # Récupérer le jeton validé
        jeton_obj = cast(
            JetonAutorisation, serializer.validated_data["jeton_obj"]
        )

        # Transaction atomique pour garantir la cohérence
        try:
            with transaction.atomic():
                # Utiliser le jeton
                jeton_obj.utiliser(
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )

                # Annuler l'encaissement
                cancellation_data = {
                    "id_encaissement": encaissement.idencaissement,
                    "date_annulation": timezone.now().date(),
                    "motif_annulation": jeton_obj.demande.motif,
                }
                (err, qryset) = save_premium_collection_cancellation(
                    request.user.id, cancellation_data
                )
                data_insertion_serializer = DataInsertionSerializer(
                    qryset,
                    many=True,
                )
                st = status.HTTP_201_CREATED
                if err:
                    transaction.set_rollback(True)
                    st = status.HTTP_400_BAD_REQUEST
                return JsonResponse(
                    data_insertion_serializer.data, status=st, safe=False
                )
        except Exception as error:
            return JsonResponse(
                {
                    "ObjectId": encaissement.idencaissement,
                    "OutputMessage": str(error).split("\n")[0],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def get_client_ip(request):
        """Récupère l'adresse IP du client"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    @action(detail=True, methods=["post"])
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
            return Response(
                {"erreur": "Cet encaissement est déjà annulé"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        motif = request.data.get("motif")
        if not motif or len(motif) < 10:
            return Response(
                {"erreur": "Le motif doit contenir au moins 10 caractères"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                "reference": encaissement.numeropiece,
                "montant": str(encaissement.montantencaissement),
            },
        )

        envoyer_notification_nouvelle_demande.delay(demande.id)

        return Response(
            {
                "message": "Demande d'annulation créée avec succès",
                "demande_id": demande.id,
            },
            status=status.HTTP_201_CREATED,
        )


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
                    {
                        "erreur": "La date de fin doit être postérieure à la date de début."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        contracts = (
            Contrat.objects.filter(
                dateemission__range=(start_date, end_date),
            )
            .filter(
                Q(idcontratannulation__isnull=True) | Q(idcontratannulation=0)
            )
            .select_related("idclient", "iddevis")
            .annotate(
                client=F("idclient__Nom"),
                numerodevis=F("iddevis__numerodevis"),
            )
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
        queryset = (
            ReversementCompagnie.objects.filter(Q(valide=False))
            .select_related("compagnie", "banque")
            .prefetch_related("details")
            .order_by("-date_reversement")[:1000]
        )
        serializer = ReversementCompagnieSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = (
            ReversementCompagnie.objects.filter(Q(valide=False))
            .select_related("compagnie", "banque")
            .prefetch_related("details")
            .order_by("-date_reversement")
        )
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
            ReversementCompagnie.objects.filter(Q(valide=True))
            .select_related("compagnie", "mode_reversement", "banque")
            .prefetch_related("details")
            .filter(Q(piece_annulee=False))
            .order_by("-date_reversement")[:1000]
        )
        serializer = ReversementCompagnieSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = (
            ReversementCompagnie.objects.filter(Q(valide=True))
            .select_related("compagnie", "mode_reversement", "banque")
            .prefetch_related("details")
            .filter(Q(piece_annulee=False))
        )
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
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
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

        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
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

        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )

    return JsonResponse(
        input_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


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
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
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
        data_insertion_serializer = QuotationIaInsertionSerializer(
            queryset, many=True
        )
        st = status.HTTP_201_CREATED
        if error:
            st = status.HTTP_400_BAD_REQUEST

        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )

    return JsonResponse(
        enregistrementdevis_ia_serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
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
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
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
    enregistrementdevis_voyage_serializer = (
        EnregistrementDevisVoyageSerializer(
            data=enregistrementdevis_voyage_data
        )
    )
    if enregistrementdevis_voyage_serializer.is_valid():
        (err, queryset) = save_quotation_voyage(
            enregistrementdevis_voyage_data
        )
        data_insertion_serializer = DataInsertionSerializer(
            queryset, many=True
        )
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
    return JsonResponse(
        enregistrementdevis_voyage_serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
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
        data_insertion_serializer = DataInsertionSerializer(
            queryset, many=True
        )
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
    return JsonResponse(
        enregistrementdevis_mrh_serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
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
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
    return JsonResponse(
        enregistrementdevis_tri_serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


###########################################################################
# Create new quotation - RC
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation_risques_divers(request):
    enregistrementdevis_risques_divers_data = JSONParser().parse(request)
    print("JSON de la requête:", enregistrementdevis_risques_divers_data)
    enregistrementdevis_risques_divers_serializer = (
        EnregistrementDevisRisqquesDiversSerializer(
            data=enregistrementdevis_risques_divers_data
        )
    )
    if enregistrementdevis_risques_divers_serializer.is_valid():
        (err, queryset) = save_quotation_risques_divers(
            request.user.id,
            enregistrementdevis_risques_divers_serializer.validated_data,
        )
        data_insertion_serializer = DataInsertionSerializer(
            queryset,
            many=True,
        )
        st = status.HTTP_201_CREATED
        if err:
            st = status.HTTP_400_BAD_REQUEST
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
    return JsonResponse(
        enregistrementdevis_risques_divers_serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


###########################################################################
# Bank Risk Insurance
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_quotation_globaledebanque(request):
    enregistrementdevis_gdb_data = JSONParser().parse(request)
    # #print("JSON de la requête:", enregistrementdevis_gdb_data)
    enregistrementdevis_gdb_serializer = (
        EnregistrementDevisGlobaleDeBanqueSerializer(
            data=enregistrementdevis_gdb_data
        )
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
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
    return JsonResponse(
        enregistrementdevis_gdb_serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
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
            data_insertion_serializer.data,
            status=status.HTTP_201_CREATED,
            safe=False,
        )
    return JsonResponse(
        creationayantdroit_serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
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
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )

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
            serializer = AssureIaParDevisOuContratSerializer(
                assures, many=True
            )
            # print(serializer)
            return JsonResponse(
                serializer.data, status=status.HTTP_200_OK, safe=False
            )
        else:
            return JsonResponse(
                {"Status": "Echec", "Data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AssureIaParContratView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcontrat):
        (msg, assures) = get_liste_assure_ia(id=idcontrat, statut="CNT")
        if not msg:
            serializer = AssureIaParDevisOuContratSerializer(
                assures, many=True
            )
            # print(serializer.data)
            return JsonResponse(
                serializer.data, status=status.HTTP_200_OK, safe=False
            )
        else:
            return JsonResponse(
                {"Status": "Echec", "Data": msg},
                status=status.HTTP_400_BAD_REQUEST,
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
            return JsonResponse(
                serializer.data, status=status.HTTP_200_OK, safe=False
            )
        else:
            return JsonResponse(
                {"Status": "Echec", "Data": msg},
                status=status.HTTP_400_BAD_REQUEST,
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
        return JsonResponse(
            serializer.data, status=status.HTTP_200_OK, safe=False
        )


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
            serializer = ContractForPremiumCollectionSerializer(
                item, many=True
            )
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
        (msg, item) = get_info_encaissement(
            detailencaissement=iddetailencaissement
        )
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
            details = DetailEncaissement.objects.filter(
                encaissement=encaissement
            )
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


class ImportationFichierGUCEViewSet(viewsets.ViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request):
        messages = []
        serializer_class = ImportationTransportSerializer(data=request.data)
        if (
            "fichier_excel" not in request.FILES
            or not serializer_class.is_valid()
        ):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            (error_occured, messages) = export_excel(
                request.FILES["fichier_excel"],
                request.user.id,
                request.POST["debut_periode"],
                request.POST["fin_periode"],
            )
            data_insertion_serializer = DataInsertionSerializer(
                messages, many=True
            )
            if not error_occured:
                return Response(
                    data=data_insertion_serializer.data,
                    status=status.HTTP_202_ACCEPTED,
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
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        nom_client = request.query_params.get("nom_client", "")
        numero_police = request.query_params.get("numero_police", "")

        # Calcul de l'offset
        limit = page_size
        offset = (page - 1) * page_size

        (msg, devis_list, total_count) = get_extended_quotation_info(
            0,
            numero_police,
            nom_client,
            None,
            None,
            idproduit,
            limit=limit,
            offset=offset,
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
                        "total_pages": (total_count + limit - 1) // limit,
                    },
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
                    date_fin = datetime.strptime(
                        str(parameters[4]), "%Y-%m-%d"
                    ).date()
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
            {
                "Status": statut_msg,
                "TauxReduction": str(taux_reduction_flotte),
            },
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
                {"Status": "Succès", "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"Status": "Echec", "Data": msg},
                status=status.HTTP_400_BAD_REQUEST,
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
    enregistrementencaissement_serializer = (
        EncaissementGroupeQuittanceSerializer(
            data=enregistrementencaissement_data
        )
    )
    enregistrementencaissement_serializer.is_valid(raise_exception=True)
    try:

        result_data = save_premium_collection(
            request.user, enregistrementencaissement_data
        )
        # 3. Réponse de succès utilisant notre structure définie
        output_serializer = EncaissementResponseSerializer(result_data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    except ServiceError as e:
        # Erreur renvoyée par la procédure SQL (id=0)
        return Response(
            {"erreur": str(e.detail)}, status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        # Erreur système inattendue
        return Response(
            {
                "erreur": "Une erreur technique est survenue.",
                "details": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
            data_insertion_serializer.data,
            status=status.HTTP_201_CREATED,
            safe=False,
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
        error, queryset = premium_remittance_validation(
            request.user.id, validated_data
        )
        data_insertion_serializer = DataInsertionSerializer(
            queryset,
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
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
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
        return JsonResponse(
            data_insertion_serializer.data, status=st, safe=False
        )
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
            serializer = ContractForPremiumCollectionSerializer(
                item, many=True
            )
            # print(serializer.data)
            return JsonResponse(
                serializer.data, status=status.HTTP_200_OK, safe=False
            )
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
        (msg, item) = get_contract_list_for_pc(
            referenceclient, referencecontrat
        )
        if not msg:
            serializer = ContractForPremiumCollectionSerializer(
                item, many=True
            )
            return JsonResponse(
                serializer.data, status=status.HTTP_200_OK, safe=False
            )
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
                    {
                        "message": "Error executing stored procedure.",
                        "details": str(e),
                    },
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

    queryset = UsageHabitation.objects.filter(actif=True).order_by("libelle")
    serializer_class = UsageHabitationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "code"

    @action(detail=True, methods=["get"])
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
                {"erreur": f"Paramètres de calcul non trouvés pour {code}"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["get"])
    def garanties(self, request, code=None):
        """
        Retourne les sous-garanties (obligatoires et optionnelles) pour un usage.

        GET /api/mrh/usages/{code}/garanties/
        """
        usage = cast(UsageHabitation, self.get_object())

        # Garanties obligatoires
        sous_garanties_oblig = (
            usage.sous_garanties_liees.filter(obligatoire=True, actif=True)
            .select_related("sous_garantie")
            .order_by("ordre_affichage")
        )

        # Garanties optionnelles
        sous_garanties_opt = (
            usage.sous_garanties_liees.filter(obligatoire=False, actif=True)
            .select_related("sous_garantie")
            .order_by("ordre_affichage")
        )

        return Response(
            {
                "obligatoires": [
                    {
                        "code": gu.sous_garantie.code,
                        "libelle": gu.sous_garantie.libelle,
                        "taux_repartition": gu.taux_repartition,
                    }
                    for gu in sous_garanties_oblig
                ],
                "optionnelles": [
                    {
                        "code": gu.sous_garantie.code,
                        "libelle": gu.sous_garantie.libelle,
                    }
                    for gu in sous_garanties_opt
                ],
            }
        )

    @action(detail=True, methods=["get"])
    def offres(self, request, code=None):
        """
        Retourne les offres pour un usage.

        GET /api/mrh/usages/{code}/offres/
        """
        usage = cast(UsageHabitation, self.get_object())

        offre_mrh_liee = usage.offre
        return Response(
            {
                "id_offre": offre_mrh_liee.IdOffre if offre_mrh_liee else "",
                "libelle_offre": (
                    offre_mrh_liee.LibelleOffre if offre_mrh_liee else ""
                ),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def options(self, request, code=None):
        """
        Retourne les options applicables à un usage.

        GET /api/mrh/usages/{code}/options/
        """
        usage = self.get_object()

        options = (
            Option.objects.filter(
                usages_applicables__usage=usage,
                usages_applicables__actif=True,
                actif=True,
            )
            .distinct()
            .order_by("type_option", "libelle")
        )

        serializer = OptionSerializer(options, many=True)
        return Response(serializer.data)


class SousGarantieMRHViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour lister les sous-garanties MRH.

    GET /api/mrh/sous-garanties/
    GET /api/mrh/sous-garanties/{code}/
    """

    queryset = SousGarantieMRH.objects.filter(actif=True).order_by(
        "type", "libelle"
    )
    serializer_class = SousGarantieMRHSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "code"


class SousGarantieForfaitViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour lister les garanties optionnelles à forfait.

    GET /api/mrh/sous-garanties-forfait/
    """

    queryset = SousGarantieForfait.objects.filter(actif=True).select_related(
        "sous_garantie"
    )
    serializer_class = SousGarantieForfaitSerializer
    permission_classes = [IsAuthenticated]


class OptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour lister les options disponibles.

    GET /api/mrh/options/
    GET /api/mrh/options/{code}/
    """

    queryset = Option.objects.filter(actif=True).order_by(
        "type_option", "libelle"
    )
    serializer_class = OptionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "code"


# ============================================================================
# MISE A JOUR DU DEVIS
# ============================================================================
class MiseAJourDevis(APIView):
    @action(detail=True, methods=["post"])
    def garanties(self, request, pk=None):
        """
        Met à jour un devis avec les informations.

        GET /api/mrh/devis//garanties/
        """
        usage = cast(UsageHabitation, self.get_object())

        # Garanties obligatoires
        sous_garanties_oblig = (
            usage.sous_garanties_liees.filter(obligatoire=True, actif=True)
            .select_related("sous_garantie")
            .order_by("ordre_affichage")
        )

        # Garanties optionnelles
        sous_garanties_opt = (
            usage.sous_garanties_liees.filter(obligatoire=False, actif=True)
            .select_related("sous_garantie")
            .order_by("ordre_affichage")
        )

        return Response(
            {
                "obligatoires": [
                    {
                        "code": gu.sous_garantie.code,
                        "libelle": gu.sous_garantie.libelle,
                        "taux_repartition": gu.taux_repartition,
                    }
                    for gu in sous_garanties_oblig
                ],
                "optionnelles": [
                    {
                        "code": gu.sous_garantie.code,
                        "libelle": gu.sous_garantie.libelle,
                    }
                    for gu in sous_garanties_opt
                ],
            }
        )


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
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        service = MRHCalculService()

        try:
            # Calculer la prime
            resultat = service.calculer_maison(
                code_usage=data["code_usage"],
                valeur_batiment=data.get("valeur_batiment"),
                valeur_contenu=data.get("valeur_contenu"),
                loyer_mensuel=data.get("loyer_mensuel"),
                capital_rvt=data.get("capital_rvt"),
                options=[
                    opt["code_option"] for opt in data.get("options", [])
                ],
                sous_garanties_optionnelles=[
                    gar["code_sous_garantie"]
                    for gar in data.get("sous_garanties_optionnelles", [])
                ],
                adresse=data.get("adresse"),
                description=data.get("description"),
            )

            # Sérialiser la réponse
            response_serializer = MaisonCalculeeSerializer(resultat)
            return Response(
                response_serializer.data, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
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
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        service = MRHCalculService()

        try:
            # Créer le devis
            id_devis = service.creer_devis(
                idintermediaire=data["idintermediaire"],
                idcompagnie=data["idcompagnie"],
                idproduit=data["idproduit"],
                idtarif=data["idtarif"],
                idoffre=data["idoffre"],
                idclient=data["idclient"],
                dateeffet=data["dateeffet"],
                **{
                    k: v
                    for k, v in data.items()
                    if k
                    not in [
                        "idintermediaire",
                        "idcompagnie",
                        "idproduit",
                        "idtarif",
                        "idoffre",
                        "idclient",
                        "dateeffet",
                    ]
                },
            )

            # Retourner la réponse
            from .models import Devis  # Import local

            devis = Devis.objects.get(iddevis=id_devis)

            response_data = {
                "devis_id": id_devis,
                "numero_devis": devis.numerodevis or "",
                "statut": "success",
                "message": "Devis créé avec succès",
                "date_creation": devis.dateemission,
            }

            response_serializer = DevisMRHResponseSerializer(response_data)
            return Response(
                response_serializer.data, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
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

                return Response(
                    {"message": "Devis enregistré avec succès"},
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            return Response(
                {"erreur": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

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
                "devis_id": devis.iddevis,
                "numero_devis": devis.numerodevis,
                "statut": "success",
                "message": "Devis récupéré avec succès",
                "prime_nette_totale": devis.primenette,
                "taxe_totale": devis.taxe,
                "accessoires": devis.accessoire,
                "prime_ttc_totale": devis.primettc,
                "maisons": [
                    {
                        "maison_id": str(m.iddevisdetail),
                        "code_usage": (
                            m.observation[:30] if m.observation else ""
                        ),  # Approximatif
                        "libelle_usage": (
                            m.observation[:30] if m.observation else ""
                        ),
                        "parametres": {
                            "valeur_batiment": m.valeurneuve,
                            "valeur_contenu": m.valeurvenale,
                        },
                        "prime_nette_totale": m.primenette,
                        "prime_annuelle_totale": m.primeannuelle,
                        "taxe_totale": m.taxeenregistrement,
                        "prime_ttc_totale": m.primenette
                        + m.taxeenregistrement,
                        "sous_garanties": [],  # Peut être enrichi si besoin
                        "options_appliquees": [],
                        "adresse": (
                            m.observation[33:]
                            if len(m.observation or "") > 33
                            else ""
                        ),
                    }
                    for m in maisons
                ],
                "nombre_maisons": maisons.count(),
                "date_calcul": devis.dateemission,
            }

            serializer = DevisMRHCalculeResponseSerializer(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Devis.DoesNotExist:
            return Response(
                {"error": f"Devis {pk} non trouvé"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def list(self, request):
        """
        Liste les devis (avec filtres optionnels).

        GET /api/mrh/devis/?client={id}&statut={statut}
        """
        from .models import Devis  # Import local

        queryset = Devis.objects.all().order_by("-dateemission")

        # Filtres optionnels
        client_id = request.query_params.get("client", None)
        if client_id:
            queryset = queryset.filter(client_id=client_id)

        statut = request.query_params.get("statut", None)
        if statut:
            queryset = queryset.filter(statut=statut)

        # Pagination simple
        page_size = int(request.query_params.get("page_size", 20))
        page = int(request.query_params.get("page", 1))
        start = (page - 1) * page_size
        end = start + page_size

        devis_list = queryset[start:end]

        data = [
            {
                "devis_id": d.iddevis,
                "numero_devis": d.numerodevis,
                "client": d.client_id,
                "date_effet": d.dateeffet,
                "prime_ttc": d.primettc,
                "statut": d.statut,
            }
            for d in devis_list
        ]

        return Response(
            {
                "count": queryset.count(),
                "page": page,
                "page_size": page_size,
                "results": data,
            },
            status=status.HTTP_200_OK,
        )

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
                    {"error": "Impossible de supprimer un devis confirmé"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            devis.delete()

            return Response(
                {"message": f"Devis {pk} supprimé avec succès"},
                status=status.HTTP_204_NO_CONTENT,
            )

        except Devis.DoesNotExist:
            return Response(
                {"error": f"Devis {pk} non trouvé"},
                status=status.HTTP_404_NOT_FOUND,
            )


# ============================================================================
# SECTION 4 : ENDPOINTS DE GESTION DE MAISONS
# ============================================================================


class MaisonViewSet(viewsets.ViewSet):
    """
    ViewSet pour la gestion des maisons dans un devis.

    POST /api/mrh/devis/{devis_id}/maisons/ - Ajouter une maison
    DELETE /api/mrh/devis/{devis_id}/maisons/{maison_id}/ - Supprimer une maison
    PUT /api/mrh/devis/{devis_id}/maisons/{maison_id}/ - Modifier une maison
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
                {"erreur": f"Devis {devis_id} non trouvé"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Valider les données
        serializer = MaisonAjoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data["maison"]
        service = MRHCalculService()

        if not offre_mrh_compatible(data["id_offre"], data["code_usage"]):
            return Response(
                {"erreur": "Offre incompatible avec l'usage"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Calculer et enregistrer la maison
            resultat = service.calculer_et_enregistrer_maison(
                id_devis=devis_id,
                id_produit=devis.produit_id,
                id_compagnie=devis.compagnie_id,
                id_tarif=data.get("id_tarif"),
                id_offre=data.get("id_offre"),
                code_usage=data["code_usage"],
                valeur_batiment=data.get("valeur_batiment"),
                valeur_contenu=data.get("valeur_contenu"),
                loyer_mensuel=data.get("loyer_mensuel"),
                capital_rvt=data.get("capital_rvt"),
                options=[
                    opt["code_option"] for opt in data.get("options", [])
                ],
                sous_garanties_optionnelles=[
                    gar["code_sous_garantie"]
                    for gar in data.get("sous_garanties_optionnelles", [])
                ],
                adresse=data.get("adresse"),
                description=data.get("description"),
            )

            # Construire la réponse
            response_data = {
                "devis_id": devis_id,
                "maison_id": resultat["id_maison"],
                "statut": "success",
                "message": "Maison ajoutée avec succès",
                "calcul": resultat["calcul"],
            }

            response_serializer = MaisonAjouteeResponseSerializer(
                response_data
            )
            return Response(
                response_serializer.data, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, devis_id=None, pk=None):
        """
        Modifier une maison existante dans un devis MRH.

        PUT /api/mrh/devis/{devis_id}/maisons/{maison_id}/

        Permet de modifier les caractéristiques d'une maison :
        - Valeurs (bâtiment, contenu, loyer, RVT)
        - Options (gardien, zone industrielle, etc.)
        - Garanties optionnelles
        - Adresse

        Règles :
        - Si prime maison imposée : erreur (sauf force_recalcul=True)
        - Si prime devis imposée : erreur (sauf force_recalcul=True)
        - Si force_recalcul=True : lève l'imposition automatiquement

        Request body :
        {
            "code_usage": "proprietaire_occupant_total",  // optionnel
            "valeur_batiment": 60000000,  // optionnel
            "valeur_contenu": 12000000,  // optionnel
            "options": ["presence_gardien"],  // optionnel
            "sous_garanties_optionnelles": ["RC_MEMBRE"],  // optionnel
            "force_recalcul": false  // optionnel, défaut false
        }

        Response 200 (succès) :
        {
            "success": true,
            "id_maison": 456,
            "message": "Maison modifiée avec succès",
            "calcul": { ... },
            "totaux_devis": { ... },
            "imposition_levee": false
        }

        Response 400 (prime imposée) :
        {
            "success": false,
            "erreur": "PRIME_MAISON_IMPOSEE",
            "message": "La prime de cette maison est imposée à 150 000,00 FCFA...",
            "prime_imposee": true,
            "montant_impose": 150000.00
        }
        """

        # Validation des données
        serializer = MaisonModificationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que la maison appartient au devis
        maison = get_object_or_404(DevisDetail, iddevisdetail=pk)
        if maison.iddevis_id != int(devis_id):
            return Response(
                {
                    "erreur": "MAISON_NOT_IN_DEVIS",
                    "message": f"La maison {pk} n'appartient pas au devis {devis_id}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Appeler le service métier
        service = MRHCalculService()
        try:
            resultat = service.modifier_maison(
                id_maison=pk, **serializer.validated_data
            )

            # Si échec (prime imposée)
            if not resultat.get("success", False):
                return Response(resultat, status=status.HTTP_400_BAD_REQUEST)

            # Succès
            return Response(resultat, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"erreur": "VALIDATION_ERROR", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {
                    "erreur": "INTERNAL_ERROR",
                    "message": f"Erreur lors de la modification : {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                iddevisdetail=pk, iddevis_id=devis_id
            )

            # Supprimer la maison (les garanties seront supprimées en cascade)
            maison.delete()

            # Mettre à jour les totaux du devis
            service = MRHCalculService()
            totaux = service.mettre_a_jour_totaux_devis(
                id_devis=devis_id,
                id_produit=devis.produit_id,
                id_compagnie=devis.compagnie_id,
                inclure_accessoires=True,
            )

            return Response(
                {
                    "message": f"Maison {pk} supprimée avec succès",
                    "totaux_devis": totaux,
                },
                status=status.HTTP_200_OK,
            )

        except Devis.DoesNotExist:
            return Response(
                {"error": f"Devis {devis_id} non trouvé"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except DevisDetail.DoesNotExist:
            return Response(
                {"error": f"Maison {pk} non trouvée dans le devis {devis_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            return Response(
                {"valid": True, "errors": {}}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"valid": False, "errors": serializer.errors},
                status=status.HTTP_200_OK,
            )


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
                inclure_accessoires=True,
            )

            return Response(
                {"message": "Devis recalculé avec succès", "totaux": totaux},
                status=status.HTTP_200_OK,
            )

        except Devis.DoesNotExist:
            return Response(
                {"erreur": f"Devis {devis_id} non trouvé"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"erreur": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                {"erreur": str(e), "code": "DEVIS_INTROUVABLE"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            # Erreur interne
            return Response(
                {
                    "erreur": f"Erreur lors du calcul du résumé financier : {str(e)}",
                    "code": "ERREUR_INTERNE",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChequeFilter(filters.FilterSet):
    # Filtre pour les chèques non épuisés (solde > 0)
    non_epuise = filters.BooleanFilter(method="filter_non_epuise")
    # Filtre par plage de dates
    date_min = filters.DateFilter(field_name="date_saisie", lookup_expr="gte")
    date_max = filters.DateFilter(field_name="date_saisie", lookup_expr="lte")

    class Meta:
        model = Cheque
        fields = [
            "banque",
            "numero_cheque",
            "non_epuise",
            "date_min",
            "date_max",
        ]

    def filter_non_epuise(self, queryset, name, value):
        if value:  # true → non épuisés
            return queryset.filter(solde_disponible__gt=0)
        else:  # false → épuisés
            return queryset.filter(solde_disponible=0)


class CheckChequeStatusView(APIView):
    def get(self, request):
        numero = request.query_params.get("numero_cheque")
        banque_id = request.query_params.get("banque")

        cheque = Cheque.objects.filter(
            numero_cheque=numero, banque_id=banque_id
        ).first()

        if cheque:
            return Response(
                {
                    "existe": True,
                    "montant_initial": cheque.montant_initial,
                    "solde_disponible": cheque.solde_disponible,
                }
            )
        return Response({"existe": False})


class ChequeListView(generics.ListAPIView):
    queryset = Cheque.objects.all().order_by("-date_saisie")
    serializer_class = ChequeSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ChequeFilter


class ChequeDetailOperationsView(APIView):
    def get(self, request, id_cheque):
        # On récupère le chèque
        cheque = get_object_or_404(Cheque, id_cheque=id_cheque)

        # On récupère toutes les opérations liées
        operations = cheque.operations.all().order_by("-date_saisie")

        # Sérialisation
        cheque_data = ChequeSerializer(cheque).data
        operations_data = ChequeOperationSerializer(operations, many=True).data

        return Response(
            {"chèque": cheque_data, "historique_operations": operations_data}
        )


"""
Vues API pour modification de maison et imposition de prime MRH
================================================================

Ces vues exposent les endpoints REST pour :
1. Imposer la prime d'une maison
2. Imposer la prime d'un devis
3. Lever une imposition
4. Consulter l'historique des impositions
"""


# ============================================================================
# VUE 1 : IMPOSER LA PRIME D'UNE MAISON
# ============================================================================


class ImposerPrimeMaisonView(APIView):
    """
    Imposer la prime NETTE d'une maison.

    POST /api/mrh/devis/{devis_id}/maisons/{maison_id}/imposer-prime/

    Fixe manuellement la prime nette d'une maison.
    La taxe sera recalculée automatiquement.

    Request body :
    {
        "montant_impose": 150000.00,  // Prime NETTE en FCFA
        "motif": "Négociation commerciale - remise de 10 000 FCFA"  // optionnel
    }

    Response 200 :
    {
        "success": true,
        "id_maison": 456,
        "imposition_id": 12,
        "montant_impose": 150000.00,
        "ancien_montant_nette": 160000.00,
        "ancien_montant_ttc": 189200.00,
        "nouvelle_taxe": 27375.00,
        "message": "Prime maison imposée à 150 000,00 FCFA (prime nette)",
        "totaux_devis": { ... }
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, devis_id, maison_id):
        """Impose la prime d'une maison."""

        # Validation
        serializer = ImpositionPrimeMaisonRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que la maison appartient au devis
        maison = get_object_or_404(DevisDetail, iddevisdetail=maison_id)
        if maison.iddevis_id != devis_id:
            return Response(
                {
                    "erreur": "MAISON_NOT_IN_DEVIS",
                    "message": f"La maison {maison_id} n'appartient pas au devis {devis_id}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Appeler le service
        service = MRHCalculService()

        try:
            resultat = service.imposer_prime_maison(
                id_maison=maison_id,
                montant_impose=serializer.validated_data["montant_impose"],
                user_id=(
                    request.user.id if hasattr(request.user, "id") else None
                ),
                user_nom=(
                    request.user.get_full_name()
                    if hasattr(request.user, "get_full_name")
                    else str(request.user)
                ),
                motif=serializer.validated_data.get("motif"),
            )

            if not resultat.get("success", False):
                return Response(resultat, status=status.HTTP_400_BAD_REQUEST)

            return Response(resultat, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {"erreur": "VALIDATION_ERROR", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {
                    "erreur": "INTERNAL_ERROR",
                    "message": f"Erreur lors de l'imposition : {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# VUE 2 : IMPOSER LA PRIME D'UN DEVIS
# ============================================================================


class ImposerPrimeDevisView(APIView):
    """
    Imposer la prime NETTE globale d'un devis.

    POST /api/mrh/devis/{devis_id}/imposer-prime/

    Fixe manuellement la prime nette totale du devis.
    - La prime est répartie proportionnellement sur les maisons
    - La taxe et les accessoires sont recalculés
    - Bloque toute modification des maisons

    Request body :
    {
        "montant_impose": 400000.00,  // Prime NETTE totale en FCFA
        "montant_accessoire": 5000.00,  // Accessoire total en FCFA (optionnel, sinon calculé automatiquement)
        "motif": "Négociation commerciale - accord client"  // optionnel
    }

    Response 201 :
    {
        "success": true,
        "id_devis": 123,
        "imposition_id": 15,
        "montant_impose": 400000.00,
        "ancien_montant_nette": 450000.00,
        "ancien_montant_ttc": 532500.00,
        "nouveau_detail": {
            "primenette": 400000.00,
            "taxe": 73000.00,
            "accessoire": 5000.00,
            "primettc": 478000.00
        },
        "message": "Prime devis imposée à 400 000,00 FCFA (prime nette)",
        "note": "La taxe et les accessoires sont calculés sur cette prime imposée"
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, devis_id):
        """Impose la prime globale d'un devis."""

        # Validation
        serializer = ImpositionPrimeDevisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que le devis existe
        devis = get_object_or_404(Devis, iddevis=devis_id)

        montant_impose = serializer.validated_data["montant_impose"]
        montant_accessoire = serializer.validated_data.get(
            "montant_accessoire"
        )

        # Appeler le service
        service = MRHCalculService()

        try:
            resultat = service.imposer_prime_devis(
                id_devis=devis_id,
                montant_impose=montant_impose,
                montant_accessoire=montant_accessoire,
                user_id=(
                    request.user.id if hasattr(request.user, "id") else None
                ),
                user_nom=(
                    request.user.get_full_name()
                    if hasattr(request.user, "get_full_name")
                    else str(request.user)
                ),
                motif=serializer.validated_data.get("motif"),
            )

            if not resultat.get("success", False):
                return Response(resultat, status=status.HTTP_400_BAD_REQUEST)

            return Response(resultat, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {"erreur": "VALIDATION_ERROR", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {
                    "erreur": "INTERNAL_ERROR",
                    "message": f"Erreur lors de l'imposition : {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# VUE 3 : LEVER UNE IMPOSITION
# ============================================================================


class LeverImpositionView(APIView):
    """
    Lever une imposition de prime (maison ou devis).

    DELETE /api/mrh/devis/{devis_id}/imposer-prime/  (devis)
    DELETE /api/mrh/devis/{devis_id}/maisons/{maison_id}/imposer-prime/  (maison)

    Désactive l'imposition et autorise à nouveau les modifications.

    Request body (optionnel) :
    {
        "motif": "Erreur de saisie corrigée"
    }

    Response 200 :
    {
        "success": true,
        "type_imposition": "DEVIS",
        "id_cible": 123,
        "message": "Imposition levée pour DEVIS 123"
    }
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, devis_id, maison_id=None):
        """Lève une imposition."""

        # Validation
        serializer = LeveeImpositionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        # Déterminer le type et l'ID
        if maison_id:
            # Lever imposition maison
            type_imposition = "MAISON"
            id_cible = maison_id

            # Vérifier que la maison existe et appartient au devis
            maison = get_object_or_404(DevisDetail, iddevisdetail=maison_id)
            if maison.iddevis_id != devis_id:
                return Response(
                    {
                        "erreur": "MAISON_NOT_IN_DEVIS",
                        "message": f"La maison {maison_id} n'appartient pas au devis {devis_id}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Lever imposition devis
            type_imposition = "DEVIS"
            id_cible = devis_id

            # Vérifier que le devis existe
            get_object_or_404(Devis, iddevis=devis_id)

        # Appeler le service
        service = MRHCalculService()

        try:
            resultat = service.lever_imposition(
                type_imposition=type_imposition,
                id_cible=id_cible,
                user_id=(
                    request.user.id if hasattr(request.user, "id") else None
                ),
                user_nom=(
                    request.user.get_full_name()
                    if hasattr(request.user, "get_full_name")
                    else str(request.user)
                ),
                motif_levee=serializer.validated_data.get("motif"),
            )

            return Response(resultat, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"erreur": "VALIDATION_ERROR", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {
                    "erreur": "INTERNAL_ERROR",
                    "message": f"Erreur lors de la levée : {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# VUE 4 : HISTORIQUE DES IMPOSITIONS
# ============================================================================


class HistoriqueImpositionsView(APIView):
    """
    Consulter l'historique des impositions d'une entité.

    GET /api/mrh/devis/{devis_id}/impositions/  (historique devis)
    GET /api/mrh/devis/{devis_id}/maisons/{maison_id}/impositions/  (historique maison)

    Retourne toutes les impositions (actives et levées) avec détails.

    Response 200 :
    {
        "type_imposition": "DEVIS",
        "id_cible": 123,
        "impositions": [
            {
                "id": 15,
                "montant_impose": 400000.00,
                "ancien_montant_nette": 450000.00,
                "user_nom": "John DOE",
                "date_imposition": "2024-12-18T10:30:00Z",
                "motif": "Négociation commerciale",
                "actif": true,
                "duree_jours": 5
            },
            ...
        ],
        "total": 3,
        "actives": 1,
        "levees": 2
    }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, devis_id, maison_id=None):
        """Récupère l'historique des impositions."""

        # Déterminer le type et l'ID
        if maison_id:
            type_imposition = "MAISON"
            id_cible = maison_id

            # Vérifier existence
            maison = get_object_or_404(DevisDetail, iddevisdetail=maison_id)
            if maison.iddevis_id != devis_id:
                return Response(
                    {
                        "erreur": "MAISON_NOT_IN_DEVIS",
                        "message": f"La maison {maison_id} n'appartient pas au devis {devis_id}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            type_imposition = "DEVIS"
            id_cible = devis_id
            get_object_or_404(Devis, iddevis=devis_id)

        # Récupérer l'historique
        impositions = ImpositionPrime.objects.filter(
            type_imposition=type_imposition, id_cible=id_cible
        ).order_by("-date_imposition")

        # Formater les données
        data_impositions = []
        for imp in impositions:
            data_impositions.append(
                {
                    "id": imp.id,
                    "montant_impose": float(imp.montant_impose),
                    "ancien_montant_nette": (
                        float(imp.ancien_montant_nette)
                        if imp.ancien_montant_nette
                        else None
                    ),
                    "ancien_montant_ttc": (
                        float(imp.ancien_montant_ttc)
                        if imp.ancien_montant_ttc
                        else None
                    ),
                    "user_nom": imp.user_nom,
                    "date_imposition": imp.date_imposition.isoformat(),
                    "motif": imp.motif,
                    "actif": imp.actif,
                    "date_levee": (
                        imp.date_levee.isoformat() if imp.date_levee else None
                    ),
                    "levee_par_user_nom": imp.levee_par_user_nom,
                    "motif_levee": imp.motif_levee,
                    "duree_jours": imp.duree_jours,
                }
            )

        # Statistiques
        total = impositions.count()
        actives = impositions.filter(actif=True).count()
        levees = impositions.filter(actif=False).count()

        return Response(
            {
                "type_imposition": type_imposition,
                "id_cible": id_cible,
                "impositions": data_impositions,
                "statistiques": {
                    "total": total,
                    "actives": actives,
                    "levees": levees,
                },
            },
            status=status.HTTP_200_OK,
        )


# ============================================================================
# VUE 6 : STATUT D'IMPOSITION
# ============================================================================


class StatutImpositionView(APIView):
    """
    Vérifier le statut d'imposition d'une entité.

    GET /api/mrh/devis/{devis_id}/statut-imposition/  (statut devis)
    GET /api/mrh/devis/{devis_id}/maisons/{maison_id}/statut-imposition/  (statut maison)

    Retourne si l'entité a une prime imposée et les détails.

    Response 200 :
    {
        "imposee": true,
        "type_imposition": "DEVIS",
        "id_cible": 123,
        "montant_impose": 400000.00,
        "user_nom": "John DOE",
        "date_imposition": "2024-12-18T10:30:00Z",
        "motif": "Négociation commerciale",
        "duree_jours": 5,
        "peut_modifier": false,
        "message": "Prime imposée à 400 000,00 FCFA le 18/12/2024 par John DOE"
    }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, devis_id, maison_id=None):
        """Vérifie le statut d'imposition."""

        # Déterminer le type et l'ID
        if maison_id:
            type_imposition = "MAISON"
            id_cible = maison_id

            # Récupérer la maison
            maison = get_object_or_404(DevisDetail, iddevisdetail=maison_id)
            if maison.iddevis_id != devis_id:
                return Response(
                    {"erreur": "MAISON_NOT_IN_DEVIS"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            imposee = maison.prime_imposee
            montant = maison.primenette if imposee else None
        else:
            type_imposition = "DEVIS"
            id_cible = devis_id

            # Récupérer le devis
            devis = get_object_or_404(Devis, iddevis=devis_id)
            imposee = devis.prime_imposee
            montant = devis.primenette if imposee else None

        # Si imposée, récupérer les détails
        if imposee:
            imposition = ImpositionPrime.objects.filter(
                type_imposition=type_imposition, id_cible=id_cible, actif=True
            ).first()

            if imposition:
                return Response(
                    {
                        "imposee": True,
                        "type_imposition": type_imposition,
                        "id_cible": id_cible,
                        "montant_impose": float(montant),
                        "user_nom": imposition.user_nom,
                        "date_imposition": imposition.date_imposition.isoformat(),
                        "motif": imposition.motif,
                        "duree_jours": imposition.duree_jours,
                        "peut_modifier": False,
                        "message": (
                            f"Prime imposée à {montant:,.2f} FCFA "
                            f"le {imposition.date_imposition.strftime('%d/%m/%Y')} "
                            f"par {imposition.user_nom}"
                        ),
                    }
                )

        # Pas d'imposition
        return Response(
            {
                "imposee": False,
                "type_imposition": type_imposition,
                "id_cible": id_cible,
                "peut_modifier": True,
                "message": "Aucune imposition active",
            }
        )


"""
Vue pour consulter les détails complets d'une maison MRH
=========================================================
"""


class DetailMaisonView(APIView):
    """
    Consulter les détails complets d'une maison MRH.

    GET /api/mrh/devis/{devis_id}/maisons/{maison_id}/details/

    Retourne toutes les informations sur une maison :
    - Paramètres de calcul (usage, valeurs, loyer, etc.)
    - Liste complète des garanties avec leurs montants
    - Options appliquées
    - Totaux financiers détaillés
    - Statut d'imposition
    - Métadonnées

    Response 200 :
    {
        "id_maison": 456,
        "id_devis": 123,
        "numero_devis": "DEV-MRH-2024-00123",
        "adresse": "Cocody - Riviera Golf",
        "parametres": {
            "code_usage": "proprietaire_occupant_total",
            "libelle_usage": "Propriétaire occupant - Total",
            "valeur_batiment": 50000000.00,
            "valeur_contenu": 10000000.00,
            "loyer_mensuel": null,
            "capital_rvt": null
        },
        "options": [
            {
                "code_option": "presence_gardien",
                "libelle": "Présence d'un gardien",
                "signe": "-",
                "pourcentage": 10.00,
                "impact_financier": -15368.00
            }
        ],
        "sous_garanties": [
            {
                "id_garantie": 101,
                "code_garantie": "INC001",
                "libelle": "Incendie",
                "type": "OBLIGATOIRE",
                "acquise": true,
                "prime_nette": 38000.00,
                "prime_annuelle": 40000.00,
                "taux_taxe": 0.250,
                "taxe": 9500.00,
                "prime_ttc": 47500.00
            },
            ...
        ],
        "nombre_garanties_obligatoires": 7,
        "nombre_garanties_optionnelles": 2,
        "nombre_garanties_total": 9,
        "totaux": {
            "prime_nette_totale": 153680.00,
            "prime_annuelle_totale": 165000.00,
            "taxe_totale": 27869.60,
            "prime_ttc_totale": 181549.60,
            "economie_options": 11320.00
        },
        "imposition": {
            "imposee": false,
            "montant_impose": null,
            "date_imposition": null,
            "user_nom": null,
            "motif": null,
            "duree_jours": null
        },
        "date_creation": "2024-12-18T10:30:00Z",
        "date_modification": "2024-12-18T11:45:00Z",
        "peut_etre_modifiee": true
    }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, devis_id, maison_id):
        """Récupère les détails complets d'une maison."""

        try:
            # Récupérer la maison
            maison = get_object_or_404(
                DevisDetail.objects.select_related("iddevis"),
                iddevisdetail=maison_id,
            )

            # Vérifier que la maison appartient au devis
            if maison.iddevis_id != devis_id:
                return Response(
                    {
                        "error": "MAISON_NOT_IN_DEVIS",
                        "message": f"La maison {maison_id} n'appartient pas au devis {devis_id}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Construire les données complètes
            details = self._construire_details(maison)

            # Sérialiser
            serializer = DetailMaisonSerializer(details)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "error": "INTERNAL_ERROR",
                    "message": f"Erreur lors de la récupération des détails : {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _construire_details(self, maison):
        """Construit le dictionnaire complet des détails de la maison."""

        # 1. Récupérer les garanties
        sous_garanties = self._get_garanties(maison)

        # 2. Extraire les paramètres depuis les nouvelles colonnes
        parametres = self._extraire_parametres(maison)

        # 3. Extraire les options depuis JSON
        options = self._extraire_options(maison)

        # 4. Calculer les totaux
        totaux = self._calculer_totaux(maison, sous_garanties)

        # 5. Récupérer les infos d'imposition
        imposition = self._get_imposition_info(maison)

        # 6. Statistiques garanties
        sous_garanties_obligatoires = [
            g for g in sous_garanties if g["type"] == "OBLIGATOIRE"
        ]
        sous_garanties_optionnelles = [
            g for g in sous_garanties if g["type"] == "OPTIONNELLE"
        ]

        return {
            # Identifiants
            "id_maison": maison.iddevisdetail,
            "id_devis": maison.iddevis_id,
            "numero_devis": (
                maison.iddevis.numerodevis if maison.iddevis else None
            ),
            "matricule": maison.matricule or None,
            # Informations générales
            "adresse": maison.adressecnd or "",
            "description": maison.observation,
            # Paramètres
            "parametres": parametres,
            # Options
            "options": options,
            # Garanties
            "sous_garanties": sous_garanties,
            "nombre_sous_garanties_obligatoires": len(
                sous_garanties_obligatoires
            ),
            "nombre_sous_garanties_optionnelles": len(
                sous_garanties_optionnelles
            ),
            "nombre_sous_garanties_total": len(sous_garanties),
            # Totaux
            "totaux": totaux,
            # Imposition
            "imposition": imposition,
            # Dates (non disponibles pour l'instant)
            "date_creation": None,
            "date_modification": None,
            # Métadonnées
            "peut_etre_modifiee": not maison.prime_imposee,
        }

    def _get_garanties(self, maison):
        """Récupère toutes les garanties de la maison avec leurs détails."""

        from django.db import connection

        sous_garanties = []

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    dg.idgarantie,
                    g.code,
                    g.libelle,
					g.type,
                    dg.acquise,
                    dg.primenette,
                    dg.primeannuelle,
                    dg.taxe,
                    CASE 
                        WHEN dg.taxe > 0 AND dg.primenette > 0 
                        THEN dg.taxe / dg.primenette
                        ELSE 0.145
                    END as taux_taxe
                FROM stddevisdetgarantie dg
                JOIN stdmrh_sous_garantie g ON dg.idgarantie = g.idsousgarantie
                WHERE dg.iddevisdet = %s
                ORDER BY g.libelle
            """,
                [maison.iddevisdetail],
            )

            for row in cursor.fetchall():
                (
                    id_garantie,
                    code,
                    libelle,
                    type_garantie,
                    acquise,
                    prime_nette,
                    prime_annuelle,
                    taxe,
                    taux_taxe,
                ) = row

                prime_nette = (
                    Decimal(str(prime_nette)) if prime_nette else Decimal("0")
                )
                prime_annuelle = (
                    Decimal(str(prime_annuelle))
                    if prime_annuelle
                    else Decimal("0")
                )
                taxe = Decimal(str(taxe)) if taxe else Decimal("0")
                taux_taxe = (
                    Decimal(str(taux_taxe)) if taux_taxe else Decimal("0.145")
                )

                # Déterminer le type (obligatoire ou optionnelle)
                # On considère qu'une garantie avec prime_annuelle = prime_nette est obligatoire
                # et qu'une garantie forfaitaire (sans répartition) est optionnelle
                # type_garantie = tyself._determiner_type_garantie(code, prime_annuelle, prime_nette)

                sous_garanties.append(
                    {
                        "id_sous_garantie": id_garantie,
                        "code_sous_garantie": code,
                        "libelle": libelle,
                        "type": type_garantie,
                        "acquise": bool(acquise),
                        "prime_nette": float(prime_nette),
                        "prime_annuelle": float(prime_annuelle),
                        "taux_taxe": float(taux_taxe),
                        "taxe": float(taxe),
                        "prime_ttc": float(prime_nette + taxe),
                    }
                )

        return sous_garanties

    def _determiner_type_garantie(
        self, code_garantie, prime_annuelle, prime_nette
    ):
        """Détermine si une garantie est obligatoire ou optionnelle."""

        # Les garanties optionnelles à forfait sont facilement identifiables
        codes_optionnels = ["RC_MEMBRE", "BRIS_GLACE", "VOL_AGGRAVE"]

        if any(opt in code_garantie.upper() for opt in codes_optionnels):
            return "OPTIONNELLE"

        return "OBLIGATOIRE"

    def _extraire_parametres(self, maison):
        """Extrait les paramètres de calcul depuis la maison."""

        code_usage = maison.modelevehicule or "proprietaire_occupant_total"

        loyer_mensuel = (
            Decimal(maison.chargeutile)
            if maison.chargeutile and maison.chargeutile > 0
            else None
        )
        capital_rvt = (
            Decimal(maison.valeuraccessoire)
            if maison.valeuraccessoire and maison.valeuraccessoire > 0
            else None
        )

        return {
            "code_usage": code_usage,
            "libelle_usage": self._get_libelle_usage(code_usage),
            "valeur_batiment": Decimal(maison.valeurneuve or 0),
            "valeur_contenu": Decimal(maison.valeurvenale or 0),
            "loyer_mensuel": loyer_mensuel,
            "capital_rvt": capital_rvt,
        }

    def _extraire_code_usage(self, observation):
        """Extrait le code usage depuis l'observation."""

        # Liste des codes usage possibles
        from configuration_api.models import UsageHabitation

        codes_usage = list(
            UsageHabitation.objects.values_list("code", flat=True)
        )

        observation_lower = observation.lower()

        for code in codes_usage:
            if code in observation_lower:
                return code

        # Par défaut
        return "proprietaire_occupant_total"

    def _get_libelle_usage(self, code_usage):
        """Retourne le libellé de l'usage."""

        libelles = {
            "proprietaire_occupant_total": "Propriétaire occupant - Total",
            "proprietaire_occupant_rez": "Propriétaire occupant - Rez-de-chaussée",
            "proprietaire_bailleur": "Propriétaire bailleur",
            "proprietaire_non_occupant": "Propriétaire non occupant",
            "locataire": "Locataire",
            "locataire_saisonnier": "Locataire saisonnier",
            "locaux_commerciaux": "Locaux commerciaux",
            "batiment_usage_mixte": "Bâtiment à usage mixte",
        }

        return libelles.get(code_usage, code_usage)

    def _extraire_options(self, maison):
        """Extrait les options appliquées depuis le JSON."""

        if not maison.conducteur or maison.conducteur.strip() in [
            "",
            "[]",
            "null",
        ]:
            return []

        try:
            codes_options = json.loads(maison.conducteur)
        except (json.JSONDecodeError, TypeError, ValueError):
            # Si le JSON est invalide, retourner liste vide
            return []

        if not codes_options or not isinstance(codes_options, list):
            return []

        # Récupérer les détails des options depuis stdmrhoption
        from django.db import connection

        options = []

        if codes_options:
            codes = [opt["code_option"] for opt in codes_options]
            placeholders = ",".join(["%s"] * len(codes_options))

            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT code AS code_option, libelle, signe_ajustement AS signe, taux_ajustement AS pourcentage
                    FROM stdmrh_option
                    WHERE code IN ({placeholders})
                    ORDER BY libelle
                """,
                    codes,
                )

                for row in cursor.fetchall():
                    code, libelle, signe, pourcentage = row

                    # Calculer l'impact financier estimé si possible
                    impact = None
                    if pourcentage and maison.primeannuelle:
                        base = float(maison.primeannuelle)
                        pct = float(pourcentage) / 100
                        if signe == "-":
                            impact = -1 * base * pct
                        else:
                            impact = base * pct

                    options.append(
                        {
                            "code_option": code,
                            "libelle": libelle,
                            "signe": signe,
                            "pourcentage": (
                                float(pourcentage) if pourcentage else None
                            ),
                            "impact_financier": impact,
                        }
                    )

        return options

    def _extraire_adresse(self, observation):
        """Extrait l'adresse depuis l'observation."""

        if not observation:
            return ""

        # L'adresse est généralement au début de l'observation
        # Format possible : "Adresse - usage - autres infos"
        parts = observation.split(" - ")
        if parts:
            return parts[0].strip()

        return observation[:100]  # Premiers 100 caractères

    def _calculer_totaux(self, maison, garanties):
        """Calcule les totaux financiers."""

        prime_nette_totale = sum(g["prime_nette"] for g in garanties)
        prime_annuelle_totale = sum(g["prime_annuelle"] for g in garanties)
        taxe_totale = sum(g["taxe"] for g in garanties)

        return {
            "prime_nette_totale": prime_nette_totale,
            "prime_annuelle_totale": prime_annuelle_totale,
            "taxe_totale": taxe_totale,
            "prime_ttc_totale": prime_nette_totale + taxe_totale,
            "economie_options": prime_annuelle_totale - prime_nette_totale,
        }

    def _get_imposition_info(self, maison):
        """Récupère les informations d'imposition."""

        if not maison.prime_imposee:
            return {
                "imposee": False,
                "montant_impose": None,
                "date_imposition": None,
                "user_nom": None,
                "motif": None,
                "duree_jours": None,
            }

        # Récupérer l'imposition active
        imposition = ImpositionPrime.objects.filter(
            type_imposition="MAISON", id_cible=maison.iddevisdetail, actif=True
        ).first()

        if imposition:
            return {
                "imposee": True,
                "montant_impose": float(maison.primenette),
                "date_imposition": imposition.date_imposition,
                "user_nom": imposition.user_nom,
                "motif": imposition.motif,
                "duree_jours": imposition.duree_jours,
            }

        return {
            "imposee": True,
            "montant_impose": float(maison.primenette),
            "date_imposition": maison.prime_imposee_date,
            "user_nom": None,
            "motif": None,
            "duree_jours": None,
        }
