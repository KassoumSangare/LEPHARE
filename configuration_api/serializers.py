from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from rest_framework import serializers

from core.validators import ErrorMessage, validate_contrat_validity_period

from .models import (
    Accessoire,
    AccessoireCourtierParCompagnie,
    Acte,
    AssistanceAutomobile,
    Avenant,
    Banque,
    Branche,
    Carrosserie,
    Categorie,
    CategoriePermis,
    ChoixSousGarantie,
    CollegeSante,
    Commission,
    CommissionProduit,
    Commune,
    Compagnie,
    Continent,
    DelaiAvisEcheance,
    DemandeGarantie,
    DemandeGarantieHabitation,
    DemandeGarantieIa,
    DemandeGarantieRisquesDivers,
    DemandeGarantieVoyage,
    DomaineActiviteRC,
    Energie,
    EnregistrementOffreGarantie,
    FormuleSecuriteRoutiere,
    FormuleSecuriteRoutiereParCompagnie,
    Garantie,
    GarantiePourOffre,
    GarantieProposee,
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
    OffreCollegeSante,
    OffreDetail,
    OffreGarantie,
    OffreParProduit,
    OffreSanteParTarif,
    Option,
    ParametresCalcul,
    ParametreSite,
    Pays,
    PaysZone,
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
    SousGarantieForfait,
    SousGarantieMRH,
    SystemeSecurite,
    Tarif,
    TarifDetail,
    TarifParProduit,
    TauxTaxeGarantieProduit,
    TypeAssure,
    TypeContratSante,
    TypeReduction,
    TypeSouscripteur,
    TypeVehicule,
    UsageHabitation,
    UsageVehicule,
    Utilisateur,
    Ville,
    ZoneCouvertureSante,
    ZoneVoyage,
)


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop("fields", None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class PrimeCalculationInputSerializer(serializers.Serializer):
    id_produit = serializers.IntegerField(required=True)
    id_compagnie = serializers.IntegerField(required=True)
    prime_nette = serializers.DecimalField(
        max_digits=19, decimal_places=4, required=True
    )
    date_effet = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    id_offre = serializers.IntegerField(required=True)


class PrimeCalculationOutputSerializer(serializers.Serializer):
    taux_taxe = serializers.DecimalField(max_digits=5, decimal_places=2)
    accessoire = serializers.DecimalField(max_digits=19, decimal_places=4)
    montant_taxe = serializers.DecimalField(max_digits=19, decimal_places=4)
    prime_totale = serializers.DecimalField(max_digits=19, decimal_places=4)


class SousGarantieSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = SousGarantie
        fields = "__all__"


class GarantieSerializer(serializers.ModelSerializer):
    sousgaranties = SousGarantieSerializer(
        many=True,
        read_only=True,
        fields=("IdSousGarantie", "LibelleSousGarantie"),
    )

    class Meta:
        model = Garantie
        fields = [
            "IdGarantie",
            "CodeGarantie",
            "LibelleGarantie",
            "Active",
            "Ordre",
            "SaisieAuto",
            "SaisieRd",
            "SaisieSante",
            "SaisieTransport",
            "sousgaranties",
        ]


class MenuParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuParent
        fields = "__all__"


class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = "__all__"


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = "__all__"


class GroupeUtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupeUtilisateur
        fields = "__all__"


class GarantieRisqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarantieRisque
        fields = "__all__"


class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = "__all__"


class TarifSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarif
        fields = "__all__"


class TarifDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarifDetail
        fields = "__all__"


class BrancheSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branche
        fields = "__all__"


class RisqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Risque
        fields = "__all__"


class EnergieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Energie
        fields = "__all__"


class AvenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avenant
        fields = (
            "IdAvenant",
            "CodeAvenant",
            "LibelleAvenant",
        )


class CompagnieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compagnie
        fields = (
            "IdCompagnie",
            "RaisonSociale",
            "Adresse1",
            "CodeAsaci",
            "codeacces",
        )


class OffreSerializer(serializers.ModelSerializer):
    OffreBoisee = serializers.IntegerField(read_only=True)

    class Meta:
        model = Offre
        fields = ("IdOffre", "LibelleOffre", "OffreBoisee")


class OffreGarantieSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffreGarantie
        fields = "__all__"


class OffreDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffreDetail
        fields = "__all__"


class CarrosserieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrosserie
        fields = ["IdCarrosserie", "LibelleCarrosserie"]  # fields = "__all__"


class TypeVehiculeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeVehicule
        fields = "__all__"


class QualiteSouscripteurMrhSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualiteSouscripteurMrh
        fields = "__all__"


class TypeSouscripteurSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeSouscripteur
        fields = "__all__"


class TypeAssureSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeAssure
        fields = "__all__"


class ProfessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profession
        fields = "__all__"


class GenreVehiculeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenreVehicule
        fields = "__all__"


class ActeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Acte
        fields = "__all__"


class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = "__all__"


class CommissionProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionProduit
        fields = "__all__"


class TauxTaxeGarantieProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = TauxTaxeGarantieProduit
        fields = "__all__"


class AccessoireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessoire
        fields = "__all__"


class PaysSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pays
        fields = "__all__"


class PaysZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaysZone
        fields = [
            "id_pays",
            "libelle_pays",
            "nationalite",
            "id_zone",
        ]


class ContinentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Continent
        fields = "__all__"


class ZoneVoyageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneVoyage
        fields = "__all__"


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = "__all__"


class VilleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ville
        fields = "__all__"


class CommuneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commune
        fields = "__all__"


class IntermediaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intermediaire
        # fields = '__all__'
        fields = (
            "IdIntermediaire",
            "CodeIntermediaire",
            "LibelleIntermediaire",
        )


class QualiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qualite
        fields = "__all__"


class SecteurActiviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecteurActivite
        fields = "__all__"


class QualiteAyantDroitSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualiteAyantDroit
        fields = "__all__"


class MarqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marque
        fields = "__all__"


class SystemeSecuriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemeSecurite
        fields = "__all__"


class ZoneCouvertureSanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneCouvertureSante
        fields = "__all__"


class ProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produit
        fields = [
            "id_produit",
            "libelle_produit",
        ]


class OffreParProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffreParProduit
        fields = [
            "IdOffre",
            "LibelleOffre",
        ]


class OffreSanteParTarifSerializer(serializers.ModelSerializer):
    # IdZoneCouverture = serializers.IntegerField(required=False)

    class Meta:
        model = OffreSanteParTarif
        fields = [
            "IdOffre",
            "LibelleOffre",
            "IdZoneCouverture",
        ]


class TarifParProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarifParProduit
        fields = [
            "IdTarif",
            "LibelleTarif",
            "CodeCategorie",
        ]


class ModeleVehiculeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeleVehicule
        fields = "__all__"


class ProfessionIaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionIa
        fields = [
            "id",
            "code_profession",
            "libelle_profession",
            "code_classe_assure",
        ]


class UsageVehiculeSerializer(serializers.ModelSerializer):
    Carrosseries = CarrosserieSerializer(many=True, read_only=True)

    class Meta:
        model = UsageVehicule
        fields = ["IdUsage", "LibelleUsage", "Carrosseries"]


class TypeReductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeReduction
        fields = "__all__"


class BanqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banque
        fields = "__all__"


class ModeEncaissementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeEncaissement
        fields = "__all__"


class GarantieProposeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarantieProposee
        fields = [
            "IdGarantie",
            "LibelleGarantie",
            "IdSousGarantie",
            "LibelleSousGarantie",
            "Acquise",
            "Capital",
            "NombrePlace",
            "PrimeAnnuelle",
            "PrimeNette",
            "Taxe",
            "MontantAccessoire",
            "TauxFranchise",
            "FranchiseMinimum",
            "FranchiseMaximum",
            "MontantFranchise",
            "TexteFranchise",
        ]


class DemandeGarantieVoyageSerializer(serializers.ModelSerializer):
    IdOffre = serializers.IntegerField(
        allow_null=True,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'offre",
            field_type="int",
            gender_number="fs",
            field_nature="idt",
        ),
    )
    IdZoneVoyage = serializers.IntegerField(
        allow_null=True,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La destination",
            field_type="int",
            gender_number="fs",
            field_nature="idt",
        ),
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        allow_null=True,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de réduction",
            field_type="decimal",
            gender_number="ms",
        ),
    )

    DateEffet = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date d'effet",
            field_type="date",
            gender_number="fs",
        ),
    )
    DateExpiration = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date d'expiration",
            field_type="date",
            gender_number="fs",
        ),
    )
    DateNaissance = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date de naissance",
            field_type="date",
            gender_number="fs",
        ),
    )
    IdCompagnie = serializers.IntegerField(
        required=False, default=1, allow_null=True
    )
    IdTarif = serializers.IntegerField(
        required=False, default=79, allow_null=True
    )

    def validate(self, data):
        validate_contrat_validity_period(data)
        return data

    def to_internal_value(self, data):
        if "IdCompagnie" in data:
            if not data["IdCompagnie"]:
                data["IdCompagnie"] = 1
        if "IdTarif" in data:
            if not data["IdTarif"]:
                data["IdTarif"] = 79
        return super().to_internal_value(data)

    class Meta:
        model = DemandeGarantieVoyage
        fields = [
            "IdCompagnie",
            "IdOffre",
            "IdTarif",
            "IdZoneVoyage",
            "TauxReduction",
            "DateEffet",
            "DateExpiration",
            "DateNaissance",
        ]


class DemandeAvenantSerializer(serializers.Serializer):
    IdProduit = serializers.IntegerField()
    Flotte = serializers.BooleanField()


class DemandeGarantieHabitationSerializer(serializers.ModelSerializer):
    IdOffre = serializers.IntegerField(
        allow_null=True,
        error_messages={
            "null": "L'offre doit être renseignée.",
            "blank": "L'offre doit être renseignée.",
            "invalid": "L'ID de l'offre doit être un nombre entier.",
        },
    )
    ValeurCapitalLoyer = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "Le montant du capital loyer doit être renseigné.",
            "blank": "Le montant du capital loyer doit être renseigné.",
            "invalid": "Le montant du capital loyer doit être un nombre.",
        },
    )
    ValeurCapitalContenu = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "Le montant du capital contenu doit être renseigné.",
            "blank": "Le montant du capital contenu doit être renseigné.",
            "invalid": "Le montant du capital contenu doit être un nombre.",
        },
    )
    ValeurCapitalObjetPrecieux = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "Le montant du capital objet précieux doit être renseigné.",
            "blank": "Le montant du capital objet précieux doit être renseigné.",
            "invalid": "Le montant du capital objet précieux doit être un nombre.",
        },
    )
    ValeurCapitalMateriel = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "Le montant du capital matériel doit être renseigné.",
            "blank": "Le montant du capital matériel doit être renseigné.",
            "invalid": "Le montant du capital matériel doit être un nombre.",
        },
    )
    ValeurDegatBatiment = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "La valeur du local doit être renseignée.",
            "blank": "La valeur du local doit être renseignée.",
            "invalid": "La valeur du local doit être un nombre.",
        },
    )
    ValeurDegatContenu = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "La valeur du contenu doit être renseignée.",
            "blank": "La valeur du contenu doit être renseignée.",
            "invalid": "La valeur du contenu doit être un nombre.",
        },
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        allow_null=True,
        error_messages={
            "null": "Le taux de réduction doit être renseigné.",
            "blank": "Le taux de réduction doit être renseigné.",
            "invalid": "Le montant du taux de réduction doit être un nombre.",
        },
    )
    Gardien = serializers.BooleanField(
        allow_null=True,
        error_messages={
            "null": "Indiquer la présence ou non d'un gardien.",
            "blank": "Indiquer la présence ou non d'un gardien.",
        },
    )
    Locataire = serializers.BooleanField(
        allow_null=True,
        error_messages={
            "null": "Indiquer si l'assuré(e) est locataire ou non.",
            "blank": "Indiquer si l'assuré(e) est locataire ou non.",
        },
    )

    DateEffet = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date d'effet doit être renseignée.",
            "blank": "La date d'effet doit être renseignée.",
            "invalid": "Mauvais format pour la date d'effet.",
        },
    )
    DateExpiration = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date d'expiration doit être renseignée.",
            "blank": "La date d'expiration doit être renseignée.",
            "invalid": "Mauvais format pour la date d'expiration.",
        },
    )
    IdCompagnie = serializers.IntegerField(
        required=False, default=1, allow_null=True
    )

    def validate(self, data):
        return validate_contrat_validity_period(data)

    def to_internal_value(self, data):
        if "IdCompagnie" in data:
            if not data["IdCompagnie"]:
                data["IdCompagnie"] = 1
        return super().to_internal_value(data)

    class Meta:
        model = DemandeGarantieHabitation
        fields = [
            "IdCompagnie",
            "IdOffre",
            "ValeurCapitalLoyer",
            "ValeurCapitalContenu",
            "ValeurCapitalObjetPrecieux",
            "ValeurCapitalMateriel",
            "ValeurDegatBatiment",
            "ValeurDegatContenu",
            "TauxReduction",
            "DateEffet",
            "DateExpiration",
            "Gardien",
            "Locataire",
        ]


class DemandeGarantieRisquesDiversSerializer(serializers.ModelSerializer):
    IdOffre = serializers.IntegerField(
        allow_null=True,
        error_messages={
            "null": "L'offre doit être renseignée.",
            "blank": "L'offre doit être renseignée.",
            "invalid": "L'ID de l'offre doit être un nombre entier.",
        },
    )
    CapitalDommageCorporel = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        required=False,
        allow_null=True,
        error_messages={
            "null": "Le capital dommage corporel doit être renseigné.",
            "blank": "Le capital dommage corporel doit être renseigné.",
            "invalid": "Le montant du capital dommage corporel doit être un nombre.",
        },
    )
    CapitalDommageMateriel = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        required=False,
        allow_null=True,
        error_messages={
            "null": "Le capital dommage matériel doit être renseigné.",
            "blank": "Le capital dommage matériel doit être renseigné.",
            "invalid": "Le montant du capital dommage matériel doit être un nombre.",
        },
    )
    CapitalIntoxicationAlimentaire = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        required=False,
        allow_null=True,
        error_messages={
            "null": "Le capital intoxication alimentaire doit être renseigné.",
            "blank": "Le capital intoxication alimentaire doit être renseigné.",
            "invalid": "Le montant du capital intoxication alimentaire doit être un nombre.",
        },
    )
    AssiettePrime = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        required=False,
        allow_null=True,
        error_messages={
            "null": "L'assiette de prime doit être renseignée.",
            "blank": "L'assiette de prime doit être renseignée.",
            "invalid": "Le montant de l'assiette de prime doit être un nombre.",
        },
    )
    TauxPrime = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        error_messages={
            "null": "Le taux de prime doit être renseigné.",
            "blank": "Le taux de prime doit être renseigné.",
            "invalid": "Le montant du taux de prime doit être un nombre.",
        },
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        error_messages={
            "null": "Le taux de réduction doit être renseigné.",
            "blank": "Le taux de réduction doit être renseigné.",
            "invalid": "Le montant du taux de réduction doit être un nombre.",
        },
    )

    DateEffet = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date d'effet doit être renseignée.",
            "blank": "La date d'effet doit être renseignée.",
            "invalid": "Mauvais format pour la date d'effet.",
        },
    )
    DateExpiration = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date d'expiration doit être renseignée.",
            "blank": "La date d'expiration doit être renseignée.",
            "invalid": "Mauvais format pour la date d'expiration.",
        },
    )
    IdCompagnie = serializers.IntegerField(
        required=False, default=1, allow_null=True
    )
    IdDevis = serializers.IntegerField(
        required=False, default=0, allow_null=True
    )

    def validate(self, data):
        validate_contrat_validity_period(data)
        return data

    def to_internal_value(self, data):
        if "IdCompagnie" in data:
            if not data["IdCompagnie"]:
                data["IdCompagnie"] = 1
        if "IdDevis" in data:
            if not data["IdDevis"]:
                data["IdDevis"] = 0
        return super().to_internal_value(data)

    class Meta:
        model = DemandeGarantieRisquesDivers
        fields = [
            "IdCompagnie",
            "IdOffre",
            "CapitalDommageCorporel",
            "CapitalDommageMateriel",
            "CapitalIntoxicationAlimentaire",
            "AssiettePrime",
            "TauxReduction",
            "TauxPrime",
            "DateEffet",
            "DateExpiration",
            "IdDevis",
        ]


class DemandeGarantieIaSerializer(serializers.ModelSerializer):
    IdOffre = serializers.IntegerField(
        allow_null=True,
        error_messages={
            "null": "L'offre doit être renseignée.",
            "blank": "L'offre doit être renseignée.",
            "invalid": "L'ID de l'offre doit être un nombre entier.",
        },
    )
    CapitalDeces = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "Le capital décès doit être renseigné.",
            "blank": "Le capital décès doit être renseigné.",
            "invalid": "Le montant du capital décès doit être un nombre.",
        },
    )
    CapitalInfirmite = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "Le capital infirmité doit être renseigné.",
            "blank": "Le capital infirmité doit être renseigné.",
            "invalid": "Le montant du capital infirmité doit être un nombre.",
        },
    )
    CapitalFraisTraitement = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "Le capital frais de traitement doit être renseigné.",
            "blank": "Le capital frais de traitement doit être renseigné.",
            "invalid": "Le montant du capital frais de traitement doit être un nombre.",
        },
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        allow_null=True,
        error_messages={
            "null": "Le taux de réduction commerciale doit être renseigné.",
            "blank": "Le taux de réduction commerciale doit être renseigné.",
            "invalid": "Le montant du taux de réduction commerciale doit être un nombre.",
        },
    )
    CodeActivite = serializers.CharField(
        max_length=3,
        allow_null=True,
        error_messages={
            "null": "L'activité doit être renseignée.",
            "blank": "L'activité doit être renseignée.",
        },
    )
    DateEffet = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date d'effet doit être renseignée.",
            "blank": "La date d'effet doit être renseignée.",
            "invalid": "Format invalide pour la date d'effet.",
        },
    )
    DateExpiration = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date d'expiration doit être renseignée.",
            "blank": "La date d'expiration doit être renseignée.",
            "invalid": "Format invalide pour la date d'expiration.",
        },
    )
    DateNaissance = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date de naissance doit être renseignée.",
            "blank": "La date de naissance doit être renseignée.",
            "invalid": "Format invalide pour la date de naissance.",
        },
    )
    IdCompagnie = serializers.IntegerField(
        required=False, default=1, allow_null=True
    )
    PrimeNette = serializers.DecimalField(
        required=False,
        default=0,
        allow_null=True,
        max_digits=19,
        decimal_places=4,
    )
    Accessoire = serializers.DecimalField(
        required=False,
        default=0,
        allow_null=True,
        max_digits=19,
        decimal_places=4,
    )

    def validate(self, data):
        validate_contrat_validity_period(data)
        return data

    def to_internal_value(self, data):
        if "IdCompagnie" in data:
            if not data["IdCompagnie"]:
                data["IdCompagnie"] = 1
        if "PrimeNette" in data:
            if not data["PrimeNette"]:
                data["PrimeNette"] = 0
        if "Accessoire" in data:
            if not data["Accessoire"]:
                data["Accessoire"] = 0
        return super().to_internal_value(data)

    class Meta:
        model = DemandeGarantieIa
        fields = [
            "IdCompagnie",
            "IdOffre",
            "CapitalDeces",
            "CapitalInfirmite",
            "CapitalFraisTraitement",
            "TauxReduction",
            "DateEffet",
            "DateExpiration",
            "CodeActivite",
            "DateNaissance",
            "PrimeNette",
            "Accessoire",
        ]


class DemandeGarantieSerializer(serializers.ModelSerializer):
    IdOffre = serializers.IntegerField(
        allow_null=True,
        error_messages={
            "null": "L'offre doit être renseignée.",
            "blank": "L'offre doit être renseignée.",
            "invalid": "L'ID de l'offre doit être un nombre entier.",
        },
    )
    IdTarif = serializers.IntegerField(
        allow_null=True,
        error_messages={
            "null": "La catégorie doit être renseignée.",
            "blank": "La catégorie doit être renseignée.",
            "invalid": "L'ID de la catégorie doit être un nombre entier.",
        },
    )
    ValNeuve = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "La valeur neuve doit être renseignée.",
            "blank": "La valeur neuve doit être renseignée.",
            "invalid": "Le montant de la valeur neuve doit être un nombre.",
        },
    )
    ValVenale = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "La valeur venale doit être renseignée.",
            "blank": "La valeur venale doit être renseignée.",
            "invalid": "Le montant de la valeur venale doit être un nombre.",
        },
    )
    ValAccessoire = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "La valeur accessoire doit être renseignée.",
            "blank": "La valeur accessoire doit être renseignée.",
            "invalid": "Le montant de la valeur accessoire doit être un nombre.",
        },
    )
    Puissance = serializers.IntegerField(
        allow_null=True,
        error_messages={
            "null": "La puissance fiscale doit être renseignée.",
            "blank": "La puissance fiscale doit être renseignée.",
            "invalid": "La puissance fiscale doit être un nombre entier.",
        },
    )
    CodeCarburant = serializers.IntegerField(
        allow_null=True,
        error_messages={
            "null": "L'énergie doit être renseignée.",
            "blank": "L'énergie doit être renseignée.",
            "invalid": "L'ID de l'énergie doit être un nombre entier.",
        },
    )
    Tonnage = serializers.IntegerField(
        allow_null=True,
        error_messages={
            "null": "La charge utile doit être renseignée.",
            "blank": "La charge utile doit être renseignée.",
            "invalid": "La valeur de la charge utile doit être un nombre entier.",
        },
    )
    TauxReduction = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "Le taux de réduction commerciale doit être renseigné.",
            "blank": "Le taux de réduction commerciale doit être renseigné.",
            "invalid": "La valeur du taux de réduction commerciale doit être un nombre.",
        },
    )
    CodeAlarme = serializers.IntegerField(
        allow_null=True,
        error_messages={
            "null": "Le système de sécurité doit être renseigné.",
            "blank": "Le système de sécurité doit être renseigné.",
            "invalid": "Le code du système de sécurité doit être un nombre entier.",
        },
    )
    Bns = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        allow_null=True,
        error_messages={
            "null": "Le taux de réduction BNS doit être renseigné.",
            "blank": "Le taux de réduction BNS doit être renseigné.",
            "invalid": "La valeur du taux de réduction BNS  doit être un nombre.",
        },
    )

    DateEffet = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "blank": "La date d'effet du contrat doit être renseignée",
            "null": "La date d'effet du contrat doit être renseignée",
        },
    )
    DateExpiration = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "blank": "La date d'expiration du contrat doit être renseignée",
            "null": "La date d'expiration du contrat doit être renseignée",
        },
    )
    IdCompagnie = serializers.IntegerField(
        required=False, default=1, allow_null=True
    )
    DateMec = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        required=False,
        allow_null=True,
    )
    RemorqueAttelee = serializers.BooleanField(
        required=False, default=False, allow_null=True
    )
    CodeFormuleSecuriteRoutiere = serializers.CharField(
        max_length=80, required=False, default="", allow_null=True
    )
    IdOptionAssistance = serializers.IntegerField(
        required=False, default=0, allow_null=True
    )
    NombrePlace = serializers.IntegerField(
        required=False, default=1, allow_null=True
    )

    CodeUsage = serializers.IntegerField(
        required=False, default=0, allow_null=True
    )
    CarburantAutreMatiere = serializers.BooleanField(
        required=False, default=False, allow_null=True
    )
    TransportEleves = serializers.BooleanField(
        required=False, default=False, allow_null=True
    )
    TransportEmployes = serializers.BooleanField(
        required=False, default=False, allow_null=True
    )
    TansportPassagerSupplementaire = serializers.BooleanField(
        required=False, default=False, allow_null=True
    )
    NsiaAutoPlus = serializers.BooleanField(
        required=False, default=False, allow_null=True
    )

    def validate(self, data):
        id_offre = data.get("IdOffre")
        if id_offre is None:
            raise serializers.ValidationError(
                {"ID Offre": "L'offre doit être renseignée."}
            )

        id_tarif = data.get("IdTarif")
        if id_tarif is None:
            raise serializers.ValidationError(
                {"ID Tarif": "La catégorie doit être renseignée."}
            )

        val_neuve = data.get("ValNeuve")
        if val_neuve is None:
            raise serializers.ValidationError(
                {"Valeur Neuve": "La valeur neuve doit être renseignée."}
            )

        val_venale = data.get("ValVenale")
        if val_venale is None:
            raise serializers.ValidationError(
                {"Valeur Venale": "La valeur venale doit être renseignée."}
            )
        val_accessoire = data.get("ValAccessoire")
        if val_accessoire is None:
            raise serializers.ValidationError(
                {
                    "Valeur Accessoire": "La valeur accessoire doit être renseignée."
                }
            )

        puissance_fiscale = data.get("Puissance")
        if puissance_fiscale is None:
            raise serializers.ValidationError(
                {
                    "Puissance Fiscale": "La puissance fiscale doit être renseignée."
                }
            )

        code_carburant = data.get("CodeCarburant")
        if code_carburant is None:
            raise serializers.ValidationError(
                {"Energie": "L'énerge doit être renseignée."}
            )

        tonnage = data.get("Tonnage")
        if tonnage is None:
            raise serializers.ValidationError(
                {"Charge Utile": "La charge utile doit être renseignée."}
            )

        taux_reduction = data.get("TauxReduction")
        if taux_reduction is None:
            raise serializers.ValidationError(
                {
                    "Taux Réduction": "Le taux de réduction commerciale doit être renseigné."
                }
            )

        code_alarme = data.get("CodeAlarme")
        if code_alarme is None:
            raise serializers.ValidationError(
                {
                    "Système Sécurité": "Le système de sécurité doit être renseigné."
                }
            )
        reduction_bns = data.get("Bns")
        if reduction_bns is None:
            raise serializers.ValidationError(
                {"BNS": "Le taux de réduction BNS doit être renseigné."}
            )

        if val_accessoire > val_venale:
            raise serializers.ValidationError(
                {
                    "Valeur Accessoire": "La valeur accessoire ne peut être supérieure à la valeur venale."
                }
            )

        if val_accessoire > val_neuve:
            raise serializers.ValidationError(
                {
                    "Valeur Accessoire": "La valeur accessoire ne peut être supérieure à la valeur neuve."
                }
            )

        if val_venale > val_neuve:
            raise serializers.ValidationError(
                {
                    "Valeur Venale": "La valeur venale ne peut être supérieure à la valeur neuve."
                }
            )

        return data

    def to_internal_value(self, data):
        if "IdCompagnie" in data:
            if not data["IdCompagnie"]:
                data["IdCompagnie"] = 1
        if "DateMec" in data:
            if not data["DateMec"]:
                data["DateMec"] = None
        if "RemorqueAttelee" in data:
            if not data["RemorqueAttelee"]:
                data["RemorqueAttelee"] = False
        if "CodeFormuleSecuriteRoutiere" in data:
            if data["CodeFormuleSecuriteRoutiere"] == "":
                data["CodeFormuleSecuriteRoutiere"] = None
        if "IdOptionAssistance" in data:
            if not data["IdOptionAssistance"]:
                data["IdOptionAssistance"] = 0
        if "NombrePlace" in data:
            if not data["NombrePlace"]:
                data["NombrePlace"] = 1
        if "CodeUsage" in data:
            if not data["CodeUsage"]:
                data["CodeUsage"] = 0
        if "CarburantAutreMatiere" in data:
            if not data["CarburantAutreMatiere"]:
                data["CarburantAutreMatiere"] = False
        if "TransportEleves" in data:
            if not data["TransportEleves"]:
                data["TransportEleves"] = False
        if "TransportEmployes" in data:
            if not data["TransportEmployes"]:
                data["TransportEmployes"] = False
        if "TansportPassagerSupplementaire" in data:
            if not data["TansportPassagerSupplementaire"]:
                data["TansportPassagerSupplementaire"] = False
        if "NsiaAutoPlus" in data:
            if not data["NsiaAutoPlus"]:
                data["NsiaAutoPlus"] = False
        return super().to_internal_value(data)

    class Meta:
        model = DemandeGarantie
        fields = [
            "IdCompagnie",
            "IdOffre",
            "IdTarif",
            "ValNeuve",
            "ValVenale",
            "ValAccessoire",
            "Puissance",
            "CodeCarburant",
            "Tonnage",
            "TauxReduction",
            "CodeAlarme",
            "DateEffet",
            "DateExpiration",
            "Bns",
            "DateMec",
            "RemorqueAttelee",
            "CodeFormuleSecuriteRoutiere",
            "IdOptionAssistance",
            "NombrePlace",
            "CodeUsage",
            "CarburantAutreMatiere",
            "TransportEleves",
            "TransportEmployes",
            "TansportPassagerSupplementaire",
            "NsiaAutoPlus",
        ]


class CategoriePermisSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriePermis
        fields = "__all__"


class AccessoireCourtierParCompagnieSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessoireCourtierParCompagnie
        fields = "__all__"


class CollegeSanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollegeSante
        fields = "__all__"


class OffreCollegeSanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffreCollegeSante
        fields = "__all__"


class LienJuridiqueSanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LienJuridiqueSante
        fields = "__all__"


class ChoixSousGarantieSerializer(serializers.Serializer):
    idgarantie = serializers.IntegerField(required=True)
    idsousgarantie = serializers.IntegerField(required=True)
    tauxfranchise = serializers.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        default=0,
        allow_null=True,
    )
    franchiseminimum = serializers.DecimalField(
        required=False,
        max_digits=19,
        decimal_places=4,
        default=0,
        allow_null=True,
    )
    franchisemaximum = serializers.DecimalField(
        required=False,
        max_digits=19,
        decimal_places=4,
        default=0,
        allow_null=True,
    )

    def create(self, validated_data):
        return ChoixSousGarantie(**validated_data)

    def update(self, instance, validated_data):
        instance.idgarantie = validated_data.get(
            "idgarantie", instance.idgarantie
        )
        instance.idsousgarantie = validated_data.get(
            "idsousgarantie", instance.idsousgarantie
        )
        instance.tauxfranchise = validated_data.get(
            "tauxfranchise", instance.tauxfranchise
        )
        instance.franchiseminimum = validated_data.get(
            "franchiseminimum", instance.franchiseminimum
        )
        instance.franchisemaximum = validated_data.get(
            "franchisemaximum", instance.franchisemaximum
        )

        return instance


class EnregistrementOffreGarantieSerializer(serializers.Serializer):
    idcompagnie = serializers.IntegerField(required=True)
    idproduit = serializers.IntegerField(required=True)
    idoffre = serializers.IntegerField(required=True)

    liste_sous_garantie = serializers.ListField(
        required=True,
        child=ChoixSousGarantieSerializer(),
        min_length=1,
        max_length=30,
    )

    def create(self, validated_data):
        return EnregistrementOffreGarantie(**validated_data)

    def update(self, instance, validated_data):
        instance.idcompagnie = validated_data.get(
            "idcompagnie", instance.idcompagnie
        )
        instance.idproduit = validated_data.get(
            "idproduit", instance.idproduit
        )
        instance.idoffre = validated_data.get("idoffre", instance.idoffre)
        instance.liste_sous_garantie = validated_data.get(
            "liste_sous_garantie", instance.liste_sous_garantie
        )

        return instance


class GarantieParProduitSerializer(serializers.Serializer):
    idcompagnie = serializers.IntegerField(required=True)
    idproduit = serializers.IntegerField(required=True)
    idoffre = serializers.IntegerField(required=True)


class GarantiePourOffreSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarantiePourOffre
        exclude = ["id"]


class ReductionFlotteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReductionFlotte
        exclude = ["taux_reduction_tarifaire"]
        # depth = 1


class FormuleSecuriteRoutiereSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormuleSecuriteRoutiere
        fields = "__all__"


class FormuleSecuriteRoutiereParCompagnieSerializer(serializers.Serializer):
    idcompagnie = serializers.IntegerField(required=True)
    codeformule = serializers.CharField(required=True, max_length=80)
    libellelongformule = serializers.CharField(required=True, max_length=100)

    def create(self, validated_data):
        return FormuleSecuriteRoutiereParCompagnie(**validated_data)

    def update(self, instance, validated_data):
        instance.idcompagnie = validated_data.get(
            "idcompagnie", instance.idcompagnie
        )
        instance.codeformule = validated_data.get(
            "codeformule", instance.codeformule
        )
        instance.libellelongformule = validated_data.get(
            "libellelongformule", instance.libellelongformule
        )

        return instance


class AssistanceAutomobileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistanceAutomobile
        fields = ("id_option", "id_compagnie", "libelle_option")


class DelaiAvisEcheanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DelaiAvisEcheance
        fields = "__all__"


class ParametreSiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParametreSite
        fields = "__all__"


# Celery Serializers
class SolarScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolarSchedule
        fields = "__all__"


class IntervalScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntervalSchedule
        fields = "__all__"


class ClockedScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClockedSchedule
        fields = "__all__"


class CrontabScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrontabSchedule
        fields = "__all__"


class PeriodicTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodicTask
        fields = "__all__"


class TypeContratSanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeContratSante
        fields = "__all__"


# ============================================================================
# SERIALIZERS POUR LES MODÈLES MRH DE BASE (LECTURE)
# ============================================================================


class UsageHabitationSerializer(serializers.ModelSerializer):
    """Serializer pour les usages habitation (lecture seule)"""

    nombre_sous_garanties_obligatoires = serializers.SerializerMethodField()
    nombre_sous_garanties_optionnelles = serializers.SerializerMethodField()
    libelle_offre = serializers.SerializerMethodField()

    class Meta:
        model = UsageHabitation
        fields = [
            "code",
            "libelle",
            "qualite_assure",
            "description",
            "offre",
            "libelle_offre",
            "actif",
            "nombre_sous_garanties_obligatoires",
            "nombre_sous_garanties_optionnelles",
        ]
        read_only_fields = fields

    def get_nombre_sous_garanties_obligatoires(self, obj):
        """Compte les sous-garanties obligatoires pour cet usage"""
        return obj.sous_garanties_liees.filter(
            obligatoire=True, actif=True
        ).count()

    def get_nombre_sous_garanties_optionnelles(self, obj):
        """Compte les sous-garanties optionnelles pour cet usage"""
        return obj.sous_garanties_liees.filter(
            obligatoire=False, actif=True
        ).count()

    def get_libelle_offre(self, obj):
        if obj.offre:
            return obj.offre.LibelleOffre


class SousGarantieMRHSerializer(serializers.ModelSerializer):
    """Serializer pour les sous-garanties MRH (lecture seule)"""

    code_sous_garantie_std = serializers.SerializerMethodField()
    id_sous_garantie_std = serializers.SerializerMethodField()

    class Meta:
        model = SousGarantieMRH
        fields = [
            "code",
            "libelle",
            "type",
            "description",
            "code_sous_garantie_std",
            "id_sous_garantie_std",
            "actif",
        ]
        read_only_fields = fields

    def get_code_sous_garantie_std(self, obj):
        """Retourne le code de la garantie standard"""
        return obj.get_code_sous_garantie_std()

    def get_id_sous_garantie_std(self, obj):
        """Retourne l'ID de la garantie standard"""
        return obj.get_id_sous_garantie_std()


class SousGarantieForfaitSerializer(serializers.ModelSerializer):
    """Serializer pour les sous-garanties à forfait"""

    sous_garantie_code = serializers.CharField(
        source="sous_garantie.code", read_only=True
    )
    sous_garantie_libelle = serializers.CharField(
        source="sous_garantie.libelle", read_only=True
    )

    class Meta:
        model = SousGarantieForfait
        fields = [
            "sous_garantie_code",
            "sous_garantie_libelle",
            "prime_nette",
            "description",
        ]
        read_only_fields = fields


class OptionSerializer(serializers.ModelSerializer):
    """Serializer pour les options (lecture seule)"""

    sous_garantie_cible_libelle = serializers.CharField(
        source="sous_garantie_cible.libelle", read_only=True, allow_null=True
    )

    class Meta:
        model = Option
        fields = [
            "code",
            "libelle",
            "description",
            "type_option",
            "type_ajustement",
            "sous_garantie_cible",
            "sous_garantie_cible_libelle",
            "taux_ajustement",
            "montant_forfait",
            "signe_ajustement",
        ]
        read_only_fields = fields


class ParametresCalculSerializer(serializers.ModelSerializer):
    """Serializer pour les paramètres de calcul (lecture seule)"""

    usage_libelle = serializers.CharField(
        source="usage.libelle", read_only=True
    )

    class Meta:
        model = ParametresCalcul
        fields = [
            "usage",
            "usage_libelle",
            "coeff_valeur_batiment",
            "coeff_valeur_contenu",
            "coeff_loyer",
            "coeff_capital_rvt",
            "coeff_reduction",
            "forfait_fixe",
            "param_valeur_batiment_requis",
            "param_valeur_contenu_requis",
            "param_loyer_requis",
            "param_capital_rvt_requis",
            "formule_texte",
        ]
        read_only_fields = fields


class DomaineActiviteRCSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomaineActiviteRC
        fields = ["id_domaine_activite", "libelle"]
        read_only_fields = ["id_domaine_activite"]
