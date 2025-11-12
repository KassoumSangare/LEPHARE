from rest_framework import serializers
from .models import *


class BordereauEmissionInputSerializer(serializers.ModelSerializer):
    date_debut = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )
    date_fin = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
    )

    class Meta:
        model = BordereauEmissionInput
        exclude = ["id"]


class BordereauEmissionResultSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BordereauEmissionResultSet
        exclude = ["id"]


class EtatDecisionnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtatDecisionnel
        exclude = [
            "id_etat",
        ]


class EtatCimaE1Serializer(serializers.ModelSerializer):
    class Meta:
        model = EtatCimaE1Emissions
        exclude = ["id"]


class EtatCimaE2Serializer(serializers.ModelSerializer):
    class Meta:
        model = EtatCimaE2Arrieres
        exclude = ["id"]
