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
    
    Logique :
    - On compare les champs différenciants (hors clé unique)
    - Score de départ = 0
    - On AJOUTE des points pour chaque similarité
    - Seuil : >= 60% pour considérer comme même personne
    
    Returns:
        (est_meme_personne: bool, score: float, differences: dict)
    """
    differences = {}
    points_obtenus = 0
    points_totaux = 0
    
    # Champs à comparer avec leur poids
    # Format: (champ_import, champ_db, poids)
    champs_comparaison = [
        ("LieuNaissance", "LieuNaissance", 15),
        ("Sexe", "IdQualite", 10),  # CORRECTION: Comparer avec IdQualite
        ("NumeroTelephone", "Telephone", 20),
        ("NumeroMobile", "Mobile", 20),
        ("Email", "Email", 10),
        ("NumeroCNI", "CniPat", 15),
    ]
    
    for champ_import, champ_db, poids in champs_comparaison:
        valeur_nouvelle = assure_data.get(champ_import, "")
        valeur_existante = getattr(assure_existant, champ_db, "")
        
        # Normaliser selon le type
        if champ_import in ("NumeroTelephone", "NumeroMobile"):
            valeur_nouvelle = normaliser_telephone(str(valeur_nouvelle) if valeur_nouvelle else "")
            valeur_existante = normaliser_telephone(str(valeur_existante) if valeur_existante else "")
        elif champ_import == "Email":
            valeur_nouvelle = str(valeur_nouvelle).strip().lower() if valeur_nouvelle else ""
            valeur_existante = str(valeur_existante).strip().lower() if valeur_existante else ""
        elif champ_import == "Sexe":
            # CORRECTION: Gérer la conversion M/F vers 1/2
            if valeur_nouvelle == "M":
                valeur_nouvelle = "1"
            elif valeur_nouvelle == "F":
                valeur_nouvelle = "2"
            valeur_existante = str(valeur_existante) if valeur_existante else ""
        else:
            valeur_nouvelle = normaliser_texte(str(valeur_nouvelle) if valeur_nouvelle else "")
            valeur_existante = normaliser_texte(str(valeur_existante) if valeur_existante else "")
        
        # CORRECTION : Comparer si AU MOINS UNE valeur est présente
        if valeur_nouvelle or valeur_existante:
            points_totaux += poids
            
            if valeur_nouvelle and valeur_existante:
                # Les deux sont présents
                if valeur_nouvelle == valeur_existante:
                    # Identiques : ajouter les points
                    points_obtenus += poids
                    logger.debug(f"  ✓ {champ_import}: identique ({valeur_nouvelle})")
                else:
                    # Différents : pas de points
                    differences[champ_import] = {
                        'nouvelle': valeur_nouvelle,
                        'existante': valeur_existante
                    }
                    logger.debug(f"  ✗ {champ_import}: différent ('{valeur_nouvelle}' vs '{valeur_existante}')")
            else:
                # Un seul est présent : pénalité partielle (50% des points)
                points_obtenus += poids * 0.5
                differences[champ_import] = {
                    'nouvelle': valeur_nouvelle or "[vide]",
                    'existante': valeur_existante or "[vide]"
                }
                logger.debug(f"  ~ {champ_import}: partiellement renseigné")
    
    # Calculer le score en pourcentage
    if points_totaux > 0:
        score = (points_obtenus / points_totaux) * 100
    else:
        # Aucun champ comparable : considérer comme même personne par défaut
        score = 100
    
    # Décision: seuil de 60%
    est_meme_personne = score >= 60
    
    logger.info(
        f"  → Analyse similarité: {score:.1f}% "
        f"({'MÊME PERSONNE' if est_meme_personne else 'HOMONYMIE'})"
    )
    
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