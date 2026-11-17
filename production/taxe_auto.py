"""Taxe d'enregistrement des devis Automobile (règle de l'utilisateur, 2026-11-17).

    taxe = (prime nette + accessoire) x 14,5 / 100, calculée en une fois et arrondie au franc

La taxe n'est jamais saisie : toute modification de la prime nette ou de l'accessoire la recalcule, et la prime TTC
avec elle. La prime nette est celle des garanties hors FGA et hors CEDEAO, qui ne sont pas taxés (constaté sur les
660 contrats repris et les grilles NSIA à lecture directe). Taux : celui de la RC Automobile (stdtauxtaxegarantieproduit),
14,5 %. Même règle à l'écran (frontend/src/utils/tarificationAuto.js, taxeAuto) et en base (sp_finalisation_devis v8).
"""
from decimal import ROUND_HALF_UP, Decimal

ID_PRODUIT_AUTO = 1
ID_GARANTIE_RC = 1
TAUX_TAXE_AUTO = Decimal("14.5")


def _decimal(valeur):
    return Decimal(str(valeur if valeur is not None else 0))


def taux_taxe_auto(cursor, date_effet=None):
    """Taux de taxe de la RC Automobile à la date d'effet, 14,5 % à défaut."""
    cursor.execute(
        "SELECT tauxtaxe FROM stdtauxtaxegarantieproduit WHERE idproduit = %s AND idgarantie = %s"
        " AND COALESCE(%s::date, CURRENT_DATE) BETWEEN debutvalidite AND finvalidite"
        " ORDER BY debutvalidite DESC LIMIT 1",
        [ID_PRODUIT_AUTO, ID_GARANTIE_RC, date_effet],
    )
    ligne = cursor.fetchone()
    return _decimal(ligne[0]) if ligne and ligne[0] is not None else TAUX_TAXE_AUTO


def taxe_auto(prime_nette_ht, accessoire, taux=TAUX_TAXE_AUTO):
    """(prime nette hors FGA et CEDEAO + accessoire) x taux / 100, arrondie au franc (ROUND de PostgreSQL)."""
    base = _decimal(prime_nette_ht) + _decimal(accessoire)
    return (base * _decimal(taux) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def taxe_et_ttc_auto(prime_nette_avec_cedeao, cedeao, accessoire, fga, taux=TAUX_TAXE_AUTO):
    """Taxe et prime TTC d'une prime nette CEDEAO comprise (hors FGA), telle que la saisissent les écrans d'imposition.

    TTC = prime nette (CEDEAO comprise) + accessoire + taxe + FGA ; la base l'arrondit ensuite à la pièce (0159).
    """
    prime_nette = _decimal(prime_nette_avec_cedeao)
    taxe = taxe_auto(prime_nette - _decimal(cedeao), accessoire, taux)
    return taxe, prime_nette + _decimal(accessoire) + taxe + _decimal(fga)
