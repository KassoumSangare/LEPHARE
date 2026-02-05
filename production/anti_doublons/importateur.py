"""
FICHIER: votre_app/anti_doublons/importateur.py
RÔLE: Logique principale d'import avec anti-doublons
"""

import os
import logging
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError

from .utils import calculer_hash_fichier
from .cle_unique import (
    obtenir_cle_unique_assure,
    generer_numero_assure_auto,
    assure_existe_deja,
    verifier_fichier_deja_importe
)
from .detection_collision import detecter_collision
from .rapport import (
    ConfigurationImport,
    RapportImport,
    StatutImport,
    ModeImport,
    AssureResultat,
    enregistrer_historique_import
)

logger = logging.getLogger(__name__)


def importer_assures_anti_doublons(
    filepath: str,
    user_id: int,
    request_post_data: dict,
    config: ConfigurationImport = None
):
    """
    Fonction principale d'import avec système anti-doublons.
    
    Args:
        filepath: Chemin vers le fichier Excel
        user_id: ID de l'utilisateur
        request_post_data: Données de la requête POST
        config: Configuration (optionnel)
    
    Returns:
        Tuple (erreur: bool, id_devis: int, rapport: RapportImport)
    """
    
    from ..import_assures import extraire_assures
    
    if config is None:
        config = ConfigurationImport()
    
    # Initialiser le rapport
    rapport = RapportImport(
        nom_fichier=os.path.basename(filepath),
        taille_fichier=os.path.getsize(filepath),
        user_id=user_id,
        mode_import=config.mode_import
    )
    
    debut = datetime.now()
    
    try:
        logger.info("=" * 80)
        logger.info(f"IMPORT: {rapport.nom_fichier}")
        logger.info("=" * 80)
        
        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 1: Calculer hash du fichier
        # ─────────────────────────────────────────────────────────────
        logger.info("→ Calcul du hash...")
        rapport.hash_fichier = calculer_hash_fichier(filepath)
        
        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 2: Vérifier si déjà importé
        # ─────────────────────────────────────────────────────────────
        if config.verifier_hash_fichier:
            logger.info("→ Vérification import antérieur...")
            import_precedent = verifier_fichier_deja_importe(rapport.hash_fichier)
            
            if import_precedent and not config.autoriser_reimport_meme_fichier:
                rapport.statut = StatutImport.REFUSE
                rapport.details_erreur = "Fichier déjà importé"
                rapport.avertissements.append(
                    f"Ce fichier a déjà été importé le "
                    f"{import_precedent.date_import.strftime('%d/%m/%Y à %H:%M')}"
                )
                rapport.duree_secondes = (datetime.now() - debut).total_seconds()
                enregistrer_historique_import(rapport)
                
                logger.warning("✗ Import refusé: fichier déjà importé")
                return (True, 0, rapport)
        
        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 3: Extraire les assurés du fichier
        # ─────────────────────────────────────────────────────────────
        logger.info("→ Extraction des assurés...")
        assures = extraire_assures(filepath)
        rapport.total_lignes = len(assures)
        logger.info(f"  {rapport.total_lignes} assurés extraits")
        
        if not assures:
            rapport.statut = StatutImport.REFUSE
            rapport.details_erreur = "Aucun assuré trouvé"
            rapport.duree_secondes = (datetime.now() - debut).total_seconds()
            enregistrer_historique_import(rapport)
            return (True, 0, rapport)
        
        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 4: Traiter les assurés avec détection de doublons
        # ─────────────────────────────────────────────────────────────
        logger.info("→ Traitement avec anti-doublons...")
        
        id_devis = traiter_assures(
            assures=assures,
            request_post_data=request_post_data,
            config=config,
            rapport=rapport
        )
        
        rapport.id_devis = id_devis
        
        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 5: Déterminer statut final
        # ─────────────────────────────────────────────────────────────
        if len(rapport.erreurs) > 0:
            if len(rapport.assures_nouveaux) > 0:
                rapport.statut = StatutImport.PARTIEL
            else:
                rapport.statut = StatutImport.ECHOUE
        else:
            rapport.statut = StatutImport.REUSSI
        
        rapport.duree_secondes = (datetime.now() - debut).total_seconds()
        
        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 6: Enregistrer dans l'historique
        # ─────────────────────────────────────────────────────────────
        enregistrer_historique_import(rapport)
        
        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 7: Afficher le résumé
        # ─────────────────────────────────────────────────────────────
        logger.info(rapport.afficher_resume())
        
        erreur_survenue = rapport.statut in [StatutImport.ECHOUE, StatutImport.REFUSE]
        
        return (erreur_survenue, id_devis, rapport)
    
    except Exception as e:
        logger.error(f"Erreur lors de l'import: {str(e)}", exc_info=True)
        
        rapport.statut = StatutImport.ECHOUE
        rapport.details_erreur = str(e)
        rapport.duree_secondes = (datetime.now() - debut).total_seconds()
        
        try:
            enregistrer_historique_import(rapport)
        except:
            pass
        
        return (True, 0, rapport)


def traiter_assures(assures, request_post_data, config, rapport):
    """
    Traite les assurés avec détection de doublons.
    
    Returns:
        int: ID du devis créé
    """
    # Import de vos fonctions existantes
    from ..import_assures import (
        insert_new_assure,
        enregistrer_devis_ia,
        get_entete_devis
    )
    
    entete_devis = get_entete_devis(
        request_post_data=request_post_data,
        flotte=(len(assures) > 1)
    )
    
    id_devis = 0
    
    with transaction.atomic():
        for idx, assure_data in enumerate(assures, 1):
            try:
                # Générer la clé unique
                cle_unique = obtenir_cle_unique_assure(assure_data)
                logger.debug(f"[{idx}/{len(assures)}] Clé: {cle_unique[:50]}...")
                
                # Vérifier si existe déjà
                assure_existant = assure_existe_deja(cle_unique)
                
                if assure_existant:
                    # ─── ASSURÉ EXISTANT ───
                    logger.info(f"  → Existant (ID: {assure_existant.IdClient})")
                    
                    # Analyser la similarité
                    est_meme, score, diffs = detecter_collision(
                        assure_data,
                        assure_existant
                    )
                    
                    if est_meme:
                        # Même personne
                        if config.mode_import == ModeImport.CREER_SEULEMENT:
                            rapport.assures_ignores.append(AssureResultat(
                                nom=assure_data['Nom'],
                                prenoms=assure_data.get('Prenoms', ''),
                                cle_unique=cle_unique,
                                numero_ligne=idx,
                                action='IGNORE',
                                id_client=assure_existant.IdClient,
                                message=f"Existant (similarité: {score}%)"
                            ))
                            continue
                    else:
                        # Homonymie - personnes différentes
                        if config.generer_numero_assure_auto:
                            # Générer un NumeroAssure unique
                            numero_auto = generer_numero_assure_auto()
                            assure_data["NumeroAssure"] = numero_auto
                            cle_unique = f"NA-{numero_auto}"
                            
                            rapport.avertissements.append(
                                f"Homonymie: {assure_data['Nom']} - "
                                f"NumeroAssure généré: {numero_auto}"
                            )
                        else:
                            raise ValidationError(f"Homonymie détectée: {assure_data['Nom']}")
                
                # ─── NOUVEL ASSURÉ ───
                logger.info(f"  → Nouveau - création...")
                
                # Ajouter la clé unique
                assure_data['cle_unique'] = cle_unique
                if 'NumeroAssure' in assure_data:
                    assure_data['numero_assure'] = assure_data['NumeroAssure']
                
                # Créer l'assuré
                assure = insert_new_assure(assure_data)
                
                # Créer les bénéficiaires (votre logique existante)
                # ... 
                
                # Créer le devis
                id_devis = enregistrer_devis_ia(
                    entete_devis,
                    assure_data,
                    assure.IdClient
                )
                entete_devis["IdDevis"] = id_devis
                
                rapport.assures_nouveaux.append(AssureResultat(
                    nom=assure_data['Nom'],
                    prenoms=assure_data.get('Prenoms', ''),
                    cle_unique=cle_unique,
                    numero_ligne=idx,
                    action='CREE',
                    id_client=assure.IdClient,
                    message=f"Créé (Devis: {id_devis})"
                ))
            
            except Exception as e:
                logger.error(f"Erreur assuré {assure_data.get('Nom')}: {e}")
                
                rapport.erreurs.append({
                    'ligne': idx,
                    'nom': assure_data.get('Nom', ''),
                    'prenoms': assure_data.get('Prenoms', ''),
                    'erreur': str(e)
                })
                
                if config.mode_import == ModeImport.ERREUR_SI_DOUBLON:
                    raise
    
    return id_devis
