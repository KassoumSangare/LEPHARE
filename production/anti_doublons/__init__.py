"""
FICHIER: votre_app/anti_doublons/__init__.py
RÔLE: Fichier d'initialisation du package anti_doublons

Ce fichier permet d'importer facilement les fonctions principales.
"""

from .importateur import importer_assures_anti_doublons
from .rapport import ConfigurationImport, RapportImport
from .cle_unique import obtenir_cle_unique_assure, generer_numero_assure_auto

__all__ = [
    'importer_assures_anti_doublons',
    'ConfigurationImport',
    'RapportImport',
    'obtenir_cle_unique_assure',
    'generer_numero_assure_auto',
]

__version__ = '1.0.0'
