from decimal import Decimal


def convertir_decimal_avec_separateurs(nombre, precision=4):
    chaine_formatee = ""
    try:
        nombre_decimal = Decimal(nombre)
        if precision == 4:
            chaine_formatee = (
                f"{nombre_decimal:,.4f}".replace(",", " ")
                .replace(".", ",")
                .rstrip("0")
                .rstrip(",")
            )
        elif precision == 2:
            chaine_formatee = (
                f"{nombre_decimal:,.2f}".replace(",", " ")
                .replace(".", ",")
                .rstrip("0")
                .rstrip(",")
            )
    except Exception as error:
        print(error)

    return chaine_formatee
