"""
FICHIER: production/anti_doublons/detection_collision.py
RÔLE: Détection et analyse des collisions/homonymies
"""

import logging
from .utils import normaliser_texte, normaliser_telephone

logger = logging.getLogger(__name__)


def detecter_collision(assure_data: dict, assure_existant) -> tuple:
    """
    Analyse si deux assurés avec même clé sont vraiment la même personne.
    
    Returns:
        (est_meme_personne: bool, score: float, differences: dict)
    """
    differences = {}
    score = 100  # Score de départ
    
    # Champs à comparer avec leur poids
    champs_comparaison = [
        ("LieuNaissance", "LieuNaissance", 15),
        ("Sexe", "Sexe", 10),
        ("NumeroTelephone", "Telephone", 20),
        ("NumeroMobile", "Mobile", 20),
        ("Email", "Email", 10),
        ("NumeroCNI", "CniPat", 15),
    ]
    
    for champ_import, champ_db, poids in champs_comparaison:
        valeur_nouvelle = assure_data.get(champ_import, "")
        valeur_existante = getattr(assure_existant, champ_db, "")
        
        # Normaliser
        if "Telephone" in champ_import or "Mobile" in champ_import:
            valeur_nouvelle = normaliser_telephone(valeur_nouvelle)
            valeur_existante = normaliser_telephone(valeur_existante)
        elif champ_import == "Email":
            valeur_nouvelle = str(valeur_nouvelle).lower() if valeur_nouvelle else ""
            valeur_existante = str(valeur_existante).lower() if valeur_existante else ""
        else:
            valeur_nouvelle = normaliser_texte(str(valeur_nouvelle))
            valeur_existante = normaliser_texte(str(valeur_existante))
        
        # Comparer
        if valeur_nouvelle and valeur_existante:
            if valeur_nouvelle != valeur_existante:
                differences[champ_import] = {
                    'nouvelle': valeur_nouvelle,
                    'existante': valeur_existante
                }
                score -= poids
    
    # Décision: seuil de 60%
    est_meme_personne = score >= 60
    
    return (est_meme_personne, score, differences)


def verifier_homonymie_complete(assure_data: dict):
    """
    Recherche les homonymes complets (même nom, prénom, date).
    
    Returns:
        Liste des homonymes trouvés
    """
    from ..models import Client
    
    nom = normaliser_texte(assure_data.get("Nom", ""))
    prenoms = normaliser_texte(assure_data.get("Prenoms", ""))
    date_naissance = assure_data.get("DateNaissance")
    
    homonymes = Client.objects.filter(
        Nom__iexact=nom,
        Prenoms__iexact=prenoms,
        DateNaissance=date_naissance
    )
    
    if homonymes.exists():
        logger.warning(
            f"HOMONYMIE: {homonymes.count()} client(s) avec "
            f"nom={nom}, prenoms={prenoms}, date={date_naissance}"
        )
        
        for h in homonymes:
            logger.warning(
                f"  → ID: {h.IdClient}, CNI: {h.CniPat}, "
                f"Lieu: {h.LieuNaissance}, Tel: {h.Telephone}"
            )
    
    return list(homonymes)
