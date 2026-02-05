import re
from datetime import datetime, date
from typing import Union


def check_date_format(date):
    regex = re.compile("[0-9]{4}\-[0-9]{2}\-[0-9]{2}")
    return re.match(regex, date)


def round_float_value(string:str) -> str:
    string = string.strip()
    if string.isdigit():
        return string
    elif string.replace(".", "", 1).isdigit():
        return str(round(float(string)))


def convert_to_date(value: Union[str, datetime, date]) -> date:
    if value is None:
        raise ValueError("La valeur ne peut pas être None")

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, str):
        value = value.strip()

        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",

            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",

            "%d-%m-%Y %H:%M",
            "%d-%m-%Y %H:%M:%S",

            "%d/%m/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass

        raise ValueError(f"Format de date invalide: '{value}'")

    raise TypeError(f"Type non supporté: {type(value)}")