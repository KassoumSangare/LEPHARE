from rest_framework import serializers
from .models import DistripayTransaction


class DistripayTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistripayTransaction
        fields = "__all__"


class InitiationPaiementSerializer(serializers.Serializer):
    montant = serializers.IntegerField(
        required=True,
        allow_null=False,
        error_messages={
            "null": "Le montant du paiement doit être renseigné.",
            "blank": "Le montant du paiement doit être renseigné.",
            "invalid": "Le montant du paiement doit être un nombre entier.",
        },
    )
    description = serializers.CharField(
        required=True,
        max_length=255,
        allow_null=False,
        error_messages={
            "null": "La description du paiement doit être renseignée.",
            "blank": "La description du paiement doit être renseignée.",
        },
    )
    idclient = serializers.IntegerField(required=False, default=0, allow_null=True)

    def validate_montant(self, value):
        if value is not None:
            if value < 0:
                raise serializers.ValidationError(
                    {"Montant": "Le montant du paiement ne peut inférieur à zéro."}
                )
        return value

    def to_internal_value(self, data):
        if "idclient" in data:
            if not data["idclient"]:
                data["idclient"] = 0
        return super().to_internal_value(data)
