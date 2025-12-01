from rest_framework import serializers
from typing import Any, cast

from configuration_api.models import (
    GenreVehicule,
    Marque,
    OffreAutomobileBoisee,
    Tarif,
    TypeVehicule,
)
from core.serializers import EnregistrementDevisBaseSerializer
from core.validators import ErrorMessage, validate_contrat_validity_period
from customer.models import Client

from .models import (
    AssistanceAutomobile,
    ComplementContratDetailAuto,
    ComplementDevisDetailAuto,
    ComplementDevisDetailVoyage,
    ComplementDevisDetailMrh,
    ComplementDevisDetailSante,
    ComplementDevisDetailRC,
    ComplementDevisDetailDommage,
    ContractForPremiumCollection,
    PremiumCollectionInfo,
    PremiumRemittanceInfo,
    DevisDetGarantie,
    DevisDetail,
    CertificatTransport,
    Devis,
    TarifEcran,
    Contrat,
    ContratDetail,
    LogRecord,
    AyantDroitIa,
    ContratDetGarantie,
    Quittance,
    DetailQuittance,
    DetailEncaissement,
    Encaissement,
    DetailReversement,
    ReversementCompagnie,
    Numero,
    DataInsertionResult,
    QuotationInsertionResult,
    ExtendedDevisInfo,
    QuittanceFn,
    GarantieContratFlotte,
    VehiculeContrat,
    EnregistrementEncaissement,
    DemandeContratPourEncaissement,
    EncaissementQuittance,
    ReversementPrime,
    EncaissementGroupeQuittance,
    ReversementGroupePrime,
    AssureIaInfo,
    AssureIaParDevisOuContrat,
    GarantieSouscrite,
    InfoVehicule,
)
from django.db.models import F


def get_libelle_option(id_detail, entite="CNT"):
    try:
        if entite.upper() == "CNT":
            contrat_detail = ContratDetail.objects.get(pk=id_detail)
            complement_info = ComplementContratDetailAuto.objects.filter(
                contrat_detail=contrat_detail
            )
            if complement_info.count() > 0:
                complement = complement_info[0]
                # Guard against a missing assistance_automobile relation
                if getattr(complement, "assistance_automobile", None):
                    id_option_assistance = complement.assistance_automobile.id_option
                    try:
                        option = AssistanceAutomobile.objects.get(
                            pk=id_option_assistance
                        )
                        return option.libelle_option
                    except AssistanceAutomobile.DoesNotExist:
                        return ""
                else:
                    return ""
            else:
                return ""
        elif entite.upper() == "DEV":
            devis_detail = DevisDetail.objects.get(pk=id_detail)
            complement_info = ComplementDevisDetailAuto.objects.filter(
                devis_detail=devis_detail
            )
            if complement_info.count() > 0:
                complement = complement_info[0]
                # Guard against a missing assistance_automobile relation
                if getattr(complement, "assistance_automobile", None):
                    id_option_assistance = complement.assistance_automobile.id_option
                    try:
                        option = AssistanceAutomobile.objects.get(
                            pk=id_option_assistance
                        )
                        return option.libelle_option
                    except AssistanceAutomobile.DoesNotExist:
                        return ""
                else:
                    return ""
            else:
                return ""
        else:
            return ""
    except Exception as error:
        print(error)
        return ""


class ImportationTransportSerializer(serializers.Serializer):
    fichier_excel = serializers.FileField(
        max_length=None,
        allow_empty_file=False,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le fichier Excel", field_type="fichier", gender_number="ms"
        ),
    )
    debut_periode = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date de début de la période d'émission",
            field_type="date",
            gender_number="fs",
        ),
    )
    fin_periode = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date de fin de la période d'émission",
            field_type="date",
            gender_number="fs",
        ),
    )

    def validate(self, data):
        date_debut_periode = data.get("debut_periode")
        date_fin_periode = data.get("fin_periode")
        if date_debut_periode is not None and date_fin_periode is not None:
            if date_debut_periode > date_fin_periode:
                raise serializers.ValidationError(
                    {
                        "Début Période": "Le début de la période d'émission ne peut être postérieur à la fin de la période."
                    }
                )

        return data


class ContractForPremiumCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractForPremiumCollection
        exclude = [
            "id",
        ]


class PremiumCollectionInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PremiumCollectionInfo
        exclude = [
            "id",
        ]


class PremiumRemittanceInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PremiumRemittanceInfo
        exclude = [
            "id",
        ]


class DevisDetGarantieSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevisDetGarantie
        fields = "__all__"
        depth = 1

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        capital = representation["Capital"]
        deces = representation["deces"]
        ipp = representation["ipp"]
        ft = representation["fraismed"]
        idsousgarantie = int(representation["IdGarantie"]["IdSousGarantie"])
        if idsousgarantie == 22:
            textecapital = get_libelle_option(int(representation["IdDevisDet"]), "DEV")
        elif int(float(deces)) > 0 or int(float(ipp)) > 0 or int(float(ft)) > 0:
            textecapital = (
                "Décès: "
                + f"{int(float(deces)):,}".replace(",", " ")
                + ", IPP: "
                + f"{int(float(ipp)):,}".replace(",", " ")
                + ", FT: "
                + f"{int(float(ft)):,}".replace(",", " ")
            )
        else:
            textecapital = f"{int(float(capital)):,}".replace(",", " ")
        representation["textecapital"] = textecapital
        return representation


class DevisDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevisDetail
        fields = "__all__"
        depth = 1

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["codecategorie"] = ""
        representation["libellecategorie"] = ""
        devis = instance.iddevis
        if devis.produit.id_produit == 1:  # Automobile
            complementinfo = ComplementDevisDetailAuto.objects.filter(
                devis_detail=instance
            )
            if complementinfo.count() > 0:
                representation["bns"] = complementinfo[0].bns
                representation["formule_securite_routiere"] = complementinfo[
                    0
                ].formule_securite_routiere.libelle_formule
                if complementinfo[0].assistance_automobile:
                    representation["assistance_automobie"] = complementinfo[
                        0
                    ].assistance_automobile.id_option
                else:
                    representation["assistance_automobie"] = None
                representation["carburant_autre_matiere"] = complementinfo[
                    0
                ].carburant_autre_matiere
                representation["transport_eleves"] = complementinfo[0].transport_eleves
                representation["transport_employes"] = complementinfo[
                    0
                ].transport_employes
                representation["transport_passager_supplementaire"] = complementinfo[
                    0
                ].transport_passager_supplementaire
        elif devis.produit.id_produit in (2, 3):  # Individuelle Accident ou Voyage
            representation["date_naissance"] = representation["datemec"]
            representation["capital_ipp"] = representation["valeurneuve"]
            representation["capital_deces"] = representation["valeurvenale"]
            representation["frais_traitement"] = representation["valeuraccessoire"]
            if devis.produit.id_produit == 2:
                id_assure = int(representation["matricule"])
                representation["id_assure"] = id_assure
                assureinfo = Client.objects.get(pk=id_assure)
                representation["nom_assure"] = assureinfo.Nom
                representation["prenoms_assure"] = assureinfo.Prenoms
            if devis.produit.id_produit == 3:
                complementinfo = ComplementDevisDetailVoyage.objects.filter(
                    devis_detail=instance
                )
                if complementinfo.count() > 0:
                    representation["id_pays_destination"] = complementinfo[
                        0
                    ].pays_destination.id_pays
                    representation["id_pays_voyageur"] = complementinfo[
                        0
                    ].pays_voyageur.id_pays
                    representation["reference_contrat"] = complementinfo[
                        0
                    ].reference_contrat
                    representation["numero_attestation"] = complementinfo[
                        0
                    ].numero_attestation
                    representation["schengen"] = complementinfo[0].visa_schengen
                    representation["numero_passeport"] = complementinfo[
                        0
                    ].numero_passeport
        elif devis.produit.id_produit == 4:  # Multirisque Habitation
            complementinfo = ComplementDevisDetailMrh.objects.filter(
                devis_detail=instance
            )
            if complementinfo.count() > 0:
                representation["presence_gardien"] = complementinfo[0].presence_gardien
                representation["occupant_locataire"] = complementinfo[
                    0
                ].occupant_locataire
                representation["valeur_loyer"] = complementinfo[0].valeur_loyer
                representation["valeur_contenu"] = complementinfo[0].valeur_contenu
                representation["valeur_objet_precieux"] = complementinfo[
                    0
                ].valeur_objet_precieux
                representation["valeur_materiel"] = complementinfo[0].valeur_materiel
                representation["valeur_degat_batiment"] = complementinfo[
                    0
                ].valeur_degat_batiment
                representation["valeur_degat_contenu"] = complementinfo[
                    0
                ].valeur_degat_contenu
                representation["localisation"] = complementinfo[0].localisation
        elif devis.produit.id_produit == 5:  # Santé
            complementinfo = ComplementDevisDetailSante.objects.filter(
                devis_detail=instance
            )
            if complementinfo.count() > 0:
                representation["prime_famille"] = complementinfo[0].prime_famille
                representation["prime_affilie"] = complementinfo[0].prime_affilie
                representation["prime_globale"] = complementinfo[0].prime_globale
                representation["montant_surprime"] = complementinfo[0].montant_surprime
                representation["montant_accessoire_manuel"] = complementinfo[
                    0
                ].montant_accessoire_manuel
                representation["gestionnaire_sante"] = complementinfo[
                    0
                ].gestionnaire_sante
                representation["taux_reduction_commerciale"] = complementinfo[
                    0
                ].taux_reduction_commerciale
                representation["type_contrat"] = complementinfo[
                    0
                ].type_contrat.id_type_contrat

            tarif = Tarif.objects.get(pk=instance.idtarif)
            if tarif:
                representation["codecategorie"] = tarif.CodeCategorie
                representation["libellecategorie"] = tarif.IdCategorie.LibelleCategorie
        elif devis.produit.id_produit == 6:  # Transport
            pass
        elif devis.produit.id_produit == 7:  # Multirisque Professionnelle
            pass
        elif devis.produit.id_produit == 8:  # Responsabilité Civile
            complementinfo = ComplementDevisDetailRC.objects.filter(
                devis_detail=instance
            )
            if complementinfo.count() > 0:
                representation["taux_prime"] = complementinfo[0].taux_prime
                representation["assiette_prime"] = complementinfo[0].assiette_prime
                representation["nombre_participants"] = complementinfo[
                    0
                ].nombre_participants
                representation["id_domaine_activite"] = complementinfo[
                    0
                ].id_domaine_activite
                representation["id_activite"] = complementinfo[0].id_activite
                representation["localisation"] = complementinfo[0].localisation
                representation["date_debut"] = complementinfo[0].date_debut

        elif devis.produit.id_produit == 9:  # Tous Dommages
            if devis.offre.IdOffre == 32:
                representation["capital_materiel_informatique"] = representation[
                    "valeurneuve"
                ]
                representation["capital_frais_reconstitution"] = representation[
                    "valeurvenale"
                ]
                representation["capital_frais_supplementaire"] = representation[
                    "valeuraccessoire"
                ]
            elif devis.offre.IdOffre == 33:
                representation["capital_detournement_usage_faux"] = representation[
                    "valeurneuve"
                ]
                representation["capital_dommages_confondus"] = representation[
                    "valeurvenale"
                ]
                representation["capital_deterioration_mobiliere_immobiliere"] = (
                    representation["valeuraccessoire"]
                )
            complementinfo = ComplementDevisDetailDommage.objects.filter(
                devis_detail=instance
            )
            if complementinfo.count() > 0:
                representation["taux_prime"] = complementinfo[0].taux_prime
                representation["montant_prime"] = complementinfo[0].montant_prime

        return representation


class CertificatTransportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificatTransport
        fields = "__all__"


class DevisSerializer(serializers.ModelSerializer):
    offreboisee = serializers.SerializerMethodField()

    class Meta:
        model = Devis
        fields = "__all__"
        depth = 1

    def get_offreboisee(self, obj):
        try:
            if hasattr(obj, "iddevis"):
                devis = Devis.objects.annotate(
                    offreboisee=OffreAutomobileBoisee(F("offre__IdOffre"))
                ).get(pk=obj.iddevis)
                if devis and hasattr(devis, "offreboisee"):
                    return devis.offreboisee
        except Devis.DoesNotExist as e:
            print(e)
        return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            if instance.client:
                representation["datenaissaissanceclient"] = (
                    instance.client.DateNaissance
                )
                representation["numeroidentificationclient"] = instance.client.CniPat
            if instance.assure:
                representation["datenaissanceassure"] = instance.assure.DateNaissance
                representation["numeroidentificationassure"] = instance.assure.CniPat
        except Exception as error:
            print(error)
        finally:
            return representation


class TarifEcranSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarifEcran
        fields = "__all__"


class ContratSerializer(serializers.ModelSerializer):
    offreboisee = serializers.SerializerMethodField()

    class Meta:
        model = Contrat
        fields = "__all__"
        depth = 1

    def get_offreboisee(self, obj):
        try:
            if hasattr(obj, "iddevis"):
                devis = Devis.objects.annotate(
                    offreboisee=OffreAutomobileBoisee(F("offre__IdOffre"))
                ).get(pk=obj.iddevis)
                if devis and hasattr(devis, "offreboisee"):
                    return devis.offreboisee
            return False
        except Devis.DoesNotExist as e:
            print("Devis inexistant.")
            return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            if instance.idclient:
                client = Client.objects.get(pk=instance.idclient)
                if client:
                    representation["datenaissanceclient"] = client.DateNaissance
                    representation["numeroidentificationclient"] = client.CniPat
            if instance.idassure:
                assure = Client.objects.get(pk=instance.idassure)
                if assure:
                    representation["datenaissanceassure"] = assure.DateNaissance
                    representation["numeroidentificationassure"] = assure.CniPat
            if instance.id_police_pegas:
                representation["numeropolice"] = representation["id_police_pegas"]
        except Client.DoesNotExist as error:
            print(error)
        finally:
            return representation


class ContratDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContratDetail
        fields = "__all__"

    #   depth = 1

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["codecategorie"] = ""
        contrat = Contrat.objects.get(pk=instance.idcontrat)
        if contrat.idproduit == 5:
            tarif = Tarif.objects.get(pk=instance.idtarif)
            if tarif:
                representation["codecategorie"] = tarif.CodeCategorie
        if contrat.idproduit == 1:
            complementinfo = ComplementContratDetailAuto.objects.filter(
                contrat_detail=instance
            )
            if complementinfo.count() > 0:
                representation["bns"] = complementinfo[0].bns
                representation["formule_securite_routiere"] = complementinfo[
                    0
                ].formule_securite_routiere.libelle_formule
                representation["carburant_autre_matiere"] = complementinfo[
                    0
                ].carburant_autre_matiere
                representation["transport_eleves"] = complementinfo[0].transport_eleves
                representation["transport_employes"] = complementinfo[
                    0
                ].transport_employes
                representation["transport_passager_supplementaire"] = complementinfo[
                    0
                ].transport_passager_supplementaire
            try:
                if int(representation["idmarque"]) != 0:
                    marque = Marque.objects.get(pk=int(representation["idmarque"]))
                    representation["libellemarque"] = marque.LibelleMarque
                idtv = int(representation["idtypevehicule"])
                if idtv != 0:
                    typevehicule = TypeVehicule.objects.get(pk=idtv)
                    representation["libelletypevehicule"] = typevehicule.libelle_type
                idgv = int(representation["idgenrevehicule"])
                if idgv != 0:
                    genrevehicule = GenreVehicule.objects.get(pk=idgv)
                    representation["libellegenrevehicule"] = genrevehicule.LibelleGenre

            except Exception as error:
                print(error)
        return representation


class LogRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogRecord
        fields = ("msg", "level_name")


class AyantDroitIaSerializer(serializers.ModelSerializer):
    libelle_qualite = serializers.SerializerMethodField()

    def get_libelle_qualite(self, obj):
        libelle_qualite = obj.qualite_ayant_droit.libelle_qualite_ayant_droit
        if not libelle_qualite:
            return None
        return libelle_qualite

    class Meta:
        model = AyantDroitIa
        fields = (
            "id_ayant_droit",
            "id_assure",
            "qualite_ayant_droit",
            "nom_ayant_droit",
            "prenoms_ayant_droit",
            "libelle_qualite",
            "part",
        )


class ImportationAssureIaSerializer(serializers.Serializer):
    FichierExcel = serializers.FileField(
        max_length=None,
        allow_empty_file=False,
        error_messages={
            "null": "Le choix du fichier Excel est obligatoire",
            "blank": "Le choix du fichier Excel est obligatoire",
        },
    )
    IdCompagnie = serializers.IntegerField(
        error_messages={
            "null": "La compagnie doit être renseignée.",
            "blank": "La compagnie doit être renseignée.",
            "invalid": "L'ID de la compagnie doit être un nombre entier.",
        }
    )
    IdIntermediaire = serializers.IntegerField(
        error_messages={
            "null": "L'intermédiaire doit être renseigné.",
            "blank": "L'intermédiaire doit être renseigné.",
            "invalid": "L'ID de l'intermédiaire doit être un nombre entier.",
        }
    )
    IdOffre = serializers.IntegerField(
        error_messages={
            "null": "L'offre doit être renseignée.",
            "blank": "L'offre doit être renseignée.",
            "invalid": "L'ID de l'offre doit être un nombre entier.",
        }
    )
    IdAvenant = serializers.IntegerField(
        error_messages={
            "null": "L'avenant doit être renseigné.",
            "blank": "L'avenant doit être renseigné.",
            "invalid": "L'ID de l'avenant doit être un nombre entier.",
        }
    )
    IdClient = serializers.IntegerField(
        error_messages={
            "null": "Le client doit être renseigné.",
            "blank": "Le client doit être renseigné.",
            "invalid": "L'ID du client doit être un nombre entier.",
        }
    )
    NumeroPoliceConnexe = serializers.CharField(
        max_length=50, default="", required=False, allow_null=True
    )
    DateEffet = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date d'effet doit être renseignée.",
            "blank": "La date d'effet doit être renseignée.",
            "invalid": "Format invalide pour la date d'effet.",
        },
    )
    DateExpiration = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date d'expiration doit être renseignée.",
            "blank": "La date d'expiration doit être renseignée.",
            "invalid": "Format invalide pour la date d'expiration.",
        },
    )
    DateEmission = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages={
            "null": "La date d'émission doit être renseignée.",
            "blank": "La date d'émission doit être renseignée.",
            "invalid": "Format invalide pour la date d'émission.",
        },
    )
    IdTarif = serializers.IntegerField(
        error_messages={
            "null": "La catégorie doit être renseignée.",
            "blank": "La catégorie doit être renseignée.",
            "invalid": "L'ID de la catégorie doit être un nombre entier.",
        }
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages={
            "null": "Le taux de réduction doit être renseigné.",
            "blank": "Le taux de réduction doit être renseigné.",
            "invalid": "Le taux de réduction doit être un nombre.",
        },
    )
    IdDuree = serializers.IntegerField(
        default=1,
        error_messages={
            "null": "La durée du contrat doit être renseignée.",
            "blank": "La durée du contrat doit être renseignée.",
            "invalid": "L'ID de la durée du contrat doit être un nombre entier.",
        },
    )
    IdDevis = serializers.IntegerField(
        default=0,
        error_messages={
            "null": "L'ID du devis doit être renseigné.",
            "blank": "L'ID du devis doit être renseigné.",
            "invalid": "L'ID du devis doit être un nombre entier.",
        },
    )
    NumeroPoliceCompagnie = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )

    def validate(self, data):
        validate_contrat_validity_period(data)
        return data


class ContratDetGarantieSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContratDetGarantie
        fields = "__all__"
        depth = 1


class QuittanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quittance
        fields = "__all__"
        depth = 1


class DetailQuittanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetailQuittance
        fields = "__all__"
        depth = 1


# class EncaissementSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Encaissement
#         fields = "__all__"
#         depth = 1


class DetailEncaissementShortSerializer(serializers.ModelSerializer):
    nomclient = serializers.CharField(source='numeroquittance.client.Nom', read_only=True)
    prenomsclient = serializers.CharField(source='numeroquittance.client.Prenoms', read_only=True)
    telephoneclient = serializers.CharField(source='numeroquittance.client.Telephone', read_only=True)
    mobileclient = serializers.CharField(source='numeroquittance.client.Mobile', read_only=True)
    primettc = serializers.DecimalField(source="numeroquittance.primettc", max_digits=19, decimal_places=4, read_only=True)
    class Meta:
        model = DetailEncaissement
        fields = (
            "iddetailencaissement",
            "numeroquittance",
            "indiceacompte",
            "soldeinitial",
            "montant_encaissement",
            "primettc",
            "nomclient",
            "prenomsclient",
            "telephoneclient",
            "mobileclient",
        )


class EncaissementSerializer(serializers.ModelSerializer):
    details = DetailEncaissementShortSerializer(many=True, read_only=True)
    modepaiement = serializers.CharField(source='modepaiement.libellemodepaiement', read_only=True)
    banque = serializers.CharField(source='banque.libelle', read_only=True)

    class Meta:
        model = Encaissement
        fields = (
            "idencaissement",
            "numeropiece",
            "dateencaissement",
            "montantencaissement",
            "montantenattente",
            "montantdeduit",
            "modepaiement",
            "banque",
            "numerocheque",
            "compte_compensation",
            "idutilisateur",
            "datesaisie",
            "piece_annulee",
            "dateannulation",
            "nomannulation",
            "motifannulation",
            "datesaisieannulation",
            "nomtireurcheque",
            "details",
        )

class DetailEncaissementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetailEncaissement
        fields = "__all__"
        depth = 1


class DetailReversementShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetailReversement
        fields = (
            "id_detail_reversement",
            "solde_initial",
            "montant_reverse",
        )


class ReversementCompagnieSerializer(serializers.ModelSerializer):
    details = DetailReversementShortSerializer(many=True, read_only=True)

    class Meta:
        model = ReversementCompagnie
        fields = (
            "id_reversement",
            "compagnie",
            "numero_reversement",
            "date_reversement",
            "montant_reversement",
            "montant_en_attente",
            "montant_deduit",
            "mode_reversement",
            "banque",
            "numero_cheque",
            "compte_compensation",
            "utilisateur",
            "date_saisie",
            "piece_annulee",
            "date_annulation",
            "nom_annulation",
            "motif_annulation",
            "date_saisie_annulation",
            "nom_tireur_cheque",
            "details",
        )
        depth = 1


class DetailReversementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetailReversement
        fields = "__all__"
        depth = 1


class NumeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Numero
        fields = "__all__"


class CreationAyantDroitIaSerializer(serializers.Serializer):
    IdAssure = serializers.IntegerField(
        error_messages={
            "null": "L'assuré doit être renseigné.",
            "blank": "L'assuré doit être renseigné.",
            "invalid": "L'ID de l'assuré doit être un nombre entier.",
        }
    )
    IdQualiteAyantDroit = serializers.IntegerField(
        error_messages={
            "null": "La qualité de l'ayant-droit doit être renseignée.",
            "blank": "La qualité de l'ayant-droit doit être renseignée.",
            "invalid": "Le code de la qualité de l'ayant-droit doit être un nombre entier.",
        }
    )
    NomAyantDroit = serializers.CharField(
        max_length=50,
        error_messages={
            "null": "Le nom de l'ayant-droit doit être renseigné.",
            "blank": "Le nom de l'ayant-droit doit être renseigné.",
        },
    )
    PrenomsAyantDroit = serializers.CharField(
        max_length=60,
        error_messages={
            "null": "Les prénoms de l'ayant-droit doivent être renseignés.",
            "blank": "Les prénoms de l'ayant-droit doivent être renseignés.",
        },
    )
    Part = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages={
            "null": "La part de l'ayant-droit doit être renseignée.",
            "blank": "La part de l'ayant-droit doit être renseignée.",
            "invalid": "La part de l'ayant-droit doit être un nombre.",
        },
    )

    def validate(self, data):
        part_ayant_droit = data.get("Part")
        if part_ayant_droit is not None:
            if part_ayant_droit > 100 or part_ayant_droit <= 0:
                raise serializers.ValidationError(
                    {
                        "Part": "La part de l'ayant-droit doit est comprise entre 0 et 100."
                    }
                )
        return data


class EnregistrementDevisAutoSerializer(EnregistrementDevisBaseSerializer):

    CodeUsage = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'usage",
            field_type="int",
            gender_number="ms",
            field_nature="cod",
        ),
    )
    IdCarrosserie = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La carrosserie",
            field_type="int",
            gender_number="fs",
            field_nature="idt",
        ),
    )
    CodeCarburant = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'énergie",
            field_type="int",
            gender_number="fs",
            field_nature="cod",
        ),
    )
    Puissance = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La puissance fiscale", field_type="int", gender_number="fs"
        ),
    )
    NombrePlace = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le nombre de places", field_type="int", gender_number="ms"
        ),
    )
    Charge = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La charge utile", field_type="int", gender_number="fs"
        ),
    )
    ValeurNeuve = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La valeur neuve", field_type="decimal", gender_number="fs"
        ),
    )
    ValeurVenale = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La valeur venale", field_type="decimal", gender_number="fs"
        ),
    )
    ValeurAccessoire = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La valeur accessoire", field_type="decimal", gender_number="fs"
        ),
    )
    TauxReduction = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de réduction commerciale",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    CodeAlarme = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le système de sécurité",
            field_type="int",
            gender_number="ms",
            field_nature="cod",
        ),
    )
    Bns = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de réduction BNS",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    NomConducteur = serializers.CharField(
        max_length=80, required=False, default="", allow_null=True
    )
    AdresseConducteur = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )
    DateMec = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date de mise en circulation",
            field_type="date",
            gender_number="fs",
        ),
    )
    NumMoteur = serializers.CharField(
        max_length=20, required=False, default="", allow_null=True
    )
    NumChassis = serializers.CharField(
        max_length=20, required=False, default="", allow_null=True
    )
    IdTypeVehicule = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le type du véhicule",
            field_type="int",
            gender_number="ms",
            field_nature="idt",
        ),
    )
    IdMarque = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La marque du véhicule",
            field_type="int",
            gender_number="fs",
            field_nature="idt",
        ),
    )
    Matricule = serializers.CharField(
        max_length=20,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le numéro d'immatriculation",
            field_type="str",
            gender_number="ms",
        ),
    )
    NumPermisConduire = serializers.CharField(
        max_length=30, required=False, default="", allow_null=True
    )
    IdGenreVehicule = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le genre du véhicule",
            field_type="int",
            gender_number="ms",
            field_nature="idt",
        ),
    )
    NumCarteBrunePhysique = serializers.CharField(
        max_length=50, required=False, default="", allow_null=True
    )
    ModeleVehicule = serializers.CharField(
        max_length=20, required=False, default="", allow_null=True
    )
    IdDevis = serializers.IntegerField(
        default=0,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'ID du devis", field_type="int", gender_number="ms"
        ),
    )
    IdDevisDetail = serializers.IntegerField(
        default=0,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'ID du détail du devis", field_type="int", gender_number="ms"
        ),
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
    IdDuree = serializers.IntegerField(required=False, allow_null=True, default=1)
    IdTerme = serializers.IntegerField(required=False, allow_null=True, default=1)
    NumeroPoliceCompagnie = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )

    def validate(self, data):
        data = super().validate(data)

        val_neuve = data.get("ValeurNeuve")
        if val_neuve is None:
            raise serializers.ValidationError(
                {"Valeur neuve": "La valeur neuve doit être renseignée."}
            )

        val_venale = data.get("ValeurVenale")
        if val_venale is None:
            raise serializers.ValidationError(
                {"Valeur venale": "La valeur venale doit être renseignée."}
            )

        val_accessoire = data.get("ValeurAccessoire")
        if val_accessoire is None:
            raise serializers.ValidationError(
                {"Valeur accessoire": "La valeur accessoire doit être renseignée."}
            )

        if val_accessoire > val_venale:
            raise serializers.ValidationError(
                {
                    "Valeur accessoire": "La valeur accessoire ne peut supérieure à la valeur venale."
                }
            )
        if val_accessoire > val_neuve:
            raise serializers.ValidationError(
                {
                    "Valeur accessoire": "La valeur accessoire ne peut supérieure à la valeur neuve."
                }
            )
        if val_venale > val_neuve:
            raise serializers.ValidationError(
                {
                    "Valeur venale": "La valeur venale ne peut supérieure à la valeur neuve."
                }
            )

        return data

    def to_internal_value(self, data):
        if "IdDuree" in data:
            if not data["IdDuree"]:
                data["IdDuree"] = 1
        if "IdTerme" in data:
            if not data["IdTerme"]:
                data["IdTerme"] = 1
        if "NumMoteur" in data:
            if data["NumMoteur"] == "":
                data["NumMoteur"] = None
        if "NumChassis" in data:
            if data["NumChassis"] == "":
                data["NumChassis"] = None
        if "NumCarteBrunePhysique" in data:
            if data["NumCarteBrunePhysique"] == "":
                data["NumCarteBrunePhysique"] = None
        if "ModeleVehicule" in data:
            if data["ModeleVehicule"] == "":
                data["ModeleVehicule"] = None
        if "RemorqueAttelee" in data:
            if not data["RemorqueAttelee"]:
                data["RemorqueAttelee"] = False
        if "CodeFormuleSecuriteRoutiere" in data:
            if data["CodeFormuleSecuriteRoutiere"] == "":
                data["CodeFormuleSecuriteRoutiere"] = None
        if "IdOptionAssistance" in data:
            if not data["IdOptionAssistance"]:
                data["IdOptionAssistance"] = 0
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
        if "NomConducteur" in data:
            if data["NomConducteur"] == "":
                data["NomConducteur"] = None
        if "AdresseConducteur" in data:
            if data["AdresseConducteur"] == "":
                data["AdresseConducteur"] = None
        if "NumPermisConduire" in data:
            if data["NumPermisConduire"] == "":
                data["NumPermisConduire"] = None
        if "NumeroPoliceCompagnie" in data:
            if data["NumeroPoliceCompagnie"] == "":
                data["NumeroPoliceCompagnie"] = None

        return super().to_internal_value(data)


class FinalisationDevisFlotteSerializer(serializers.Serializer):
    IdDevis = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'ID du devis", field_type="int", gender_number="ms"
        ),
    )
    IdClient = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le client",
            field_type="int",
            gender_number="ms",
            field_nature="idt",
        ),
    )
    IdAssure = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'assuré",
            field_type="int",
            gender_number="ms",
            field_nature="idt",
        ),
    )
    Flotte = serializers.BooleanField(
        default=False,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Flotte", field_type="boolean"
        ),
    )


#################################################"EnregistrementDevisIaSerializer"
class EnregistrementDevisIaSerializer(EnregistrementDevisBaseSerializer):

    IdProfession = serializers.IntegerField(required=False, allow_null=True)

    CapitalDeces = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital décès", field_type="decimal", gender_number="ms"
        ),
    )
    CapitalIpp = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital IPP", field_type="decimal", gender_number="ms"
        ),
    )
    FraisTraitement = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Les frais de traitement",
            field_type="decimal",
            gender_number="mp",
            field_nature="mnt",
        ),
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de réduction", field_type="decimal", gender_number="ms"
        ),
    )
    CodeActivite = serializers.CharField(
        max_length=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'activité", field_type="str", gender_number="fs"
        ),
    )
    DateNaissance = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date de naissance", field_type="date", gender_number="fs"
        ),
    )
    AdresseGeographique = serializers.CharField(
        max_length=100, required=False, default="", allow_null=True
    )
    IdDuree = serializers.IntegerField(
        default=1,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La durée du contrat",
            field_type="int",
            gender_number="fs",
            field_nature="idt",
        ),
    )
    IdDevis = serializers.IntegerField(
        default=0,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'ID du devis", field_type="int", gender_number="ms"
        ),
    )
    IdDevisDetail = serializers.IntegerField(
        default=0,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'ID du détail du devis", field_type="int", gender_number="ms"
        ),
    )
    NumeroPoliceConnexe = serializers.CharField(
        max_length=50, required=False, default="", allow_null=True
    )
    NumeroPoliceCompagnie = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )

    def to_internal_value(self, data):

        if "AdresseGeographique" in data:
            if data["AdresseGeographique"] == "":
                data["AdresseGeographique"] = None
        if "NumeroPoliceConnexe" in data:
            if data["NumeroPoliceConnexe"] == "":
                data["NumeroPoliceConnexe"] = None
        if "NumeroPoliceCompagnie" in data:
            if data["NumeroPoliceCompagnie"] == "":
                data["NumeroPoliceCompagnie"] = None
        return super().to_internal_value(data)


################################## Enregistrement Devis Voyage Serializer ############################
class EnregistrementDevisVoyageSerializer(EnregistrementDevisBaseSerializer):
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de réduction", field_type="decimal", gender_number="ms"
        ),
    )
    DateNaissance = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date de naissance", field_type="date", gender_number="fs"
        ),
    )
    IdDevis = serializers.IntegerField(required=False, default=0, allow_null=True)
    IdPaysDestination = serializers.IntegerField(
        required=False, default=1, allow_null=True
    )
    IdPaysVoyageur = serializers.IntegerField(
        required=False, default=1, allow_null=True
    )
    ReferenceContrat = serializers.CharField(
        max_length=50,
        allow_null=True,
        required=False,
        default="",
    )
    NumeroAttestation = serializers.CharField(
        max_length=30,
        allow_null=True,
        required=False,
        default="",
    )
    Schengen = serializers.BooleanField(
        allow_null=True,
        required=False,
        default=False,
    )
    NumeroPasseport = serializers.CharField(
        max_length=30,
        allow_null=True,
        required=False,
        default="",
    )
    NumeroPoliceCompagnie = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )

    def to_internal_value(self, data):
        if "ReferenceContrat" in data:
            if data["ReferenceContrat"] == "":
                data["ReferenceContrat"] = None
        if "NumeroAttestation" in data:
            if data["NumeroAttestation"] == "":
                data["NumeroAttestation"] = None
        if "Schengen" in data:
            if not data["Schengen"]:
                data["Schengen"] = False
        if "NumeroPasseport" in data:
            if data["NumeroPasseport"] == "":
                data["NumeroPasseport"] = None
        if "IdDevis" in data:
            if not data["IdDevis"]:
                data["IdDevis"] = 0
        if "IdPaysDestination" in data:
            if not data["IdPaysDestination"]:
                data["IdPaysDestination"] = 1
        if "IdPaysVoyageur" in data:
            if not data["IdPaysVoyageur"]:
                data["IdPaysVoyageur"] = 1
        if "NumeroPoliceCompagnie" in data:
            if data["NumeroPoliceCompagnie"] == "":
                data["NumeroPoliceCompagnie"] = None

        return super().to_internal_value(data)


############################## Enregistrement Devis MRH Serializer ###########################
class EnregistrementDevisMrhSerializer(EnregistrementDevisBaseSerializer):
    Gardien = serializers.BooleanField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Gardien", field_type="boolean"
        ),
    )
    Locataire = serializers.BooleanField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Locataire", field_type="boolean"
        ),
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de réduction", field_type="decimal", gender_number="ms"
        ),
    )
    ValeurCapitalLoyer = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital valeur du loyer",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    ValeurCapitalContenu = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital valeur du contenu",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    ValeurCapitalObjetPrecieux = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital valeur des objets précieux",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    ValeurCapitalMateriel = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital valeur du matériel",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    ValeurDegatBatiment = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La valeur des dégâts bâtiment",
            field_type="decimal",
            gender_number="fs",
        ),
    )
    ValeurDegatContenu = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La valeur des dégats contenu",
            field_type="decimal",
            gender_number="fs",
        ),
    )
    IdDevis = serializers.IntegerField(required=False, allow_null=True, default=0)
    Localisation = serializers.CharField(
        required=False, allow_null=True, default="", max_length=100
    )
    IdDuree = serializers.IntegerField(required=False, allow_null=True, default=1)
    IdTerme = serializers.IntegerField(required=False, allow_null=True, default=1)
    TelephoneAssure = serializers.CharField(required=False, allow_null=True, default="")
    NumeroPoliceCompagnie = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )

    def to_internal_value(self, data):
        if "TelephoneAssure" in data:
            if data["TelephoneAssure"] == "":
                data["TelephoneAssure"] = None
        if "IdTerme" in data:
            if not data["IdTerme"]:
                data["IdTerme"] = 1
        if "IdDuree" in data:
            if not data["IdDuree"]:
                data["IdDuree"] = 1
        if "Localisation" in data:
            if not data["Localisation"]:
                data["Localisation"] = None
        if "IdDevis" in data:
            if not data["IdDevis"]:
                data["IdDevis"] = 0
        if "NumeroPoliceCompagnie" in data:
            if data["NumeroPoliceCompagnie"] == "":
                data["NumeroPoliceCompagnie"] = None
        return super().to_internal_value(data)


############################## Enregistrement Devis Tous Risques Info Serializer ###########################
class EnregistrementDevisTRInfoSerializer(EnregistrementDevisBaseSerializer):

    TauxPrime = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de prime", field_type="decimal", gender_number="ms"
        ),
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de réduction", field_type="decimal", gender_number="ms"
        ),
    )
    CapitalMaterielInformatique = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital matériel informatique",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    CapitalFraisReconstitution = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital frais de reconstitution",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    CapitalFraisSupplementaire = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital frais supplémentaires",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    MontantPrime = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le montant de la prime",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    IdDevis = serializers.IntegerField(required=False, allow_null=True, default=0)
    IdDuree = serializers.IntegerField(required=False, allow_null=True, default=1)
    TelephoneAssure = serializers.CharField(required=False, allow_null=True, default="")
    NumeroPoliceCompagnie = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )

    def to_internal_value(self, data):
        if "TelephoneAssure" in data:
            if data["TelephoneAssure"] == "":
                data["TelephoneAssure"] = None
        if "IdDevis" in data:
            if not data["IdDevis"]:
                data["IdDevis"] = 0
        if "IdDuree" in data:
            if not data["IdDuree"]:
                data["IdDuree"] = 1
        if "NumeroPoliceCompagnie" in data:
            if data["NumeroPoliceCompagnie"] == "":
                data["NumeroPoliceCompagnie"] = None

        return super().to_internal_value(data)


############################## Enregistrement Devis RC #####################################################
class EnregistrementDevisRCSerializer(EnregistrementDevisBaseSerializer):
    AssiettePrime = serializers.DecimalField(
        max_digits=19, decimal_places=4, required=False, allow_null=True, default=0
    )
    IdDomaineActivite = serializers.IntegerField(
        required=False, allow_null=True, default=0
    )
    IdActivite = serializers.IntegerField(required=False, allow_null=True, default=0)
    Localisation = serializers.CharField(
        max_length=60, required=False, allow_null=True, default=""
    )
    DateDebut = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        required=False,
        allow_null=True,
    )
    NombreParticipants = serializers.IntegerField(
        required=False, allow_null=True, default=0
    )
    TauxPrime = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de prime", field_type="decimal", gender_number="ms"
        ),
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de réduction", field_type="decimal", gender_number="ms"
        ),
    )
    CapitalDommageCorporel = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital dommage corporel",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    CapitalIntoxicationAlimentaire = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital intoxication alimentaire",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    CapitalDommageMateriel = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital dommage matériel",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    IdDevis = serializers.IntegerField(required=False, allow_null=True, default=0)
    IdDuree = serializers.IntegerField(required=False, allow_null=True, default=1)
    TelephoneAssure = serializers.CharField(
        max_length=20, required=False, allow_null=True, default=""
    )
    AdresseGeographique = serializers.CharField(
        max_length=60, required=False, allow_null=True, default=""
    )
    NumeroPoliceConnexe = serializers.CharField(
        max_length=50, required=False, default="", allow_null=True
    )
    NumeroPoliceCompagnie = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )

    def to_internal_value(self, data):
        if "TelephoneAssure" in data:
            if data["TelephoneAssure"] == "":
                data["TelephoneAssure"] = None
        if "IdDevis" in data:
            if not data["IdDevis"]:
                data["IdDevis"] = 0
        if "IdDuree" in data:
            if not data["IdDuree"]:
                data["IdDuree"] = 1
        if "AssiettePrime" in data:
            if not data["AssiettePrime"]:
                data["IdDuree"] = 0
        if "IdDomaineActivite" in data:
            if not data["IdDomaineActivite"]:
                data["IdDomaineActivite"] = 0
        if "IdActivite" in data:
            if not data["IdActivite"]:
                data["IdActivite"] = 0
        if "Localisation" in data:
            if not data["Localisation"]:
                data["Localisation"] = ""
        if "NombreParticipants" in data:
            if not data["NombreParticipants"]:
                data["NombreParticipants"] = 0
        if "NumeroPoliceConnexe" in data:
            if data["NumeroPoliceConnexe"] == "":
                data["NumeroPoliceConnexe"] = None
        if "NumeroPoliceCompagnie" in data:
            if data["NumeroPoliceCompagnie"] == "":
                data["NumeroPoliceCompagnie"] = None

        return super().to_internal_value(data)


############################## Enregistrement Devis Globale de Banque Serializer ###########################
class EnregistrementDevisGlobaleDeBanqueSerializer(EnregistrementDevisBaseSerializer):
    TauxPrime = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de prime", field_type="decimal", gender_number="ms"
        ),
    )
    TauxReduction = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le taux de réduction", field_type="decimal", gender_number="ms"
        ),
    )

    CapitalDetournementUsageFaux = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital détournement",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    CapitalDommagesConfondus = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital dommages confondus",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    CapitalDeteriorationImmobiliere = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le capital détérioration immobilière",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    MontantPrime = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le montant de la prime",
            field_type="decimal",
            gender_number="ms",
        ),
    )
    IdDevis = serializers.IntegerField(required=False, default=0, allow_null=True)
    IdDuree = serializers.IntegerField(required=False, allow_null=True, default=1)
    TelephoneAssure = serializers.CharField(required=False, allow_null=True, default="")
    NumeroPoliceCompagnie = serializers.CharField(
        max_length=60, required=False, default="", allow_null=True
    )

    def to_internal_value(self, data):
        if "TelephoneAssure" in data:
            if data["TelephoneAssure"] == "":
                data["TelephoneAssure"] = None
        if "IdDevis" in data:
            if not data["IdDevis"]:
                data["IdDevis"] = 0
        if "IdDuree" in data:
            if not data["IdDuree"]:
                data["IdDuree"] = 1
        if "NumeroPoliceCompagnie" in data:
            if data["NumeroPoliceCompagnie"] == "":
                data["NumeroPoliceCompagnie"] = None
        return super().to_internal_value(data)


class OperationSurDevisSerializer(serializers.Serializer):
    IdDevis = serializers.IntegerField()


class OperationSurDevisDetailSerializer(serializers.Serializer):
    IdDevisDetail = serializers.IntegerField()


class DataInsertionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataInsertionResult
        fields = (
            "ObjectId",
            "OutputMessage",
        )


class QuotationIaInsertionSerializer(serializers.ModelSerializer):
    Assure = serializers.CharField(source="NumeroImmatriculation", max_length=50)

    class Meta:
        model = QuotationInsertionResult
        fields = (
            "IdDevis",
            "IdDevisDetail",
            "Assure",
            "OutputMessage",
        )


class QuotationInsertionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationInsertionResult
        fields = (
            "IdDevis",
            "IdDevisDetail",
            "NumeroImmatriculation",
            "OutputMessage",
        )


class ExtendedQuotationInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtendedDevisInfo
        exclude = [
            "intermediaire",
            "compagnie",
            "produit",
            "offre",
            "client",
            "assure",
            "avenant",
            "aperiteur",
        ]


class QuittancePropositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuittanceFn
        fields = (
            "IdDevis",
            "RaisonSociale",
            "LibelleIntermediaire",
            "IdClient",
            "NumeroDevis",
            "NumeroAvenant",
            "NomClient",
            "AdresseClient",
            "DateEffet",
            "DateExpiration",
            "DateEmission",
            "Duree",
            "PrimeNette",
            "PrimeNetteHorsFga",
            "Fga",
            "Accessoire",
            "AccessoireCompagnie",
            "AccessoireIntermediaire",
            "TaxeEnregistrement",
            "PrimeTtc",
            "Confirme",
            "LibelleProduit",
            "LibelleCategorie",
            "CommissionIntermediaire",
            "CommissionGestionnaire",
            "CommissionAperition",
            "TitreClient",
            "ProfessionClient",
            "TypeAssure",
            "TypeSouscripteur",
            "TelephoneClient",
            "MobileClient",
            "AdresseGeographique",
            "EmailClient",
            "Cedeao",
            "LibelleMouvement",
            "NomAssure",
            "AdresseAssure",
            "LibelleOffre",
            "LibelleBareme",
            "CodeCategorie",
            "FraisGestion",
            "NumeroPoliceConnexe",
            "CodeIntermediaire",
            "DateNaissanceClient",
            "DateNaissanceAssure",
        )


class QuittanceContratSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuittanceFn
        fields = (
            "IdContrat",
            "IdDevis",
            "RaisonSociale",
            "LibelleIntermediaire",
            "IdClient",
            "NumeroPolice",
            "NumeroAvenant",
            "NomClient",
            "AdresseClient",
            "DateEffet",
            "DateExpiration",
            "DateEmission",
            "Duree",
            "PrimeNette",
            "PrimeNetteHorsFga",
            "Fga",
            "Accessoire",
            "AccessoireCompagnie",
            "AccessoireIntermediaire",
            "TaxeEnregistrement",
            "PrimeTtc",
            "LibelleProduit",
            "LibelleCategorie",
            "CommissionIntermediaire",
            "CommissionGestionnaire",
            "CommissionAperition",
            "TitreClient",
            "ProfessionClient",
            "TypeAssure",
            "TypeSouscripteur",
            "TelephoneClient",
            "MobileClient",
            "AdresseGeographique",
            "EmailClient",
            "Cedeao",
            "LibelleMouvement",
            "NomAssure",
            "AdresseAssure",
            "NumeroQuittance",
            "LibelleOffre",
            "LibelleBareme",
            "CodeCategorie",
            "FraisGestion",
            "NumeroPoliceConnexe",
            "CodeIntermediaire",
            "DateNaissanceClient",
            "DateNaissanceAssure",
        )


class GarantieContratFlotteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarantieContratFlotte
        fields = (
            "IdContrat",
            "NatureRisque",
            "Garantie",
            "SommeMaxGarantie",
            "Franchise",
            "PrimeNette",
        )


class VehiculeContratSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehiculeContrat
        fields = (
            "IdContrat",
            "LibelleTarif",
            "LibelleCategorie",
            "IdMarque",
            "LibelleMarque",
            "IdTypeVehicule",
            "LibelleTypeVehicule",
            "ChargeUtile",
            "Puissance",
            "Immatriculation",
            "DateMec",
            "CodeEnergie",
            "LibelleEnergie",
            "ValeurNeuve",
            "ValeurVenale",
            "NombrePlace",
            "Rc",
            "Fga",
            "Cedeao",
            "Recours",
            "RecoursAnticipe",
            "RecoursExpress",
            "Dommages",
            "Collision",
            "BrisDeGlaces",
            "Incendie",
            "Explosion",
            "VolSimple",
            "VolMainsArmees",
            "Vandalisme",
            "VolAccessoires",
            "IndividuelleChauffeur",
            "InfirmitePermanente",
            "IncapaciteTemporaire",
            "Deces",
            "FraisTraitement",
            "Immobilisation",
            "NsiaAssistCar",
            "PersonnesTransportees",
            "RecoursTiersIncendie",
            "SecuriteRoutiere",
            "PrimeHorsTaxes",
            "Reduction",
            "PrimeNette",
        )


class EnregistrementEncaissementSerializer(serializers.ModelSerializer):
    date_encaissement = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )

    class Meta:
        model = EnregistrementEncaissement
        fields = [
            "mode_encaissement",
            "banque",
            "montant_total",
            "numero_cheque",
            "reference_encaissement",
            "reference_compensation",
            "nom_emetteur",
            "date_encaissement",
            "liste_quittance",
        ]


class DemandeContratPourEncaissementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandeContratPourEncaissement
        fields = (
            "referenceclient",
            "referencecontrat",
        )


class EncaissementQuittanceSerializer(serializers.Serializer):
    numero_quittance = serializers.CharField(required=True)
    montant_encaissement = serializers.DecimalField(
        required=True, max_digits=19, decimal_places=4
    )

    def create(self, validated_data):
        return EncaissementQuittance(**validated_data)

    def update(self, instance, validated_data):
        instance.numero_quittance = validated_data.get(
            "numero_quittance", instance.numero_quittance
        )
        instance.montant_encaissement = validated_data.get(
            "montant_encaissement", instance.montant_encaissement
        )
        return instance


class ReversementPrimeSerializer(serializers.Serializer):
    identifiant_encaissement = serializers.IntegerField(required=True)
    montant_reversement = serializers.DecimalField(
        required=True, max_digits=19, decimal_places=4
    )

    def create(self, validated_data):
        return ReversementPrime(**validated_data)

    def update(self, instance, validated_data):
        instance.identifiant_encaissement = validated_data.get(
            "identifiant_encaissement", instance.identifiant_encaissement
        )
        instance.montant_reversement = validated_data.get(
            "montant_reversement", instance.montant_reversement
        )
        return instance


class EncaissementGroupeQuittanceSerializer(serializers.Serializer):
    mode_encaissement = serializers.IntegerField(required=True)
    date_encaissement = serializers.DateField(
        required=True,
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    banque = serializers.IntegerField(required=False, default=1, allow_null=True)
    montant_total = serializers.DecimalField(
        required=True, max_digits=19, decimal_places=4
    )
    numero_cheque = serializers.CharField(
        max_length=20, required=False, default="", allow_null=True
    )
    reference_encaissement = serializers.CharField(
        max_length=50, required=False, default="", allow_null=True
    )
    reference_compensation = serializers.CharField(
        max_length=10, required=False, default="", allow_null=True
    )
    nom_emetteur = serializers.CharField(required=True, max_length=50)
    liste_quittance = serializers.ListField(
        required=True,
        child=EncaissementQuittanceSerializer(),
        min_length=1,
        max_length=100,
    )

    def to_internal_value(self, data):
        if "numero_cheque" in data:
            if data["numero_cheque"] == "":
                data["numero_cheque"] = None
        if "reference_encaissement" in data:
            if data["reference_encaissement"] == "":
                data["reference_encaissement"] = None
        if "reference_compensation" in data:
            if data["reference_compensation"] == "":
                data["reference_compensation"] = None

        return super().to_internal_value(data)

    def create(self, validated_data):
        return EncaissementGroupeQuittance(**validated_data)

    def update(self, instance, validated_data):
        instance.mode_encaissement = validated_data.get(
            "mode_encaissement", instance.mode_encaissement
        )
        instance.date_encaissement = validated_data.get(
            "date_encaissement", instance.date_encaissement
        )
        instance.banque = validated_data.get("banque", instance.banque)
        instance.montant_total = validated_data.get(
            "montant_total", instance.montant_total
        )
        instance.numero_cheque = validated_data.get(
            "numero_cheque", instance.numero_cheque
        )
        instance.reference_encaissement = validated_data.get(
            "reference_encaissement", instance.reference_encaissement
        )
        instance.reference_compensation = validated_data.get(
            "reference_compensation", instance.reference_compensation
        )
        instance.nom_emetteur = validated_data.get(
            "nom_emetteur", instance.nom_emetteur
        )
        instance.liste_quittance = validated_data.get(
            "liste_quittance", instance.liste_quittance
        )
        return instance


class ReversementGroupePrimeSerializer(serializers.Serializer):
    compagnie = serializers.IntegerField(required=True)
    mode_reversement = serializers.IntegerField(required=True)
    date_reversement = serializers.DateField(
        required=True,
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    banque = serializers.IntegerField(required=False, default=1, allow_null=True)
    montant_total = serializers.DecimalField(
        required=True, max_digits=19, decimal_places=4
    )
    numero_cheque = serializers.CharField(
        max_length=20, required=False, default="", allow_null=True
    )
    nom_emetteur = serializers.CharField(required=True, max_length=50)
    reference_reversement = serializers.CharField(
        max_length=40, required=False, default="", allow_null=True
    )
    reference_compensation = serializers.CharField(
        max_length=10, required=False, default="", allow_null=True
    )
    liste_encaissement = serializers.ListField(
        required=True,
        child=ReversementPrimeSerializer(),
        min_length=1,
        max_length=100,
    )

    def to_internal_value(self, data):
        if "numero_cheque" in data:
            if data["numero_cheque"] == "":
                data["numero_cheque"] = None
        if "reference_reversement" in data:
            if data["reference_reversement"] == "":
                data["reference_reversement"] = None
        if "reference_compensation" in data:
            if data["reference_compensation"] == "":
                data["reference_compensation"] = None

        return super().to_internal_value(data)

    def create(self, validated_data):
        return ReversementGroupePrime(**validated_data)

    def update(self, instance, validated_data):
        instance.compagnie = validated_data.get("compagnie", instance.compagnie)
        instance.mode_reversement = validated_data.get(
            "mode_reversement", instance.mode_reversement
        )
        instance.date_reversement = validated_data.get(
            "date_reversement", instance.date_reversement
        )
        instance.banque = validated_data.get("banque", instance.banque)
        instance.montant_total = validated_data.get(
            "montant_total", instance.montant_total
        )
        instance.numero_cheque = validated_data.get(
            "numero_cheque", instance.numero_cheque
        )
        instance.nom_emetteur = validated_data.get(
            "nom_emetteur", instance.nom_emetteur
        )
        instance.reference_reversement = validated_data.get(
            "reference_reversement", instance.reference_reversement
        )
        instance.reference_compensation = validated_data.get(
            "reference_compensation", instance.reference_compensation
        )
        instance.liste_encaissement = validated_data.get(
            "liste_encaissement", instance.liste_encaissement
        )
        return instance


class ChangementImmatriculationSerializer(serializers.Serializer):
    date_emission = serializers.DateField(
        required=True,
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    date_effet = serializers.DateField(
        required=True,
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    id_devis_ancien = serializers.IntegerField(required=True)
    id_devis_detail_ancien = serializers.IntegerField(required=True)
    numero_carte_brune_physique = serializers.CharField(required=True, max_length=100)
    numero_immatriculation = serializers.CharField(required=True, max_length=100)
    id_devis = serializers.IntegerField(required=False, default=0, allow_null=True)
    id_devis_detail = serializers.IntegerField(
        required=False, default=0, allow_null=True
    )
    id_produit = serializers.IntegerField(required=False, default=1, allow_null=True)
    id_avenant = serializers.IntegerField(required=False, default=10, allow_null=True)

    def to_internal_value(self, data):
        if "id_devis" in data:
            if not data["id_devis"]:
                data["id_devis"] = 0
        if "id_devis_detail" in data:
            if not data["id_devis_detail"]:
                data["id_devis_detail"] = 0
        if "id_produit" in data:
            if not data["id_produit"]:
                data["id_produit"] = 1
        if "id_avenant" in data:
            if not data["id_avenant"]:
                data["id_avenant"] = 10

        return super().to_internal_value(data)


class AvenantAnlRenSerializer(serializers.Serializer):
    date_emission = serializers.DateField(
        required=False,
        allow_null=True,
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        default=None,
    )
    date_effet = serializers.DateField(
        required=False,
        allow_null=True,
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        default=None,
    )
    id_contrat = serializers.IntegerField()
    id_avenant = serializers.IntegerField()
    motif_annulation = serializers.CharField(
        required=False, allow_null=True, max_length=255, default=""
    )

    def to_internal_value(self, data):
        if "motif_annulation" in data:
            if not data["motif_annulation"]:
                data["motif_annulation"] = ""

        return super().to_internal_value(data)


class AssureIaInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssureIaInfo
        exclude = [
            "id",
        ]


class AssureIaParDevisOuContratSerializer(serializers.ModelSerializer):
    AyantsDroit = serializers.SerializerMethodField()

    def get_AyantsDroit(self, obj):
        AyantsDroit = AyantDroitIa.objects.filter(id_assure=obj.IdAssure)
        if not AyantsDroit:
            return None
        return AyantDroitIaSerializer(AyantsDroit, many=True).data

    class Meta:
        model = AssureIaParDevisOuContrat
        fields = (
            "IdAssure",
            "IdDetail",
            "Nom",
            "Prenoms",
            "AdressePostale",
            "AdresseGeographique",
            "DateNaissance",
            "LieuNaissance",
            "Profession",
            "AyantsDroit",
            "CapitalDeces",
            "CapitalInfirmite",
            "CapitalFraisTraitement",
        )


class GarantieSouscriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarantieSouscrite
        exclude = ["id"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        idsousgarantie = int(representation["idsousgarantie"])
        if idsousgarantie == 22:
            textecapital = representation["libelleoption"]
        else:
            capital = representation["capital"]
            deces = representation["deces"]
            ipp = representation["ipp"]
            ft = representation["ft"]
            if int(float(deces)) > 0 or int(float(ipp)) > 0 or int(float(ft)) > 0:
                textecapital = (
                    "Décès: "
                    + f"{int(float(deces)):,}".replace(",", " ")
                    + ", IPP: "
                    + f"{int(float(ipp)):,}".replace(",", " ")
                    + ", FT: "
                    + f"{int(float(ft)):,}".replace(",", " ")
                )
            else:
                if float(capital) > 0.0:
                    textecapital = f"{int(float(capital)):,}".replace(",", " ")
                else:
                    textecapital = ""
        representation["textecapital"] = textecapital
        return representation


class InfoVehiculeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfoVehicule
        exclude = [
            "id",
        ]


class AnnulationEncaissementSerializer(serializers.Serializer):
    id_encaissement = serializers.IntegerField()
    date_annulation = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    motif_annulation = serializers.CharField(max_length=60)


class GarantieSerializer(serializers.Serializer):
    """
    Sérialiseur pour la liste des garanties.
    """

    id_devis_detail = serializers.IntegerField(allow_null=True, required=False)
    id_garantie = serializers.IntegerField()
    acquise = serializers.BooleanField()
    capital = serializers.DecimalField(max_digits=19, decimal_places=4)
    prime_annuelle = serializers.DecimalField(max_digits=19, decimal_places=4)
    prime_nette = serializers.DecimalField(max_digits=19, decimal_places=4)
    montant_franchise = serializers.DecimalField(max_digits=19, decimal_places=4)
    taux_franchise = serializers.DecimalField(max_digits=5, decimal_places=2)
    franchise_minimum = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
    )
    franchise_maximum = serializers.DecimalField(max_digits=19, decimal_places=4)
    capital_deces = serializers.DecimalField(max_digits=19, decimal_places=4)
    capital_ipp = serializers.DecimalField(max_digits=19, decimal_places=4)
    capital_ft = serializers.DecimalField(max_digits=19, decimal_places=4)
    reduction_commerciale = serializers.DecimalField(max_digits=5, decimal_places=2)
    reduction_bns = serializers.DecimalField(max_digits=5, decimal_places=2)


# I have modified this on Novembre 5th, 2025
class CorrectionDevisSerializer(serializers.Serializer):
    """
    Sérialiseur pour les données du devis principal.
    """

    id_devis = serializers.IntegerField()
    prime_annuelle = serializers.DecimalField(max_digits=19, decimal_places=4)
    prime_nette = serializers.DecimalField(max_digits=19, decimal_places=4)
    taxe = serializers.DecimalField(
        max_digits=19, decimal_places=4, allow_null=True, required=False
    )
    accessoire = serializers.DecimalField(
        max_digits=19, decimal_places=4, allow_null=True, required=False
    )
    fga = serializers.DecimalField(
        max_digits=19, decimal_places=4, allow_null=True, required=False
    )
    cedeao = serializers.DecimalField(
        max_digits=19, decimal_places=4, allow_null=True, required=False
    )
    prime_ttc = serializers.DecimalField(
        max_digits=19, decimal_places=4, allow_null=True, required=False
    )
    date_emission = serializers.DateField(
        allow_null=True,
        required=False,
        format=cast(Any, "%d-%m-%Y"),
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    date_effet = serializers.DateField(
        allow_null=True,
        required=False,
        format=cast(Any, "%d-%m-%Y"),
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    date_expiration = serializers.DateField(
        allow_null=True,
        required=False,
        format=cast(Any, "%d-%m-%Y"),
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    numero_police = serializers.CharField(
        allow_null=True, max_length=50, required=False
    )
    reduction_commerciale = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True, required=False
    )
    reduction_bns = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True, required=False
    )
    reduction_flotte = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True, required=False
    )
    liste_garantie = GarantieSerializer(many=True, allow_null=True, required=False)
    supprimer_garanties_manquantes = serializers.BooleanField(
        allow_null=True, required=False
    )

    def validate(self, data):
        data = super().validate(data)
        try:
            id_devis_recu = data["id_devis"]
            id_devis = int(id_devis_recu)
            devis = Devis.objects.get(pk=id_devis)
            if devis:
                id_produit = devis.produit.pk
                if id_produit == 1:
                    missing_fields = set(self.fields.keys()) - set(
                        cast(dict, data).keys()
                    )
                    if missing_fields:
                        raise serializers.ValidationError(
                            f"Champs manquants: {list(missing_fields)[0]}"
                        )
                data["id_produit"] = id_produit
        except ValueError:
            message = (
                f"ValueError: Impossible de convertir '{id_devis_recu}' en entier."
            )
            print(message)
            raise serializers.ValidationError(message)
        except TypeError:
            message = f"TypeError: Type '{type(id_devis_recu).__name__}' impossible à convertir en entier."
            print(message)
            raise serializers.ValidationError(message)
        except OverflowError:
            message = f"OverflowError: '{id_devis_recu}' est trop grand pour être converti en entier."
            print(message)
            raise serializers.ValidationError(message)
        except Devis.DoesNotExist:
            message = f"Devis avec ID: '{id_devis_recu}' inexistant."
            print(message)
            raise serializers.ValidationError(message)
        except Exception as e:
            message = f"Erreur inattendue: {e.__class__.__name__} - {e}"
            print(message)
            raise serializers.ValidationError(message)

        return data


class DevisDetailClientSerializer(serializers.ModelSerializer):
    iddevisdetail = serializers.IntegerField(source="pk")
    marque = serializers.CharField(source="idmarque.LibelleMarque", max_length=60)

    class Meta:
        model = DevisDetail
        fields = ["iddevisdetail", "iddevis", "matricule", "datemec", "marque"]
        read_only_fields = fields


class DevisClientSerializer(serializers.ModelSerializer):
    iddevis = serializers.IntegerField(source="pk")
    nomclient = serializers.CharField(source="client.Nom")
    details = DevisDetailClientSerializer(many=True, read_only=True)

    class Meta:
        model = Devis
        fields = [
            "iddevis",
            "numerodevis",
            "nomclient",
            "dateeffet",
            "dateemission",
            "flotte",
            "details",
        ]
        read_only_fields = fields


class ConsolidationDevisClientSerializer(serializers.Serializer):
    """
    Serializer pour valider le format des données de consolidation.
    """

    iddevis = serializers.IntegerField(min_value=1)

    def validate_iddevis(self, value):
        """
        Validation supplémentaire pour l'ID du devis.
        """
        if value <= 0:
            raise serializers.ValidationError("L'ID du devis doit être positif.")
        return value


class PrimeUpdateSerializer(serializers.Serializer):
    """
    Serializer for validating input data for the stored procedure call.
    """

    # CHARACTER VARYING
    numero_devis = serializers.CharField(max_length=255)

    # NUMERIC (Use DecimalField for precision)
    prime_annuelle = serializers.DecimalField(
        max_digits=19, decimal_places=4, allow_null=True
    )
    prime_nette = serializers.DecimalField(
        max_digits=19, decimal_places=4, allow_null=True
    )
    accessoire = serializers.DecimalField(
        max_digits=19, decimal_places=4, allow_null=True
    )
    taxe = serializers.DecimalField(max_digits=19, decimal_places=4, allow_null=True)
    fga = serializers.DecimalField(max_digits=19, decimal_places=4, allow_null=True)
    cedeao = serializers.DecimalField(max_digits=19, decimal_places=4, allow_null=True)
    prime_ttc = serializers.DecimalField(
        max_digits=19, decimal_places=4, allow_null=True
    )
