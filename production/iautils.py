from decimal import Decimal

from core.utils import convert_to_date


def unpack_ia_quotation_post_data(post_data):
    IdIntermediaire = int(post_data["IdIntermediaire"])
    IdCompagnie = int(post_data["IdCompagnie"])
    IdProduit = int(post_data["IdProduit"])
    IdOffre = int(post_data["IdOffre"])
    IdAvenant = int(post_data["IdAvenant"])
    IdClient = int(post_data["IdClient"])
    IdAssure = int(post_data["IdAssure"])
    IdProfession = int(post_data["IdProfession"])
    Flotte = bool(post_data["Flotte"])
    Coassurance = bool(post_data["Coassurance"])
    DateEffet = convert_to_date(post_data["DateEffet"])
    DateExpiration = convert_to_date(post_data["DateExpiration"])
    DateEmission = convert_to_date(post_data["DateEmission"])
    IdTarif = int(post_data["IdTarif"])
    CapitalDeces = Decimal(post_data["CapitalDeces"])
    CapitalIpp = Decimal(post_data["CapitalIpp"])
    FraisTraitement = Decimal(post_data["FraisTraitement"])
    TauxReduction = Decimal(post_data["TauxReduction"])
    CodeActivite = str(post_data["CodeActivite"])
    DateNaissance = convert_to_date(post_data["DateNaissance"])
    IdDuree = int(post_data["IdDuree"])
    IdDevis = 0
    IdDevisDetail = 0
    if "IdDevis" in post_data and post_data["IdDevis"]:
        IdDevis = int(post_data["IdDevis"])

    if "IdDevisDetail" in post_data and post_data["IdDevisDetail"]:
        IdDevisDetail = int(post_data["IdDevisDetail"])

    AdresseGeographique = ""
    if "AdresseGeographique" in post_data:
        if post_data["AdresseGeographique"]:
            AdresseGeographique = str(post_data["AdresseGeographique"])

    NumeroPoliceConnexe = ""
    if "NumeroPoliceConnexe" in post_data:
        if post_data["NumeroPoliceConnexe"]:
            NumeroPoliceConnexe = str(post_data["NumeroPoliceConnexe"])

    NumeroPoliceCompagnie = ""
    if "NumeroPoliceCompagnie" in post_data:
        if post_data["NumeroPoliceCompagnie"]:
            NumeroPoliceCompagnie = str(post_data["NumeroPoliceCompagnie"])

    PrimeNette = Decimal("0")
    if "PrimeNette" in post_data:
        if post_data["PrimeNette"]:
            PrimeNette = Decimal(post_data["PrimeNette"])
    Accessoire = Decimal("0")
    if "Accessoire" in post_data:
        if post_data["Accessoire"]:
            Accessoire = Decimal(post_data["Accessoire"])

    return (
        IdIntermediaire,
        IdCompagnie,
        IdProduit,
        IdOffre,
        IdAvenant,
        IdClient,
        IdAssure,
        IdProfession,
        Flotte,
        Coassurance,
        DateEffet,
        DateExpiration,
        DateEmission,
        IdTarif,
        CapitalDeces,
        CapitalIpp,
        FraisTraitement,
        TauxReduction,
        CodeActivite,
        DateNaissance,
        AdresseGeographique,
        NumeroPoliceConnexe,
        NumeroPoliceCompagnie,
        IdDuree,
        PrimeNette,
        Accessoire,
        IdDevis,
        IdDevisDetail,
        "",
    )
