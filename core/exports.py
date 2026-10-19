"""
Exports tableur (CSV, Excel) : neutralisation des formules.

Une valeur saisie (nom de client, description du journal, motif…) qui commence par =, +, -, @ serait
évaluée comme une formule à l'ouverture d'un CSV dans Excel ou LibreOffice (injection de formules :
appel de liens, DDE, fuite de données). Les fonctions ci-dessous la font afficher comme du texte, sans
changer les nombres ni la structure des exports.
"""

import re

# Premiers caractères d'une formule, variantes pleine chasse comprises, plus tabulation et retours à la ligne
DEBUTS_FORMULE = ("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠")
# Nombre écrit en texte (-1500, +2,5, -1 250 000 avec espaces insécables) : jamais une formule, laissé tel quel
NOMBRE = re.compile(r"^[+-]?\d[\d   ]*([.,]\d+)?$")


def cellule_csv(valeur):
    """Valeur d'une cellule CSV : un texte qui commence (espaces ignorés) par un caractère de formule est
    préfixé d'une apostrophe, que le tableur affiche comme du texte au lieu de l'évaluer."""
    if valeur is None:
        return ""
    if not isinstance(valeur, str):
        return valeur
    debut = valeur.lstrip(" ")
    if debut[:1] in DEBUTS_FORMULE and not NOMBRE.match(debut.strip()):
        return "'" + valeur
    return valeur


def ligne_csv(valeurs):
    return [cellule_csv(v) for v in valeurs]


def texte_excel(cellule):
    """Cellule openpyxl : un texte commençant par « = » (qu'openpyxl enregistrerait comme formule) est enregistré
    comme texte, à l'identique. Renvoie la cellule."""
    if isinstance(cellule.value, str) and cellule.data_type == "f":
        cellule.data_type = "s"
    return cellule
