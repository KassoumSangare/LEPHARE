"""
FICHIER: production/anti_doublons/rapport.py
RÔLE: Gestion des rapports d'import et configuration
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from django.utils import timezone


# =====================================================================
# ÉNUMÉRATIONS
# =====================================================================

class ModeImport(Enum):
    """Modes d'import disponibles"""
    CREER_SEULEMENT = "creer_seulement"
    METTRE_A_JOUR = "mettre_a_jour"
    ERREUR_SI_DOUBLON = "erreur_si_doublon"
    IGNORER_SILENCIEUX = "ignorer_silencieux"


class StatutImport(Enum):
    """Statuts d'import"""
    REUSSI = "REUSSI"
    ECHOUE = "ECHOUE"
    PARTIEL = "PARTIEL"
    REFUSE = "REFUSE"


# =====================================================================
# CONFIGURATION
# =====================================================================

@dataclass
class ConfigurationImport:
    """Configuration pour un import"""
    mode_import: ModeImport = ModeImport.CREER_SEULEMENT
    verifier_hash_fichier: bool = True
    autoriser_reimport_meme_fichier: bool = False
    generer_numero_assure_auto: bool = True
    seuil_similarite: int = 60


# =====================================================================
# RÉSULTATS
# =====================================================================

@dataclass
class AssureResultat:
    """Résultat du traitement d'un assuré"""
    nom: str
    prenoms: str
    cle_unique: str
    numero_ligne: int
    action: str  # 'CREE', 'IGNORE', 'MIS_A_JOUR', 'ERREUR'
    id_client: Optional[int] = None
    message: str = ""


@dataclass
class RapportImport:
    """Rapport détaillé d'un import"""
    hash_fichier: str = ""
    nom_fichier: str = ""
    taille_fichier: int = 0
    date_import: datetime = field(default_factory=timezone.now)
    user_id: Optional[int] = None
    mode_import: ModeImport = ModeImport.CREER_SEULEMENT
    
    total_lignes: int = 0
    assures_nouveaux: List[AssureResultat] = field(default_factory=list)
    assures_ignores: List[AssureResultat] = field(default_factory=list)
    assures_mis_a_jour: List[AssureResultat] = field(default_factory=list)
    erreurs: List[dict] = field(default_factory=list)
    avertissements: List[str] = field(default_factory=list)
    
    statut: StatutImport = StatutImport.REUSSI
    details_erreur: str = ""
    id_devis: int = 0
    duree_secondes: float = 0.0
    
    def generer_resume(self) -> dict:
        """Génère un résumé statistique"""
        return {
            "total": self.total_lignes,
            "nouveaux": len(self.assures_nouveaux),
            "ignores": len(self.assures_ignores),
            "mis_a_jour": len(self.assures_mis_a_jour),
            "erreurs": len(self.erreurs),
            "avertissements": len(self.avertissements),
            "taux_reussite": (len(self.assures_nouveaux) + len(self.assures_mis_a_jour)) / max(self.total_lignes, 1) * 100,
            "duree_secondes": self.duree_secondes,
            "statut": self.statut.value
        }
    
    def afficher_resume(self) -> str:
        """Génère un résumé textuel"""
        resume = self.generer_resume()
        
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║ RAPPORT D'IMPORT - {self.nom_fichier[:40]}
╠══════════════════════════════════════════════════════════════════╣
║ Statut: {self.statut.value}
║ Durée: {self.duree_secondes:.2f}s
╠══════════════════════════════════════════════════════════════════╣
║ Total: {resume['total']}
║ Nouveaux: {resume['nouveaux']}
║ Ignorés: {resume['ignores']}
║ Mis à jour: {resume['mis_a_jour']}
║ Erreurs: {resume['erreurs']}
║ Taux réussite: {resume['taux_reussite']:.1f}%
╚══════════════════════════════════════════════════════════════════╝
"""


def enregistrer_historique_import(rapport: RapportImport) -> int:
    """Enregistre le rapport dans la base de données"""
    from ..models import ImportsHistorique
    
    details_json = {
        "nouveaux": [
            {
                "nom": a.nom,
                "prenoms": a.prenoms,
                "cle_unique": a.cle_unique,
                "id_client": a.id_client
            }
            for a in rapport.assures_nouveaux
        ],
        "ignores": [
            {
                "nom": a.nom,
                "prenoms": a.prenoms,
                "cle_unique": a.cle_unique,
                "raison": a.message
            }
            for a in rapport.assures_ignores
        ],
        "erreurs": rapport.erreurs,
        "avertissements": rapport.avertissements
    }
    
    historique = ImportsHistorique.objects.create(
        hash_fichier=rapport.hash_fichier,
        nom_fichier=rapport.nom_fichier,
        taille_fichier=rapport.taille_fichier,
        date_import=rapport.date_import,
        user_id=rapport.user_id,
        mode_import=rapport.mode_import.value,
        nb_assures_total=rapport.total_lignes,
        nb_assures_nouveaux=len(rapport.assures_nouveaux),
        nb_assures_ignores=len(rapport.assures_ignores),
        nb_assures_mis_a_jour=len(rapport.assures_mis_a_jour),
        nb_erreurs=len(rapport.erreurs),
        statut=rapport.statut.value,
        details_erreur=rapport.details_erreur,
        id_devis=rapport.id_devis,
        duree_secondes=rapport.duree_secondes,
        details_json=details_json
    )
    
    return historique.id
