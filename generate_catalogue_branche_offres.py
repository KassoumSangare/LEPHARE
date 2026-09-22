"""Generate the URANUS Branche -> Offre -> Garanties catalogue."""

import unicodedata
from collections import defaultdict

import psycopg


DB_DSN = "host=127.0.0.1 port=5432 dbname=oreole user=postgres password=root"


def normalize(value):
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value or "").upper()
        if unicodedata.category(char) != "Mn"
    )


def classify_offer(name, products):
    normalized_name = normalize(name)
    normalized_products = normalize(products)

    if "NON SPECIFIEE" in normalized_name:
        return "Non spécifiée / transversale"
    if "SANTE" in normalized_name or "MINENE" in normalized_name or "OFFRE ARGENT" in normalized_name or "OFFRE OR" in normalized_name:
        return "Santé"
    if "INDIVIDUELLE ACCIDENT" in normalized_name or any(
        marker in normalized_name
        for marker in (
            "CHEFS DEPARTEMENTS", "CHAUFFEURS", "DIRECTEURS", "CADRES ET INGENIEURS",
            "CONTROLEURS", "CHEFS DE SERVICES", "CONSEILLER SPECIAL",
        )
    ):
        return "Individuelle Accidents"
    if "AUTOMOBILE" in normalized_name or any(
        marker in normalized_name
        for marker in (
            "TIERS", "TIERCE", "OFFRE VEHICULE", "ENGINS MOBILES",
            "TECK", "ACCACIA", "BAOBAB", "EBENE", "SPECIAL VTC",
        )
    ):
        return "Automobile"
    if "SANTE" in normalized_products:
        return "Santé"
    if "INDIVIDUELLE ACCIDENTS" in normalized_products:
        return "Individuelle Accidents"
    if "VOYAGE" in normalized_products or any(
        marker in normalized_name
        for marker in ("VOYAGE", "SCHENGEN", "EUROPE", "VOYAGEUR", "PERLE", "ECONOMIE", "ECONOMIQUE", "CLASSIQUE", "PREMIUM", "BASIC", "PLUS", "EXTRA")
    ):
        return "Voyage"
    if "TRANSPORT" in normalized_products or any(
        marker in normalized_name
        for marker in ("TRANSPORT", "MARITIMES", "AERIENNES", "TERRESTRES", "FLUVIALES", "FERROVIAIRES")
    ):
        return "Transport"
    if "MULTIRISQUES HABITATION" in normalized_products or any(
        marker in normalized_name
        for marker in ("LOCATAIRE", "PROPRIETAIRE", "LOGEMENT", "HABITATION", "ATEGBAN")
    ):
        return "Habitation / MRH"
    if "RESPONSABILITE CIVILE" in normalized_products or any(
        marker in normalized_name for marker in ("RESPONSABILITE CIVILE", "OFFRE RC", "GLOBALE DE BANQUE")
    ):
        return "Responsabilité Civile"
    if "MULTIRISQUES PROFESSIONNELLE" in normalized_products or any(
        marker in normalized_name for marker in ("PROFESSIONNEL", "ENTREPRISE", "BUREAU", "IMMEUBLE", "AGRICOLE", "PAC")
    ):
        return "Multirisques Professionnelle"
    return "Autres Risques"


def main():
    query = """
        SELECT o.idoffre, o.libelleoffre, o.actif,
               COALESCE(string_agg(DISTINCT used.libelleproduit, ' | ' ORDER BY used.libelleproduit), '') AS products,
               COALESCE(string_agg(DISTINCT g.libellegarantie, ' | ' ORDER BY g.libellegarantie), '') AS guarantees
        FROM public.stdoffre o
        LEFT JOIN (
            SELECT DISTINCT d.idoffre, p.libelleproduit
            FROM public.stddevis d
            JOIN public.stdproduit p ON p.idproduit = d.idproduit
            UNION
            SELECT DISTINCT cd.idoffre, p.libelleproduit
            FROM public.stdcontratdetail cd
            JOIN public.stdproduit p ON p.idproduit = cd.idproduit
        ) used ON used.idoffre = o.idoffre
        LEFT JOIN public.stdoffregarantie og ON og.idoffre = o.idoffre
        LEFT JOIN public.stdsousgarantie sg ON sg.idsousgarantie = og.idsousgarantie
        LEFT JOIN public.stdgarantie g ON g.idgarantie = sg.idgarantie
        GROUP BY o.idoffre, o.libelleoffre, o.actif
        ORDER BY o.idoffre
    """

    grouped = defaultdict(list)
    with psycopg.connect(DB_DSN) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            for offer_id, name, active, products, guarantees in cursor.fetchall():
                grouped[classify_offer(name, products)].append(
                    {
                        "id": offer_id,
                        "name": name,
                        "active": active,
                        "guarantees": guarantees or "Aucune garantie paramétrée",
                    }
                )

    print("# Catalogue Branche -> Offre -> Garanties")
    print()
    print("Source : tables URANUS `stddevis`, `stdcontratdetail`, `stdoffre`, `stdoffregarantie`, `stdsousgarantie`, `stdgarantie`.")
    print()
    for branch in sorted(grouped):
        offers = grouped[branch]
        print(f"## Branche {branch} ({len(offers)} offres)")
        for offer in offers:
            status = "Active" if offer["active"] else "Inactive"
            print(f"- **{offer['name']}** (ID {offer['id']}, {status})")
            print(f"  - Garanties : {offer['guarantees']}")
        print()


if __name__ == "__main__":
    main()
