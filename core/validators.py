from rest_framework import serializers


def validate_contrat_validity_period(data):
    date_effet = data.get("DateEffet")
    date_expiration = data.get("DateExpiration")
    if date_effet is not None and date_expiration is not None:
        if date_expiration < date_effet:
            raise serializers.ValidationError(
                {
                    "Date Expiration": "La date d'expiration ne paut être antérieure à la date d'effet."
                }
            )
    return data


class ErrorMessage:
    default_error_templates = {
        "null_ms": "{field} doit être renseigné.",
        "null_mp": "{field} doivent être renseignés.",
        "null_fs": "{field} doit être renseignée.",
        "null_fp": "{field} doivent être renseignées.",
        "null_boolean": "Le champ {field} doit être renseigné.",
        "invalid_int": "{field} doit être un nombre entier.",
        "invalid_decimal": "{field} doit être un nombre.",
        "invalid_date": "Format invalide pour {field}.",
        "invalid_boolean": "Choisir Vrai(True) ou Faux(False) pour le champ {field}.",
    }

    @classmethod
    def get_field_name_for_invalid(
        cls, field_name, gender_number=None, field_nature=None, field_type=None
    ):
        field_name_for_invalid = field_name
        if field_type is None:
            field_type = ""
        if field_type not in ("int", "decimal"):
            if (
                field_type == "date"
                and field_name_for_invalid.startswith("L")
                and len(field_name_for_invalid) >= 2
            ):
                field_name_for_invalid = "l" + field_name_for_invalid[1:]
            return field_name_for_invalid

        if field_nature is None:
            field_nature = ""
        if gender_number is None:
            gender_number = ""
        if field_nature == "" or gender_number == "":
            return field_name_for_invalid

        prefix = ""
        if field_nature == "mnt":
            prefix = "Le montant "
        elif field_nature == "idt":
            prefix = "L'ID "
        elif field_nature == "val":
            prefix = "La valeur "
        elif field_nature == "cod":
            prefix = "Le code "

        if field_name.startswith("L'") or field_name.startswith("l'"):
            if len(field_name) >= 3:
                field_name_for_invalid = prefix + "de l'" + field_name[2:]
            else:
                field_name_for_invalid = prefix + "de l'"
            return field_name_for_invalid
        else:
            words = field_name.split()
            if len(words) > 1:
                field_name_for_invalid = " ".join(words[1:])
            else:
                return field_name_for_invalid

        if gender_number == "ms":
            field_name_for_invalid = prefix + "du " + field_name_for_invalid
        elif gender_number == "mp":
            field_name_for_invalid = prefix + "des " + field_name_for_invalid
        elif gender_number == "fs":
            field_name_for_invalid = prefix + "de la " + field_name_for_invalid
        elif gender_number == "fp":
            field_name_for_invalid = prefix + "des " + field_name_for_invalid

        return field_name_for_invalid

    @classmethod
    def generate_error_messages(
        cls, field_name, field_type="int", gender_number=None, field_nature=None
    ):
        if field_nature is None:
            field_nature = ""
        if gender_number is None:
            gender_number = ""

        if field_type != "boolean" and gender_number == "":
            raise Exception(
                "Gender and number are mandatory when field type is not boolean."
            )

        if field_type == "boolean":
            null_key = "null_boolean"
        else:
            null_key = "null_" + gender_number.strip().lower()
        if field_type in ("int", "decimal"):
            field_name_for_invalid = cls.get_field_name_for_invalid(
                field_name=field_name,
                field_nature=field_nature,
                gender_number=gender_number,
                field_type=field_type,
            )

        if field_type == "int":
            return {
                "null": cls.default_error_templates[null_key].format(field=field_name),
                "blank": cls.default_error_templates[null_key].format(field=field_name),
                "invalid": cls.default_error_templates["invalid_int"].format(
                    field=field_name_for_invalid
                ),
            }
        elif field_type == "decimal":
            return {
                "null": cls.default_error_templates[null_key].format(field=field_name),
                "blank": cls.default_error_templates[null_key].format(field=field_name),
                "invalid": cls.default_error_templates["invalid_decimal"].format(
                    field=field_name_for_invalid
                ),
            }
        elif field_type == "date":
            return {
                "null": cls.default_error_templates[null_key].format(field=field_name),
                "blank": cls.default_error_templates[null_key].format(field=field_name),
                "invalid": cls.default_error_templates["invalid_date"].format(
                    field=field_name
                ),
            }
        elif field_type == "boolean":
            return {
                "null": cls.default_error_templates[null_key].format(field=field_name),
                "blank": cls.default_error_templates[null_key].format(field=field_name),
                "invalid": cls.default_error_templates["invalid_boolean"].format(
                    field=field_name
                ),
            }
        else:
            return {
                "null": cls.default_error_templates[null_key].format(field=field_name),
                "blank": cls.default_error_templates[null_key].format(field=field_name),
            }
