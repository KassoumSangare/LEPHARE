from django.db import connection
from django.db.models import F, Q, Subquery
from django.http.response import JsonResponse
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from knox.auth import TokenAuthentication
from rest_framework import permissions, status, viewsets
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Accessoire,
    AccessoireCourtierParCompagnie,
    Acte,
    AssistanceAutomobile,
    Avenant,
    AvenantProduit,
    Banque,
    Branche,
    Carrosserie,
    Categorie,
    CategoriePermis,
    CollegeSante,
    Commission,
    CommissionProduit,
    Commune,
    Compagnie,
    Continent,
    DelaiAvisEcheance,
    DomaineActiviteRC,
    Energie,
    FormuleSecuriteRoutiere,
    Garantie,
    GarantieRisque,
    GenreVehicule,
    GroupeUtilisateur,
    Intermediaire,
    LienJuridiqueSante,
    Marque,
    Menu,
    MenuParent,
    ModeEncaissement,
    ModeleVehicule,
    Offre,
    OffreAutomobileBoisee,
    OffreCollegeSante,
    OffreDetail,
    OffreGarantie,
    ParametreSite,
    Pays,
    Produit,
    Profession,
    ProfessionIa,
    Qualite,
    QualiteAyantDroit,
    QualiteSouscripteurMrh,
    ReductionFlotte,
    Region,
    Risque,
    SecteurActivite,
    SousGarantie,
    SystemeSecurite,
    Tarif,
    TarifDetail,
    TauxTaxeGarantieProduit,
    TypeAssure,
    TypeContratSante,
    TypeReduction,
    TypeSouscripteur,
    TypeVehicule,
    UsageVehicule,
    Utilisateur,
    Ville,
    ZoneCouvertureSante,
    ZoneVoyage,
)
from .serializers import (
    AccessoireCourtierParCompagnieSerializer,
    AccessoireSerializer,
    ActeSerializer,
    AssistanceAutomobileSerializer,
    AvenantSerializer,
    BanqueSerializer,
    BrancheSerializer,
    CarrosserieSerializer,
    CategoriePermisSerializer,
    CategorieSerializer,
    ClockedScheduleSerializer,
    CollegeSanteSerializer,
    CommissionProduitSerializer,
    CommissionSerializer,
    CommuneSerializer,
    CompagnieSerializer,
    ContinentSerializer,
    CrontabScheduleSerializer,
    DelaiAvisEcheanceSerializer,
    DemandeAvenantSerializer,
    DemandeGarantieHabitationSerializer,
    DemandeGarantieIaSerializer,
    DemandeGarantieRisquesDiversSerializer,
    DemandeGarantieSerializer,
    DemandeGarantieVoyageSerializer,
    DomaineActiviteRCSerializer,
    EnergieSerializer,
    EnregistrementOffreGarantieSerializer,
    FormuleSecuriteRoutiereParCompagnieSerializer,
    FormuleSecuriteRoutiereSerializer,
    GarantieParProduitSerializer,
    GarantiePourOffreSerializer,
    GarantieProposeeSerializer,
    GarantieRisqueSerializer,
    GarantieSerializer,
    GenreVehiculeSerializer,
    GroupeUtilisateurSerializer,
    IntermediaireSerializer,
    IntervalScheduleSerializer,
    LienJuridiqueSanteSerializer,
    MarqueSerializer,
    MenuParentSerializer,
    MenuSerializer,
    ModeEncaissementSerializer,
    ModeleVehiculeSerializer,
    OffreCollegeSanteSerializer,
    OffreDetailSerializer,
    OffreGarantieSerializer,
    OffreParProduitSerializer,
    OffreSanteParTarifSerializer,
    OffreSerializer,
    ParametreSiteSerializer,
    PaysSerializer,
    PaysZoneSerializer,
    PeriodicTaskSerializer,
    PrimeCalculationInputSerializer,
    PrimeCalculationOutputSerializer,
    ProduitSerializer,
    ProfessionIaSerializer,
    ProfessionSerializer,
    QualiteAyantDroitSerializer,
    QualiteSerializer,
    QualiteSouscripteurMrhSerializer,
    ReductionFlotteSerializer,
    RegionSerializer,
    RisqueSerializer,
    SecteurActiviteSerializer,
    SolarScheduleSerializer,
    SousGarantieSerializer,
    SystemeSecuriteSerializer,
    TarifDetailSerializer,
    TarifParProduitSerializer,
    TarifSerializer,
    TauxTaxeGarantieProduitSerializer,
    TypeAssureSerializer,
    TypeContratSanteSerializer,
    TypeReductionSerializer,
    TypeSouscripteurSerializer,
    TypeVehiculeSerializer,
    UsageVehiculeSerializer,
    UtilisateurSerializer,
    VilleSerializer,
    ZoneCouvertureSanteSerializer,
    ZoneVoyageSerializer,
)
from .utils import (
    get_college_sante_par_offre,
    get_formule_securite_routiere,
    get_garantie_offre,
    get_garantie_offre_ia,
    get_garantie_offre_mrh,
    get_garantie_offre_risques_divers,
    get_garantie_offre_voyage,
    get_garantie_produit,
    get_liste_avenant_produit,
    get_liste_pays_voyage,
    get_offre_par_produit,
    get_offre_sante_par_tarif,
    get_offre_voyage,
    get_tarif_par_produit,
    get_tarif_voyage,
    get_zone_couverture_sante,
    save_offre_garantie,
)


class SettingsModelViewSet(viewsets.ModelViewSet):
    permission_classes_by_action = {
        "create": (
            permissions.IsAuthenticated,
            permissions.IsAdminUser,
        ),
        "list": (permissions.IsAuthenticated,),
        "retrieve": (permissions.IsAuthenticated,),
        "update": (
            permissions.IsAuthenticated,
            permissions.IsAdminUser,
        ),
        "destroy": (
            permissions.IsAuthenticated,
            permissions.IsAdminUser,
        ),
        "search": (permissions.IsAuthenticated,),
    }


class PrimeCalculationView(APIView):
    """
    Vue permettant de calculer :
    - le taux de taxe applicable selon le produit
    - le coût de police basé sur la prime nette
    - le montant de la taxe
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request, *args, **kwargs):
        from decimal import ROUND_HALF_UP, Decimal

        input_serializer = PrimeCalculationInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        id_compagnie = input_serializer.validated_data["id_compagnie"]
        id_produit = input_serializer.validated_data["id_produit"]
        prime_nette = input_serializer.validated_data["prime_nette"]
        date_effet = input_serializer.validated_data["date_effet"]
        id_offre = input_serializer.validated_data["id_offre"]

        # 2. Taux de taxe
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT public.fn_get_taux_taxe(%s, %s, %s, %s)",
                [id_compagnie, id_produit, id_offre, date_effet],
            )
            row = cursor.fetchone()
            taux_taxe = row[0] if row is not None else Decimal("0")

        # 3. Accessoires
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT accessoire_compagnie, accessoire_intermediaire "
                "FROM public.fn_get_accessoire(%s, %s, %s, %s, %s)",
                [prime_nette, id_produit, id_offre, id_compagnie, date_effet],
            )
            row = cursor.fetchone()

            accessoire_compagnie = row[0] if row else Decimal("0")
            accessoire_intermediaire = row[1] if row else Decimal("0")

            cout_police = accessoire_compagnie + accessoire_intermediaire

        # 4. Taxe
        base_taxe = (
            (prime_nette + cout_police) * taux_taxe / Decimal("100")
        )  # Arrondi à l’unité (0 décimale), comme round(..., 0) mais en Decimal
        montant_taxe = base_taxe.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        prime_totale = prime_nette + cout_police + montant_taxe

        output_data = {
            "taux_taxe": taux_taxe,
            "accessoire": cout_police,
            "montant_taxe": montant_taxe,
            "prime_totale": prime_totale,
        }

        output_serializer = PrimeCalculationOutputSerializer(output_data)
        return Response(output_serializer.data, status=status.HTTP_200_OK)


class GarantieViewSet(viewsets.ModelViewSet):
    queryset = Garantie.objects.filter(~Q(IdGarantie=0))
    serializer_class = GarantieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class DomaineActiviteRCViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    queryset = DomaineActiviteRC.objects.all()
    serializer_class = DomaineActiviteRCSerializer


class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class MenuParentViewSet(viewsets.ModelViewSet):
    queryset = MenuParent.objects.all()
    serializer_class = MenuParentSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class UtilisateurViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer


class GroupeUtilisateurViewSet(viewsets.ModelViewSet):
    queryset = GroupeUtilisateur.objects.all()
    serializer_class = GroupeUtilisateurSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class SousGarantieViewSet(viewsets.ModelViewSet):
    queryset = SousGarantie.objects.filter(~Q(IdSousGarantie=0))
    serializer_class = SousGarantieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class GarantieRisqueViewSet(viewsets.ModelViewSet):
    queryset = GarantieRisque.objects.all()
    serializer_class = GarantieRisqueSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class CategorieViewSet(viewsets.ModelViewSet):
    queryset = Categorie.objects.all()
    serializer_class = CategorieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class TarifViewSet(viewsets.ModelViewSet):
    queryset = Tarif.objects.filter(~Q(IdTarif=0))
    serializer_class = TarifSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class QualiteSouscripteurMrhViewSet(viewsets.ModelViewSet):
    queryset = QualiteSouscripteurMrh.objects.all()
    serializer_class = QualiteSouscripteurMrhSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class TarifDetailViewSet(viewsets.ModelViewSet):
    queryset = TarifDetail.objects.all()
    serializer_class = TarifDetailSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class BrancheViewSet(viewsets.ModelViewSet):
    queryset = Branche.objects.all()
    serializer_class = BrancheSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class RisqueViewSet(viewsets.ModelViewSet):
    queryset = Risque.objects.all()
    serializer_class = RisqueSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class EnergieViewSet(viewsets.ModelViewSet):
    queryset = Energie.objects.filter(~Q(IdEnergie=0))
    serializer_class = EnergieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class OffreDetailViewSet(viewsets.ModelViewSet):
    queryset = OffreDetail.objects.all()
    serializer_class = OffreDetailSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class OffreViewSet(viewsets.ModelViewSet):
    queryset = Offre.objects.annotate(
        OffreBoisee=OffreAutomobileBoisee(F("IdOffre"))
    ).filter(~Q(IdOffre=0))
    serializer_class = OffreSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class OffreGarantieViewSet(viewsets.ModelViewSet):
    queryset = OffreGarantie.objects.filter(
        ~Q(IdOffre=0) & ~Q(IdSousGarantie=0) & ~Q(IdCompagnie=0)
    )
    serializer_class = OffreGarantieSerializer
    permission_classes_by_action = {
        "create": (
            permissions.IsAuthenticated,
            permissions.IsAdminUser,
        ),
        "list": (permissions.IsAuthenticated,),
        "retrieve": (permissions.IsAuthenticated,),
        "update": (
            permissions.IsAuthenticated,
            permissions.IsAdminUser,
        ),
        "destroy": (
            permissions.IsAuthenticated,
            permissions.IsAdminUser,
        ),
        "search": (permissions.IsAuthenticated,),
    }


class GenreVehiculeViewSet(viewsets.ModelViewSet):
    queryset = GenreVehicule.objects.filter(~Q(IdGenre=0))
    serializer_class = GenreVehiculeSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class FormuleSecuriteRoutiereViewSet(SettingsModelViewSet):
    queryset = FormuleSecuriteRoutiere.objects.all()
    serializer_class = FormuleSecuriteRoutiereSerializer


class AvenantViewSet(viewsets.ModelViewSet):
    queryset = Avenant.objects.filter(~Q(IdAvenant=0))
    serializer_class = AvenantSerializer
    permission_classes_by_action = {
        "create": (
            permissions.IsAuthenticated,
            permissions.IsAdminUser,
        ),
        "list": (permissions.IsAuthenticated,),
        "retrieve": (permissions.IsAuthenticated,),
        "update": (
            permissions.IsAuthenticated,
            permissions.IsAdminUser,
        ),
        "destroy": (
            permissions.IsAuthenticated,
            permissions.IsAdminUser,
        ),
        "search": (permissions.IsAuthenticated,),
    }

    def list(self, request, *args, **kwargs):

        id_produit = request.query_params.get("idproduit")
        contrat_flotte = request.query_params.get("flotte")
        filtre_final = True

        if id_produit is None and contrat_flotte is None:
            filtre_final = False
            queryset = Avenant.objects.filter(~Q(IdAvenant=0))
        elif id_produit is None:
            contrat_flotte = contrat_flotte.lower() in [
                "true",
                "1",
                "yes",
                "vrai",
                "vraie",
                "oui",
                "o",
                "y",
                "v",
                "t",
            ]
            if contrat_flotte:
                avenants_produits = AvenantProduit.objects.filter(
                    Q(flotte=True)
                )
            else:
                avenants_produits = AvenantProduit.objects.filter(Q(mono=True))

            queryset = Avenant.objects.filter(
                IdAvenant__in=Subquery(avenants_produits.values("avenant"))
            )
        elif contrat_flotte is None:
            try:
                id_produit = int(id_produit)
                contrat_produit = Produit.objects.get(pk=id_produit)
                avenants_produits = AvenantProduit.objects.filter(
                    Q(produit=contrat_produit)
                )
                queryset = Avenant.objects.filter(
                    IdAvenant__in=Subquery(avenants_produits.values("avenant"))
                )
            except Exception:
                queryset = Avenant.objects.none()
                filtre_final = False
        else:
            try:
                contrat_flotte = contrat_flotte.lower() in [
                    "true",
                    "1",
                    "yes",
                    "vrai",
                    "vraie",
                    "oui",
                    "o",
                    "y",
                    "v",
                    "t",
                ]
                id_produit = int(id_produit)
                contrat_produit = Produit.objects.get(pk=id_produit)
                if contrat_flotte:
                    avenants_produits = AvenantProduit.objects.filter(
                        Q(produit=contrat_produit) & Q(flotte=True)
                    )
                else:
                    avenants_produits = AvenantProduit.objects.filter(
                        Q(produit=contrat_produit) & Q(mono=True)
                    )
                queryset = Avenant.objects.filter(
                    IdAvenant__in=Subquery(avenants_produits.values("avenant"))
                )
            except Exception:
                queryset = Avenant.objects.none()
                filtre_final = False

        if filtre_final:
            affaire_nouvelle = Avenant.objects.filter(Q(CodeAvenant="AFN"))
            if affaire_nouvelle:
                id_avenant_afn = affaire_nouvelle.first().IdAvenant
                queryset = queryset.filter(~Q(IdAvenant=id_avenant_afn))

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CompagnieViewSet(viewsets.ModelViewSet):
    queryset = Compagnie.objects.filter(~Q(IdCompagnie=0) & Q(Active=True))
    serializer_class = CompagnieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class CarrosserieViewSet(viewsets.ModelViewSet):
    queryset = Carrosserie.objects.all()
    serializer_class = CarrosserieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class TypeVehiculeViewSet(viewsets.ModelViewSet):
    queryset = TypeVehicule.objects.filter(~Q(id=0))
    serializer_class = TypeVehiculeSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class TypeAssureViewSet(viewsets.ModelViewSet):
    queryset = TypeAssure.objects.all()
    serializer_class = TypeAssureSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class TypeSouscripteurViewSet(viewsets.ModelViewSet):
    queryset = TypeSouscripteur.objects.all()
    serializer_class = TypeSouscripteurSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ProfessionViewSet(viewsets.ModelViewSet):
    queryset = Profession.objects.all().order_by("Libelle").values()
    serializer_class = ProfessionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ActeViewSet(viewsets.ModelViewSet):
    queryset = Acte.objects.all()
    serializer_class = ActeSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class CommissionViewSet(viewsets.ModelViewSet):
    queryset = Commission.objects.all()
    serializer_class = CommissionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class CommissionProduitViewSet(viewsets.ModelViewSet):
    queryset = CommissionProduit.objects.filter(~Q(produit=0))
    serializer_class = CommissionProduitSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class TauxTaxeGarantieProduitViewSet(viewsets.ModelViewSet):
    queryset = TauxTaxeGarantieProduit.objects.filter(
        ~Q(garantie=0) & ~Q(produit=0)
    )
    serializer_class = TauxTaxeGarantieProduitSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class AccessoireViewSet(viewsets.ModelViewSet):
    queryset = Accessoire.objects.filter(~Q(produit=0))
    serializer_class = AccessoireSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class PaysViewSet(viewsets.ModelViewSet):
    queryset = Pays.objects.all()
    serializer_class = PaysSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class VilleViewSet(viewsets.ModelViewSet):
    queryset = Ville.objects.all()
    serializer_class = VilleSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class CommuneViewSet(viewsets.ModelViewSet):
    queryset = Commune.objects.all()
    serializer_class = CommuneSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class IntermediaireViewSet(viewsets.ModelViewSet):
    queryset = Intermediaire.objects.filter(~Q(IdIntermediaire=0))
    serializer_class = IntermediaireSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class QualiteViewSet(viewsets.ModelViewSet):
    queryset = Qualite.objects.all()
    serializer_class = QualiteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class TermeViewSet(viewsets.ViewSet):
    def list(self, request):
        data = [
            {
                "IdTerme": 1,
                "Libelle": "Tacite reconduction",
            },
            {
                "IdTerme": 2,
                "Libelle": "Ferme",
            },
            {
                "IdTerme": 3,
                "Libelle": "Autre",
            },
        ]

        # 3. Return the list directly
        return Response(data)

    def retrieve(self, request, pk=None):
        data = {
            1: {
                "IdTerme": 1,
                "Libelle": "Tacite reconduction",
            },
            2: {
                "IdTerme": 2,
                "Libelle": "Ferme",
            },
            3: {
                "IdTerme": 3,
                "Libelle": "Autre",
            },
        }
        return Response(data.get(pk, {}))

    permission_classes = [
        permissions.IsAuthenticated,
    ]


class SecteurActiviteViewSet(viewsets.ModelViewSet):
    queryset = SecteurActivite.objects.all()
    serializer_class = SecteurActiviteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class QualiteAyantDroitViewSet(viewsets.ModelViewSet):
    queryset = QualiteAyantDroit.objects.all()
    serializer_class = QualiteAyantDroitSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class MarqueViewSet(viewsets.ModelViewSet):
    queryset = Marque.objects.filter(~Q(IdMarque=0))
    serializer_class = MarqueSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class SystemeSecuriteViewSet(viewsets.ModelViewSet):
    queryset = SystemeSecurite.objects.all()
    serializer_class = SystemeSecuriteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ModeleVehiculeViewSet(viewsets.ModelViewSet):
    queryset = ModeleVehicule.objects.all()
    serializer_class = ModeleVehiculeSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class UsageVehiculeViewSet(viewsets.ModelViewSet):
    queryset = UsageVehicule.objects.filter(~Q(IdUsage=0))
    serializer_class = UsageVehiculeSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        # permissions.AllowAny,
    ]


class TypeReductionViewSet(viewsets.ModelViewSet):
    queryset = TypeReduction.objects.all()
    serializer_class = TypeReductionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        # permissions.AllowAny,
    ]


class ContinentViewSet(viewsets.ModelViewSet):
    queryset = Continent.objects.all()
    serializer_class = ContinentSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        # permissions.AllowAny,
    ]


class ZoneVoyageViewSet(viewsets.ModelViewSet):
    queryset = ZoneVoyage.objects.all()
    serializer_class = ZoneVoyageSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        # permissions.AllowAny,
    ]


class ProduitViewSet(viewsets.ModelViewSet):
    queryset = Produit.objects.filter(~Q(id_produit=0))
    serializer_class = ProduitSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        # permissions.AllowAny,
    ]


class ProfessionIaViewSet(viewsets.ModelViewSet):
    queryset = (
        ProfessionIa.objects.filter(active=True)
        .order_by("libelle_profession")
        .values()
    )
    serializer_class = ProfessionIaSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        # permissions.AllowAny,
    ]


class CategoriePermisViewSet(viewsets.ModelViewSet):
    queryset = CategoriePermis.objects.all().order_by("libelle").values()
    serializer_class = CategoriePermisSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        # permissions.AllowAny,
    ]


class BanqueViewSet(viewsets.ModelViewSet):
    queryset = Banque.objects.all()
    serializer_class = BanqueSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ModeEncaissementViewSet(viewsets.ModelViewSet):
    queryset = (
        ModeEncaissement.objects.all().order_by("ordreaffichage").values()
    )
    serializer_class = ModeEncaissementSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class AccessoireCourtierParCompagnieViewSet(viewsets.ModelViewSet):
    queryset = AccessoireCourtierParCompagnie.objects.all()
    serializer_class = AccessoireCourtierParCompagnieSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class LienJuridiqueSanteViewSet(viewsets.ModelViewSet):
    queryset = (
        LienJuridiqueSante.objects.all().order_by("-libellelien").values()
    )
    serializer_class = LienJuridiqueSanteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class ZoneCouvertureSanteViewSet(viewsets.ModelViewSet):
    queryset = ZoneCouvertureSante.objects.all()
    serializer_class = ZoneCouvertureSanteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class CollegeSanteViewSet(viewsets.ModelViewSet):
    queryset = CollegeSante.objects.all()
    serializer_class = CollegeSanteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class OffreCollegeSanteViewSet(viewsets.ModelViewSet):
    queryset = OffreCollegeSante.objects.all()
    serializer_class = OffreCollegeSanteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_garantie(request):
    garantiedemandee_data = JSONParser().parse(request)
    print("JSON de la requête:", garantiedemandee_data)
    garantiedemandee_serializer = DemandeGarantieSerializer(
        data=garantiedemandee_data
    )
    if garantiedemandee_serializer.is_valid():
        garantieproposee_serializer = GarantieProposeeSerializer(
            get_garantie_offre(garantiedemandee_data), many=True
        )
        return JsonResponse(
            garantieproposee_serializer.data,
            status=status.HTTP_201_CREATED,
            safe=False,
        )
    return JsonResponse(
        garantiedemandee_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_garantie_ia(request):
    garantiedemandee_data = JSONParser().parse(request)
    print("JSON de la requête:", garantiedemandee_data)
    garantiedemandee_serializer = DemandeGarantieIaSerializer(
        data=garantiedemandee_data
    )
    if garantiedemandee_serializer.is_valid():
        garantieproposee_serializer = GarantieProposeeSerializer(
            get_garantie_offre_ia(garantiedemandee_data), many=True
        )
        return JsonResponse(
            garantieproposee_serializer.data,
            status=status.HTTP_201_CREATED,
            safe=False,
        )
    return JsonResponse(
        garantiedemandee_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_garantie_voyage(request):
    garantiedemandee_data = JSONParser().parse(request)
    # if settings.DEBUG:
    print("JSON de la requête:", garantiedemandee_data)

    garantiedemandee_serializer = DemandeGarantieVoyageSerializer(
        data=garantiedemandee_data
    )
    if garantiedemandee_serializer.is_valid():
        garantieproposee_serializer = GarantieProposeeSerializer(
            get_garantie_offre_voyage(garantiedemandee_data), many=True
        )
        return JsonResponse(
            garantieproposee_serializer.data,
            status=status.HTTP_201_CREATED,
            safe=False,
        )
    return JsonResponse(
        garantiedemandee_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


##########################################################################
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def create_offre_garantie(request):
    enregistrementoffregarantie_data = JSONParser().parse(request)
    # print("JSON de la requête:", enregistrementoffregarantie_data)

    serializer = EnregistrementOffreGarantieSerializer(
        data=enregistrementoffregarantie_data
    )
    if serializer.is_valid():
        (code_retour, msg, qset) = save_offre_garantie(
            enregistrementoffregarantie_data
        )
        if code_retour == 0:
            offregarantie_serializer = OffreGarantieSerializer(qset, many=True)
            return JsonResponse(
                offregarantie_serializer.data,
                status=status.HTTP_201_CREATED,
                safe=False,
            )
        else:
            return JsonResponse(
                {"Statut": "Echec", "Data": msg},
                status=status.HTTP_204_NO_CONTENT,
            )
    return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


##################################################################################
##########################################################################
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def get_garantie_par_produit(request):
    demandegarantie_data = JSONParser().parse(request)
    # print("JSON de la requête:", demandegarantie_data)

    serializer = GarantieParProduitSerializer(data=demandegarantie_data)
    if serializer.is_valid():
        qset = get_garantie_produit(demandegarantie_data)
        offregarantie_serializer = GarantiePourOffreSerializer(qset, many=True)
        return JsonResponse(
            offregarantie_serializer.data,
            status=status.HTTP_201_CREATED,
            safe=False,
        )
    return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


##################################################################################
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_garantie_mrh(request):
    garantiedemandee_data = JSONParser().parse(request)
    # print("JSON de la requête:", garantiedemandee_data)

    garantiedemandee_serializer = DemandeGarantieHabitationSerializer(
        data=garantiedemandee_data
    )
    if garantiedemandee_serializer.is_valid():
        garantieproposee_serializer = GarantieProposeeSerializer(
            get_garantie_offre_mrh(garantiedemandee_data), many=True
        )
        return JsonResponse(
            garantieproposee_serializer.data,
            status=status.HTTP_201_CREATED,
            safe=False,
        )
    return JsonResponse(
        garantiedemandee_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


##################################################################################
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_garantie_rc(request):
    return get_garantie_risques_divers(id_produit=8, request=request)


##################################################################################
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_garantie_mrp(request):
    return get_garantie_risques_divers(id_produit=7, request=request)


def get_garantie_risques_divers(id_produit, request):
    garantiedemandee_data = JSONParser().parse(request)
    garantiedemandee_serializer = DemandeGarantieRisquesDiversSerializer(
        data=garantiedemandee_data
    )
    if garantiedemandee_serializer.is_valid():
        garantieproposee_serializer = GarantieProposeeSerializer(
            get_garantie_offre_risques_divers(
                id_produit, garantiedemandee_data
            ),
            many=True,
        )
        return JsonResponse(
            garantieproposee_serializer.data,
            status=status.HTTP_201_CREATED,
            safe=False,
        )
    return JsonResponse(
        garantiedemandee_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


#####################################################################################
@api_view(["POST"])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_liste_avenant(request):
    avenantdemande_data = JSONParser().parse(request)
    # print("JSON de la requête:", avenantdemande_data)
    avenantdemande_serializer = DemandeAvenantSerializer(
        data=avenantdemande_data
    )
    if avenantdemande_serializer.is_valid():
        try:
            id_produit = int(avenantdemande_data["IdProduit"])
            flotte = bool(avenantdemande_data["Flotte"])
            (msg, qryset) = get_liste_avenant_produit(id_produit, flotte)
            if msg:
                return Response(
                    {"status": "Echec", "data": msg},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = AvenantSerializer(qryset, many=True)
            return JsonResponse(
                serializer.data, status=status.HTTP_201_CREATED, safe=False
            )
        except Exception as error:
            print(error)
            return Response(
                {"status": "Echec", "data": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return JsonResponse(
        avenantdemande_serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


# class AvenantContratView(APIView):
#     permission_classes = [
#         permissions.IsAuthenticated,
#     ]

#     def get(self, request, idcontrat):
#         try:
#             contrat = Contrat.objects.get(pk=idcontrat)
#             if contrat.
#             #formules = AssistanceAutomobile.objects.filter(Q(id_compagnie=idcompagnie))
#             #serializer = AssistanceAutomobileSerializer(formules, many=True)
#         except Exception as error:
#             return Response(
#                 {"status": "Echec", "data": str(error)},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         else:
#             print(serializer.data)
#             return Response(
#                 {"status": "succès", "data": serializer.data},
#                 status=status.HTTP_200_OK,
#             )


#####################################################################################
class OffreParProduitView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, *args, **kwargs):
        idproduit = request.query_params.get("idproduit")
        idtarif = request.query_params.get("idtarif")

        (msg, item) = get_offre_par_produit(
            idproduit=idproduit, idtarif=idtarif
        )
        if not msg:
            serializer = OffreParProduitSerializer(item, many=True)
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


#####################################################################################
class OffreVoyageView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, *args, **kwargs):
        idcompagnie = request.query_params.get("idcompagnie")
        idtarif = request.query_params.get("idtarif")
        idzone = request.query_params.get("idzone")
        (msg, item) = get_offre_voyage(
            idcompagnie=idcompagnie, idtarif=idtarif, idzone=idzone
        )
        if not msg:
            serializer = OffreParProduitSerializer(item, many=True)
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


##################################################################
class OffreSanteParTarifView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idtarif):
        (msg, item) = get_offre_sante_par_tarif(idtarif=idtarif)
        if not msg:
            serializer = OffreSanteParTarifSerializer(item, many=True)
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


##################################################################
class CollegeSanteParOffreView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idoffre):
        (msg, item) = get_college_sante_par_offre(id_offre=idoffre)
        if not msg:
            serializer = CollegeSanteSerializer(item, many=True)
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


###########################################################
class ZoneCouvertureOffreView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idzone):
        (msg, item) = get_zone_couverture_sante(idzone=idzone)
        if not msg:
            serializer = ZoneCouvertureSanteSerializer(item, many=True)
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


###########################################################
class FormuleSecuriteRoutiereView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcompagnie):
        (msg, formules) = get_formule_securite_routiere(
            idcompagnie=idcompagnie
        )
        if not msg:
            serializer = FormuleSecuriteRoutiereParCompagnieSerializer(
                formules, many=True
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


###########################################################
class AssistanceAutomobileView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcompagnie):
        try:
            formules = AssistanceAutomobile.objects.filter(
                Q(id_compagnie=idcompagnie) | Q(id_compagnie=0)
            ).order_by("libelle_option")
            serializer = AssistanceAutomobileSerializer(formules, many=True)
        except Exception as error:
            return Response(
                {"status": "Echec", "data": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            # print(serializer.data)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )


###########################################################
class PaysZoneView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcompagnie):
        try:
            (msg, pays) = get_liste_pays_voyage(idcompagnie)
            if not msg:
                serializer = PaysZoneSerializer(pays, many=True)
                return Response(
                    {"status": "Succès", "data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"status": "Echec", "data": msg},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as error:
            return Response(
                {"status": "Echec", "data": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class TarifParProduitView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idproduit):
        (msg, item) = get_tarif_par_produit(idproduit=idproduit)
        if not msg:
            serializer = TarifParProduitSerializer(item, many=True)
            print(serializer.data)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class TarifVoyageView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idcompagnie):
        (msg, item) = get_tarif_voyage(idcompagnie=idcompagnie)
        if not msg:
            serializer = TarifParProduitSerializer(item, many=True)
            print(serializer.data)
            return Response(
                {"status": "succès", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Echec", "data": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ReductionFlotteViewSet(viewsets.ModelViewSet):
    queryset = ReductionFlotte.objects.all()
    serializer_class = ReductionFlotteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class DelaiAvisEcheanceViewSet(SettingsModelViewSet):
    queryset = DelaiAvisEcheance.objects.all()
    serializer_class = DelaiAvisEcheanceSerializer


class ParametreSiteViewSet(SettingsModelViewSet):
    queryset = ParametreSite.objects.all()
    serializer_class = ParametreSiteSerializer


class SolarScheduleViewSet(SettingsModelViewSet):
    queryset = SolarSchedule.objects.all()
    serializer_class = SolarScheduleSerializer


class IntervalScheduleViewSet(SettingsModelViewSet):
    queryset = IntervalSchedule.objects.all()
    serializer_class = IntervalScheduleSerializer


class ClockedScheduleViewSet(SettingsModelViewSet):
    queryset = ClockedSchedule.objects.all()
    serializer_class = ClockedScheduleSerializer


class CrontabScheduleViewSet(SettingsModelViewSet):
    queryset = CrontabSchedule.objects.all()
    serializer_class = CrontabScheduleSerializer


class PeriodicTaskViewSet(SettingsModelViewSet):
    queryset = PeriodicTask.objects.all()
    serializer_class = PeriodicTaskSerializer


class TypeContratSanteViewSet(SettingsModelViewSet):
    queryset = TypeContratSante.objects.all()
    serializer_class = TypeContratSanteSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]


class IATarifGroupeView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idtarif):
        with connection.cursor() as cursor:
            cursor.execute("SELECT fn_tarif_ia_groupe(%s)", [idtarif])

            row = cursor.fetchone()
            return_value = row[0] if row else None

        # 4. Return to API client
        return Response({"est_tarif_ia_groupe": return_value})


class IATarifPersonnaliseView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, idtarif):
        with connection.cursor() as cursor:
            cursor.execute("SELECT fn_tarif_ia_personnalise(%s)", [idtarif])

            row = cursor.fetchone()
            return_value = row[0] if row else None

        # 4. Return to API client
        return Response({"est_tarif_ia_personnalise": return_value})
