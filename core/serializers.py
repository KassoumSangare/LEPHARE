from rest_framework import serializers
from core.validators import validate_contrat_validity_period, ErrorMessage


class EnregistrementDevisBaseSerializer(serializers.Serializer):

    IdIntermediaire = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'intermédiaire",
            field_type="int",
            gender_number="ms",
            field_nature="idt",
        )
    )
    IdCompagnie = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La compagnie",
            field_type="int",
            gender_number="fs",
            field_nature="idt",
        )
    )
    IdProduit = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le produit",
            field_type="int",
            gender_number="ms",
            field_nature="idt",
        )
    )
    IdTarif = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La catégorie",
            field_type="int",
            gender_number="fs",
            field_nature="idt",
        )
    )
    IdOffre = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'offre",
            field_type="int",
            gender_number="fs",
            field_nature="idt",
        )
    )
    IdAvenant = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'avenant",
            field_type="int",
            gender_number="ms",
            field_nature="idt",
        )
    )
    IdClient = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Le client",
            field_type="int",
            gender_number="ms",
            field_nature="idt",
        )
    )
    IdAssure = serializers.IntegerField(
        error_messages=ErrorMessage.generate_error_messages(
            field_name="L'assuré",
            field_type="int",
            gender_number="ms",
            field_nature="idt",
        )
    )
    Flotte = serializers.BooleanField(
        default=False,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Flotte", field_type="boolean"
        ),
    )
    Coassurance = serializers.BooleanField(
        default=False,
        error_messages=ErrorMessage.generate_error_messages(
            field_name="Coassurance", field_type="boolean"
        ),
    )
    DateEmission = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date d'émission", field_type="date", gender_number="fs"
        ),
    )
    DateEffet = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date d'effet", field_type="date", gender_number="fs"
        ),
    )
    DateExpiration = serializers.DateField(
        format="%d-%m-%Y",
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"],
        error_messages=ErrorMessage.generate_error_messages(
            field_name="La date d'expiration", field_type="date", gender_number="fs"
        ),
    )

    def validate(self, data):
        return validate_contrat_validity_period(data)
