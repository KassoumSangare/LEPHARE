"""
FICHIER: production/anti_doublons/utils.py
RÔLE: Fonctions utilitaires de normalisation et validation

Fonctions pour nettoyer et normaliser les données.
"""

import re
import unicodedata
import hashlib
from datetime import datetime, date
from decimal import Decimal, InvalidOperation


# =====================================================================
# NORMALISATION DE TEXTE
# =====================================================================

def normaliser_texte(texte: str) -> str:
    """Normalise un texte (supprime accents, minuscules, etc.)"""
    if not texte:
        return ""
    
    # Supprimer les accents
    texte = unicodedata.normalize('NFD', str(texte))
    texte = ''.join(char for char in texte if unicodedata.category(char) != 'Mn')
    
    # Minuscules et nettoyage
    texte = texte.lower()
    texte = re.sub(r'[^a-z0-9\s]', '', texte)
    texte = ' '.join(texte.split())
    
    return texte.strip()


def normaliser_cni(cni: str) -> str:
    """Normalise un numéro de CNI"""
    if not cni:
        return ""
    
    cni_norm = re.sub(r'\s+', '', str(cni).upper())
    
    if len(cni_norm) < 5:
        return ""
    
    return cni_norm


def normaliser_telephone(telephone: str) -> str:
    """
    Normalise un numéro de téléphone ivoirien pour comparaison.
    
    En Côte d'Ivoire :
    - Numéros locaux : 10 chiffres
    - Avec indicatif international : 225 + 10 chiffres = 13 chiffres
    
    Args:
        telephone: Numéro de téléphone
    
    Returns:
        str: Téléphone normalisé (chiffres uniquement) ou chaîne vide si invalide
    
    Examples:
        >>> normaliser_telephone("+225 01 02 03 04 05")
        '22501020304005'  # 13 chiffres
        >>> normaliser_telephone("01 02 03 04 05")
        '0102030405'  # 10 chiffres
    """
    if not telephone:
        return ""
    
    # Supprimer tous les caractères non numériques
    tel_clean = re.sub(r'\D', '', str(telephone))
    
    if not tel_clean:
        return ""
    
    # Si commence par 225 (indicatif Côte d'Ivoire)
    if tel_clean.startswith("225"):
        # Format attendu : 225 + 10 chiffres = 13 chiffres total
        if len(tel_clean) == 13:
            return tel_clean
        elif len(tel_clean) > 13:
            # Trop long, garder seulement les 13 premiers
            return tel_clean[:13]
        else:
            # Trop court (moins de 13), invalide
            return ""
    
    # Numéro local sans indicatif
    # Format attendu : 10 chiffres
    elif len(tel_clean) == 10:
        return tel_clean
    
    # Autres formats (tolérance pour numéros partiels)
    elif len(tel_clean) >= 8:
        return tel_clean
    
    else:
        # Moins de 8 chiffres, considéré comme invalide
        return ""



# =====================================================================
# CALCUL DE HASH
# =====================================================================

def calculer_hash_fichier(filepath: str) -> str:
    """Calcule le hash SHA256 d'un fichier"""
    sha256_hash = hashlib.sha256()
    
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


# =====================================================================
# VALIDATION
# =====================================================================

def valider_date(date_valeur, format_date="%d/%m/%Y"):
    """Valide et convertit une date"""
    if date_valeur is None or str(date_valeur).strip() == "":
        return None
    
    if isinstance(date_valeur, date):
        return date_valeur
    
    try:
        return datetime.strptime(str(date_valeur).strip(), format_date).date()
    except ValueError:
        raise ValueError(f"Date invalide: {date_valeur}")


def valider_monetaire(valeur, champ: str) -> Decimal:
    """Valide un montant monétaire"""
    if valeur is None or str(valeur).strip() == "":
        return Decimal("0.00")
    
    try:
        return Decimal(str(valeur).replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"Valeur non numérique pour {champ}: {valeur}")