from rest_framework import serializers
from .models import (
    RetourDemAttestation,
    DetailRetourDemAttestation,
    DemandeAttestation,
    ItemDemandeAttestation,
)

"""
Gestion de la demande d'attestation
"""


class RetourDemAttestationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetourDemAttestation
        fields = "__all__"


class DetailRetourDemAttestationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetailRetourDemAttestation
        fields = "__all__"


class DemandeAttestationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandeAttestation
        # fields = "__all__"
        exclude = ["id"]


class ItemDemandeAttestationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemDemandeAttestation
        # fields = "__all__"
        exclude = ["id"]


class CertificateApplicationSerializer(serializers.Serializer):
    fichier_excel = serializers.FileField(max_length=None, allow_empty_file=False)
    code_compagnie = serializers.CharField(max_length=100, default="")
    code_acces = serializers.CharField(max_length=20)


class CertificateDbApplicationSerializer(serializers.Serializer):
    id_contrat = serializers.IntegerField()


"""
Gestion de la vérification du statut d'une demande d'attestation
"""


class CheckApplicationStatusSerializer(serializers.Serializer):
    reference_demande = serializers.CharField(max_length=100, required=True)


class CertificateStatusUpdateSerializer(serializers.Serializer):
    numero_attestation = serializers.ListField(
        allow_empty=True, child=serializers.CharField(max_length=30)
    )
    code_operation = serializers.CharField(max_length=100, required=True)


class RetrieveApplicationInfoSerializer(serializers.Serializer):
    code_compagnie = serializers.CharField(max_length=100, required=True)
    numero_demande = serializers.CharField(max_length=100, required=True)
