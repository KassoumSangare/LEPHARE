"""
FICHIER: production/anti_doublons/cle_unique.py  
RÔLE: Génération des clés uniques pour identifier les assurés
"""

import logging
from datetime import date, datetime
from django.db import connection
from .utils import normaliser_texte, normaliser_cni, normaliser_telephone

logger = logging.getLogger(__name__)


def obtenir_cle_unique_assure(assure_data: dict) -> str:
    """
    Génère une clé unique ROBUSTE pour identifier un assuré.
    
    Priorité:
    1. NumeroAssure (si présent)
    2. NumeroCNI (si présent)
    3. Clé composite étendue
    """
    
    # Priorité 1: NumeroAssure
    if assure_data.get("NumeroAssure"):
        numero = str(assure_data["NumeroAssure"]).strip()
        if numero:
            return f"NA-{numero}"
    
    # Priorité 2: CNI
    if assure_data.get("NumeroCNI"):
        cni = normaliser_cni(assure_data["NumeroCNI"])
        if cni and len(cni) >= 5:
            return f"CNI-{cni}"
    
    # Priorité 3: Clé composite ÉTENDUE
    composants = []
    
    # Champs obligatoires
    composants.append(normaliser_texte(assure_data.get("Nom", "")))
    composants.append(normaliser_texte(assure_data.get("Prenoms", "")))
    
    # Date de naissance
    date_naissance = assure_data.get("DateNaissance", "")
    if isinstance(date_naissance, date):
        date_naissance = date_naissance.isoformat()
    composants.append(str(date_naissance))
    
    # Lieu de naissance
    if assure_data.get("LieuNaissance"):
        composants.append(normaliser_texte(assure_data["LieuNaissance"]))
    
    # Sexe
    if assure_data.get("Sexe"):
        composants.append(str(assure_data["Sexe"]).upper())
    
    # Téléphone
    telephone = assure_data.get("NumeroMobile") or assure_data.get("NumeroTelephone")
    if telephone:
        tel_normalise = normaliser_telephone(telephone)
        if tel_normalise:
            composants.append(tel_normalise)
    
    # Email
    email = assure_data.get("Email")
    if email and "@" in str(email):
        composants.append(str(email).lower().strip())
    
    return "COMP-" + "|".join(composants)


def generer_numero_assure_auto() -> str:
    """
    Génère automatiquement un numéro d'assuré unique.
    Format: ASS-YYYYMM-NNNN
    """
    prefixe = datetime.now().strftime("ASS-%Y%m")
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM clients 
            WHERE cle_unique LIKE %s
        """, (f"NA-{prefixe}%",))
        
        count = cursor.fetchone()[0]
        prochain_numero = count + 1
    
    numero_assure = f"{prefixe}-{prochain_numero:04d}"
    logger.info(f"NumeroAssure généré: {numero_assure}")
    
    return numero_assure


def assure_existe_deja(cle_unique: str):
    """Vérifie si un assuré avec cette clé unique existe déjà"""
    from ..models import Client
    
    try:
        return Client.objects.get(cle_unique=cle_unique)
    except Client.DoesNotExist:
        return None
    except Client.MultipleObjectsReturned:
        logger.error(f"PLUSIEURS assurés avec cle_unique={cle_unique}")
        return Client.objects.filter(cle_unique=cle_unique).first()


def verifier_fichier_deja_importe(hash_fichier: str):
    """Vérifie si un fichier a déjà été importé"""
    from ..models import ImportsHistorique
    
    try:
        return ImportsHistorique.objects.filter(
            hash_fichier=hash_fichier
        ).order_by('-date_import').first()
    except Exception as e:
        logger.error(f"Erreur vérification hash: {e}")
        return None
