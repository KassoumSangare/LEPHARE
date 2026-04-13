from rest_framework import serializers
from .models import *
from core.serializers import EnregistrementDevisBaseSerializer
from core.validators import ErrorMessage


class FilialeSanteSerializer(serializers.ModelSerializer):
    devis_filiale = serializers.IntegerField(source="devis", read_only=True)
    police_filiale = serializers.CharField(source="police", read_only=True)
    filiale_active = serializers.BooleanField(source="actif", read_only=True)
    date_emission = serializers.DateField(source="datesouscription", read_only=True)
    date_effet = serializers.DateField(source="dateeffet", read_only=True)
    date_expiration = serializers.DateField(source="dateexpiration", read_only=True)
    date_maj = serializers.DateTimeField(source="datemaj", read_only=True)
    nom_filiale = serializers.CharField(source="nomfiliale", read_only=True)

    class Meta:
        model = FilialeSante
        fields = (
            "idfiliale",
            "devis_filiale",
            "college",
            "offresante",
            "zonecouverture",
            "nom_filiale",
            "date_emission",
            "date_effet",
            "date_expiration",
            "source",
            "police_filiale",
            "filiale_active",
            "date_maj",
        )


class FilialeSanteSaisieSerializer(serializers.ModelSerializer):
    date_emission = serializers.DateField(
        source="datesouscription",
        required=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    date_effet = serializers.DateField(
        source="dateeffet",
        required=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    date_expiration = serializers.DateField(
        source="dateexpiration",
        required=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )

    class Meta:
        model = FilialeSante
        fields = (
            "idfiliale",
            "devis",
            "college",
            "offresante",
            "zonecouverture",
            "date_emission",
            "date_effet",
            "date_expiration",
            "source",
        )


class AdherentSerializer(serializers.ModelSerializer):
    devis_adherent = serializers.IntegerField(source="devis", read_only=True)
    date_naissance = serializers.DateField(
        source="datenaissance",
        required=False,
        allow_null=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    date_adhesion = serializers.DateField(
        source="dateadhesion",
        read_only=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    date_sortie = serializers.DateField(
        source="datesortie",
        read_only=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    adherent_actif = serializers.BooleanField(
        source="actif",
        read_only=True,
    )
    date_maj = serializers.DateTimeField(source="datemaj", read_only=True)
    datedebutconsommation = serializers.DateField(
        source="debutconsommation",
        required=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    cni = serializers.CharField(
        source="numerocni", required=False, default="", allow_null=True
    )
    adresse = serializers.CharField(
        source="adresseadherent", required=False, default="", allow_null=True
    )
    matricule = serializers.CharField(
        source="matriculeadherent",
        required=False,
        max_length=50,
        default="",
        allow_null=True,
    )
    groupesanguin = serializers.CharField(
        source="groupesanguinadherent",
        max_length=3,
        required=False,
        default="",
        allow_null=True,
    )
    nombrepathologie = serializers.IntegerField(
        source="nombrepathologie_adherent", required=False, default=0, allow_null=True
    )
    numerocmu = serializers.CharField(
        source="numerocmu_adherent",
        required=False,
        default="",
        allow_null=True,
    )

    class Meta:
        model = Adherent
        fields = (
            "idadherent",
            "filiale",
            "nom",
            "prenom",
            "sexe",
            "cni",
            "vip",
            "adresse",
            "mobile1",
            "mobile2",
            "email",
            "date_naissance",
            "date_adhesion",
            "date_sortie",
            "adherent_actif",
            "date_maj",
            "devis_adherent",
            "datedebutconsommation",
            "matricule",
            "groupesanguin",
            "nombrepathologie",
            "numerocmu",
            "surprimeappliquee",
            "montantsurprime",
        )


class AdherentSaisieSerializer(serializers.ModelSerializer):
    dateeffet = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    datenaissance = serializers.DateField(
        source="datenaissanceadherent",
        required=False,
        allow_null=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    datedebutconsommation = serializers.DateField(
        source="debutconsommation",
        required=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    cni = serializers.CharField(
        source="numerocni", required=False, default="", allow_null=True
    )
    fichierpiece = serializers.FileField(
        source="fichier_piece", required=False, allow_null=True
    )
    adresse = serializers.CharField(
        source="adresseadherent", required=False, default="", allow_null=True
    )
    matricule = serializers.CharField(
        source="matriculeadherent",
        required=False,
        default="",
        max_length=50,
        allow_null=True,
    )
    groupesanguin = serializers.CharField(
        source="groupesanguinadherent",
        max_length=3,
        required=False,
        default="",
        allow_null=True,
    )
    nombrepathologie = serializers.IntegerField(
        source="nombrepathologie_adherent", required=False, default=0, allow_null=True
    )
    numerocmu = serializers.CharField(
        source="numerocmu_adherent",
        required=False,
        default="",
        allow_null=True,
    )

    def to_internal_value(self, data):
        if "cni" in data:
            if data["cni"] == "":
                data["cni"] = None
        if "numerocmu" in data:
            if data["numerocmu"] == "":
                data["numerocmu"] = None
        if "adresse" in data:
            if data["adresse"] == "":
                data["adresse"] = None
        if "groupesanguin" in data:
            if data["groupesanguin"] == "":
                data["groupesanguin"] = None
            if (
                data["groupesanguin"]
                and str(data["groupesanguin"]).upper().strip() == "INFO NON DISPONIBLE"
            ):
                data["groupesanguin"] = "NS"
        if "datenaissance" in data:
            if not data["datenaissance"] and str(data["datenaissance"]) == "":
                data["datenaissance"] = None
        return super().to_internal_value(data)

    class Meta:
        model = Adherent
        fields = (
            "idadherent",
            "filiale",
            "nom",
            "prenom",
            "sexe",
            "cni",
            "fichierpiece",
            "vip",
            "adresse",
            "mobile1",
            "mobile2",
            "email",
            "devis",
            "datenaissance",
            "dateeffet",
            "datedebutconsommation",
            "matricule",
            "nombrepathologie",
            "numerocmu",
            "groupesanguin",
            "surprimeappliquee",
            "montantsurprime",
        )


class AffilieSerializer(serializers.ModelSerializer):
    date_adhesion = serializers.DateField(
        source="dateadhesion", read_only=True, required=False
    )
    date_sortie = serializers.DateField(
        source="datesortie", read_only=True, required=False
    )
    date_controle = serializers.DateField(
        source="datectrl", read_only=True, required=False
    )
    carte_vigueur = serializers.BooleanField(
        source="carte_en_vigueur", read_only=True, required=False
    )
    ancien_matricule = serializers.CharField(
        source="anc_matricule", read_only=True, required=False
    )
    date_derniere_demande = serializers.DateField(
        source="date_dern_demande", read_only=True, required=False
    )
    affilie_actif = serializers.BooleanField(
        source="actif", read_only=True, required=False
    )
    date_maj = serializers.DateTimeField(
        source="datemaj", read_only=True, required=False
    )
    devis_affilie = serializers.IntegerField(
        source="devis", read_only=True, required=False
    )

    prime_annuelle = serializers.DecimalField(
        source="primeannuelle",
        read_only=True,
        required=False,
        max_digits=19,
        decimal_places=4,
    )
    datenaissance = serializers.DateField(
        source="date_naissance",
        required=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    datedebutconsommation = serializers.DateField(
        source="debutconsommation",
        required=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    observations = serializers.CharField(
        source="observations_affilie", required=False, default="", allow_null=True
    )
    cni = serializers.CharField(
        source="numerocni", required=False, default="", allow_null=True
    )
    groupesanguin = serializers.CharField(
        source="groupesanguinaffilie", required=False, default="", allow_null=True
    )
    mobile1 = serializers.CharField(
        source="mobile1_affilie", required=False, default="", allow_null=True
    )
    mobile2 = serializers.CharField(
        source="mobile2_affilie", required=False, default="", allow_null=True
    )
    nombrepathologie = serializers.IntegerField(
        source="nombrepathologie_affilie", required=False, default=0, allow_null=True
    )
    numerocmu = serializers.CharField(
        source="numerocmu_affilie",
        required=False,
        default="",
        allow_null=True,
    )

    class Meta:
        model = Affilie
        fields = (
            "idaffilie",
            "adherent",
            "lien",
            "nom",
            "prenom",
            "cni",
            "datenaissance",
            "mobile1",
            "mobile2",
            "date_adhesion",
            "date_sortie",
            "certificat",
            "date_controle",
            "matricule",
            "carte_vigueur",
            "ancien_matricule",
            "date_derniere_demande",
            "observations",
            "handicape",
            "nombrepathologie",
            "numerocmu",
            "sexe",
            "affilie_actif",
            "prime_annuelle",
            "date_maj",
            "devis_affilie",
            "datedebutconsommation",
            "groupesanguin",
            "surprimeappliquee",
            "montantsurprime",
        )


class AffilieSaisieSerializer(serializers.ModelSerializer):
    dateeffet = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    datenaissance = serializers.DateField(
        source="date_naissance",
        required=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    datedebutconsommation = serializers.DateField(
        source="debutconsommation",
        required=True,
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    observations = serializers.CharField(
        source="observations_affilie", required=False, default="", allow_null=True
    )
    cni = serializers.CharField(
        source="numerocni", required=False, default="", allow_null=True
    )
    fichierpiece = serializers.FileField(
        source="fichier_piece", required=False, allow_null=True
    )
    groupesanguin = serializers.CharField(
        source="groupesanguinaffilie", required=False, default="", allow_null=True
    )
    mobile1 = serializers.CharField(
        source="mobile1_affilie", required=False, default="", allow_null=True
    )
    mobile2 = serializers.CharField(
        source="mobile2_affilie", required=False, default="", allow_null=True
    )
    nombrepathologie = serializers.IntegerField(
        source="nombrepathologie_affilie", required=False, default=0, allow_null=True
    )
    numerocmu = serializers.CharField(
        source="numerocmu_affilie",
        required=False,
        default="",
        allow_null=True,
    )

    def to_internal_value(self, data):
        if "groupesanguin" in data:
            if (
                data["groupesanguin"]
                and str(data["groupesanguin"]).upper().strip() == "INFO NON DISPONIBLE"
            ):
                data["groupesanguin"] = "NS"

        return super().to_internal_value(data)

    class Meta:
        model = Affilie
        fields = (
            "nom",
            "prenom",
            "datenaissance",
            "mobile1",
            "mobile2",
            "sexe",
            "cni",
            "fichierpiece",
            "lien",
            "dateeffet",
            "certificat",
            "matricule",
            "observations",
            "handicape",
            "nombrepathologie",
            "numerocmu",
            "datedebutconsommation",
            "idaffilie",
            "adherent",
            "devis",
            "groupesanguin",
            "surprimeappliquee",
            "montantsurprime",
        )


class ImportationAffilieSerializer(serializers.Serializer):
    fichier_excel = serializers.FileField(max_length=None, allow_empty_file=False)
    id_devis = serializers.IntegerField(default=0)
    date_effet = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    id_filiale = serializers.IntegerField()


#################################################"EnregistrementDevisSanteSerializer"
class EnregistrementDevisSanteSerializer(EnregistrementDevisBaseSerializer):
    PrimeFamille = serializers.DecimalField(
        max_digits=19, decimal_places=4, required=False, default=0, allow_null=True
    )
    PrimeAffilie = serializers.DecimalField(
        max_digits=19, decimal_places=4, required=False, default=0, allow_null=True
    )
    PrimeGlobale = serializers.DecimalField(
        max_digits=19, decimal_places=4, required=False, default=0, allow_null=True
    )
    MontantSuprime = serializers.DecimalField(
        max_digits=19, decimal_places=4, required=False, default=0, allow_null=True
    )
    MontantAccessoireManuel = serializers.DecimalField(
        max_digits=19, decimal_places=4, required=False, default=0, allow_null=True
    )
    TypeContrat = serializers.IntegerField(required=False, default=1, allow_null=True)
    GestionnaireSante = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )
    TauxReduction = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, default=0, allow_null=True
    )
    TauxReductionCommerciale = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, default=0, allow_null=True
    )
    IdDevis = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'ID du devis", field_type="int", gender_number="ms"
        )
    )
    IdDuree = serializers.IntegerField(required=False, default=1, allow_null=True)
    NumeroPoliceCompagnie = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )

    def to_internal_value(self, data):
        if "IdDuree" in data:
            if not data["IdDuree"]:
                data["IdDuree"] = 1
        if "MontantSuprime" in data:
            if not data["MontantSuprime"]:
                data["MontantSuprime"] = 0

        if "PrimeGlobale" in data:
            if not data["PrimeGlobale"]:
                data["PrimeGlobale"] = 0

        if "PrimeAffilie" in data:
            if not data["PrimeAffilie"]:
                data["PrimeAffilie"] = 0

        if "PrimeFamille" in data:
            if not data["PrimeFamille"]:
                data["PrimeFamille"] = 0

        if "MontantAccessoireManuel" in data:
            if not data["MontantAccessoireManuel"]:
                data["MontantAccessoireManuel"] = 0
        if "NumeroPoliceCompagnie" in data:
            if data["NumeroPoliceCompagnie"] == "":
                data["NumeroPoliceCompagnie"] = None

        return super().to_internal_value(data)


class AdherentSanteInsertionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdherentSanteInsertionResult
        fields = (
            "idadherent",
            "devis",
            "outputmessage",
        )


class AffilieSanteInsertionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffilieSanteInsertionResult
        fields = (
            "idaffilie",
            "adherent",
            "devis",
            "outputmessage",
        )


class FilialeSanteInsertionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilialeSanteInsertionResult
        fields = (
            "idfiliale",
            "devis",
            "outputmessage",
        )


class SaisieDevisSanteEnCoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaisieDevisSanteEnCours
        fields = (
            "devis",
            "identifiant_devis",
            "utilisateur",
        )


class AnnulationSaisieObjetSanteSerializer(serializers.Serializer):
    id_devis = serializers.IntegerField()
    id_objet = serializers.IntegerField()


class AnnulationSaisieAffilieSerializer(serializers.Serializer):
    id_devis = serializers.IntegerField()
    id_adherent = serializers.IntegerField()
    id_affilie = serializers.IntegerField()


class AnnulationSaisieAdherentSerializer(serializers.Serializer):
    id_devis = serializers.IntegerField()
    id_adherent = serializers.IntegerField()


class AnnulationSaisieFilialeSerializer(serializers.Serializer):
    id_devis = serializers.IntegerField()
    id_filiale = serializers.IntegerField()


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = (
            "nom",
            "prenoms",
        )


class AffilieFnSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffilieFn
        exclude = [
            "id",
        ]
