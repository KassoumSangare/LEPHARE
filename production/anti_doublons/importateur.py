"""
FICHIER: production/anti_doublons/importateur.py
VERSION AMÉLIORÉE avec gestion robuste des doublons

CORRECTIONS APPLIQUÉES:
1. Cache local pour doublons dans le même fichier
2. Passage de cle_unique à insert_new_assure()
3. Gestion IntegrityError (race condition)
4. Validation NumeroAssure unique
5. Messages d'erreur explicites
"""

import os
import logging
from datetime import datetime
from django.db import transaction, IntegrityError
from .detection_collision import detecter_collision
from .rapport import (
    ConfigurationImport,
    RapportImport,
    StatutImport,
    ModeImport,
    AssureResultat,
)
from django.core.exceptions import ValidationError

from .cle_unique import (
    obtenir_cle_unique_assure,
    generer_numero_assure_auto,
    assure_existe_deja,
    verifier_fichier_deja_importe
)


logger = logging.getLogger(__name__)


def calculer_hash_fichier(filepath: str) -> str:
    """Calcule le hash SHA256 d'un fichier"""
    import hashlib
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def traiter_assures(assures, request_post_data, config, rapport):
    """
    Traite les assurés avec détection anti-doublons ROBUSTE.
    
    ✅ AMÉLIORATIONS :
    - Cache local pour détecter doublons dans le même fichier
    - Passage de cle_unique à insert_new_assure()
    - Gestion IntegrityError avec retry (race condition)
    - Validation NumeroAssure auto unique
    - Messages d'erreur détaillés par ligne
    
    Returns:
        int: ID du devis créé
    """
    # Import de vos fonctions existantes
    from ..import_assures import (
        insert_new_assure,
        enregistrer_devis_ia,
        get_entete_devis,
        enregistrer_beneficiaire,
    )
    
    entete_devis = get_entete_devis(
        request_post_data=request_post_data,
        flotte=(len(assures) > 1)
    )
    
    id_devis = 0
    
    # ✅ AMÉLIORATION 1 : Cache local des clés uniques traitées dans ce fichier
    cles_traitees_fichier = set()
    
    with transaction.atomic():
        for idx, assure_data in enumerate(assures, 1):
            try:
                # Générer la clé unique
                cle_unique = obtenir_cle_unique_assure(assure_data)
                logger.debug(f"[{idx}/{len(assures)}] Clé: {cle_unique[:50]}...")
                
                # ✅ AMÉLIORATION 2 : Vérifier d'abord dans le cache local
                if cle_unique in cles_traitees_fichier:
                    logger.warning(f"  → Doublon dans le fichier (clé: {cle_unique[:30]}...)")
                    rapport.assures_ignores.append(AssureResultat(
                        nom=assure_data['Nom'],
                        prenoms=assure_data.get('Prenoms', ''),
                        cle_unique=cle_unique,
                        numero_ligne=idx,
                        action='IGNORE',
                        id_client=None,
                        message="Doublon dans le fichier (même CNI ou identité)"
                    ))
                    continue
                
                # Vérifier si existe déjà en base
                assure_existant = assure_existe_deja(cle_unique)
                
                if assure_existant:
                    # ─── ASSURÉ EXISTANT EN BASE ───
                    logger.info(f"  → Existant en base (ID: {assure_existant.IdClient})")
                    
                    # Analyser la similarité
                    est_meme, score, diffs = detecter_collision(
                        assure_data,
                        assure_existant
                    )
                    
                    if est_meme:
                        # ✅ CORRECTION : Même personne détectée
                        # Gérer TOUS les modes d'import
                        
                        if config.mode_import == ModeImport.CREER_SEULEMENT:
                            # Mode : Créer uniquement → Ignorer les doublons
                            rapport.assures_ignores.append(AssureResultat(
                                nom=assure_data['Nom'],
                                prenoms=assure_data.get('Prenoms', ''),
                                cle_unique=cle_unique,
                                numero_ligne=idx,
                                action='IGNORE',
                                id_client=assure_existant.IdClient,
                                message=f"Déjà en base (similarité: {score:.1f}%)"
                            ))
                            continue  # ✅ Passer au suivant
                        
                        elif config.mode_import == ModeImport.METTRE_A_JOUR:
                            # Mode : Mettre à jour → TODO: implémenter
                            logger.info(f"  → Mise à jour (non implémenté)")
                            rapport.assures_ignores.append(AssureResultat(
                                nom=assure_data['Nom'],
                                prenoms=assure_data.get('Prenoms', ''),
                                cle_unique=cle_unique,
                                numero_ligne=idx,
                                action='IGNORE',
                                id_client=assure_existant.IdClient,
                                message="Mise à jour non implémentée"
                            ))
                            continue  # ✅ Passer au suivant
                        
                        elif config.mode_import == ModeImport.ERREUR_SI_DOUBLON:
                            # Mode : Erreur si doublon → Lever une exception
                            raise ValidationError(
                                f"Doublon détecté (mode strict) - Assuré déjà en base "
                                f"(ID: {assure_existant.IdClient}, similarité: {score:.1f}%)"
                            )
                        
                        elif config.mode_import == ModeImport.IGNORER_SILENCIEUX:
                            # Mode : Ignorer silencieusement
                            logger.debug(f"  → Doublon ignoré silencieusement (ID: {assure_existant.IdClient})")
                            rapport.assures_ignores.append(AssureResultat(
                                nom=assure_data['Nom'],
                                prenoms=assure_data.get('Prenoms', ''),
                                cle_unique=cle_unique,
                                numero_ligne=idx,
                                action='IGNORE',
                                id_client=assure_existant.IdClient,
                                message=f"Ignoré (similarité: {score:.1f}%)"
                            ))
                            continue  # ✅ Passer au suivant
                        
                        else:
                            # Mode inconnu → Par sécurité, ignorer
                            logger.warning(f"  → Mode d'import inconnu: {config.mode_import} - Ignorer par sécurité")
                            rapport.assures_ignores.append(AssureResultat(
                                nom=assure_data['Nom'],
                                prenoms=assure_data.get('Prenoms', ''),
                                cle_unique=cle_unique,
                                numero_ligne=idx,
                                action='IGNORE',
                                id_client=assure_existant.IdClient,
                                message=f"Mode inconnu - Ignoré par sécurité"
                            ))
                            continue  # ✅ Passer au suivant
                    
                    else:
                        # Homonymie - personnes différentes avec même nom/date
                        if config.generer_numero_assure_auto:
                            # ✅ Générer NumeroAssure unique avec vérification
                            max_tentatives = 10
                            numero_auto = None
                            
                            for tentative in range(max_tentatives):
                                numero_auto = generer_numero_assure_auto()
                                cle_unique_na = f"NA-{numero_auto}"
                                
                                # Vérifier que ce NA n'existe ni en base ni dans le fichier
                                if (cle_unique_na not in cles_traitees_fichier and 
                                    not assure_existe_deja(cle_unique_na)):
                                    cle_unique = cle_unique_na
                                    assure_data["NumeroAssure"] = numero_auto
                                    logger.info(f"  → Homonymie - NumeroAssure généré: {numero_auto}")
                                    break
                            else:
                                # Échec après 10 tentatives
                                raise ValidationError(
                                    f"Impossible de générer un NumeroAssure unique après "
                                    f"{max_tentatives} tentatives"
                                )
                            
                            rapport.avertissements.append(
                                f"Ligne {idx} - Homonymie détectée: {assure_data['Nom']} - "
                                f"NumeroAssure généré: {numero_auto}"
                            )
                        else:
                            raise ValidationError(
                                f"Homonymie détectée (génération NumeroAssure auto désactivée)"
                            )
                
                # ─── NOUVEL ASSURÉ ───
                logger.info(f"  → Nouveau - création...")
                
                # ✅ AMÉLIORATION 4 : Passer cle_unique et numero_assure
                assure_data['cle_unique'] = cle_unique
                if 'NumeroAssure' in assure_data:
                    assure_data['numero_assure'] = assure_data['NumeroAssure']
                
                # ✅ AMÉLIORATION 5 : Gérer IntegrityError (race condition ou trigger)
                try:
                    # Créer l'assuré
                    assure = insert_new_assure(assure_data)
                    
                    # ✅ Ajouter au cache local
                    cles_traitees_fichier.add(cle_unique)
                    
                except IntegrityError as e:
                    # Violation de contrainte UNIQUE
                    error_msg = str(e).lower()
                    
                    if 'cle_unique' in error_msg or 'unique' in error_msg:
                        logger.warning(
                            f"  → IntegrityError sur cle_unique : {cle_unique[:30]}... "
                            f"(race condition ou doublon)"
                        )
                        
                        # Réessayer de vérifier si l'assuré existe maintenant
                        assure_existant = assure_existe_deja(cle_unique)
                        if assure_existant:
                            rapport.assures_ignores.append(AssureResultat(
                                nom=assure_data['Nom'],
                                prenoms=assure_data.get('Prenoms', ''),
                                cle_unique=cle_unique,
                                numero_ligne=idx,
                                action='IGNORE',
                                id_client=assure_existant.IdClient,
                                message="Créé par un autre processus (race condition)"
                            ))
                            # Ajouter au cache quand même
                            cles_traitees_fichier.add(cle_unique)
                            continue
                    
                    # Autre erreur IntegrityError (CNI, etc.)
                    raise ValidationError(
                        f"Erreur d'intégrité lors de la création: {str(e)}"
                    )
                
                # Créer les bénéficiaires             
                for idx, ben in enumerate(assure_data.get("Beneficiaires", []), 1):
                    logger.debug(f"Traitement du bénéficiaire {idx}/{len(assure_data['Beneficiaires'])}")
                    enregistrer_beneficiaire(assure.IdClient, ben)
                
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
                    message=f"Créé avec succès (Devis: {id_devis})"
                ))
            
            except ValidationError as e:
                logger.error(f"  ✗ Erreur validation ligne {idx}: {e}")
                rapport.erreurs.append(
                    f"Ligne {idx} ({assure_data.get('Nom', 'Inconnu')} "
                    f"{assure_data.get('Prenoms', '')}): {str(e)}"
                )
            
            except Exception as e:
                logger.error(f"  ✗ Erreur ligne {idx}: {e}", exc_info=True)
                rapport.erreurs.append(
                    f"Ligne {idx} ({assure_data.get('Nom', 'Inconnu')} "
                    f"{assure_data.get('Prenoms', '')}): "
                    f"Erreur lors de l'enregistrement de l'assuré: {str(e)}"
                )
                
                # Propager l'erreur si mode strict
                if config.mode_import == ModeImport.ERREUR_SI_DOUBLON:
                    raise
    
    return id_devis


def importer_assures_anti_doublons(
    filepath: str,
    user_id: int,
    request_post_data: dict,
    config: ConfigurationImport = None
):
    """
    Fonction principale d'import avec système anti-doublons.
    
    CORRECTION : L'enregistrement de l'historique est maintenant dans la même
    transaction que l'import des assurés pour garantir la cohérence.
    
    Args:
        filepath: Chemin vers le fichier Excel
        user_id: ID de l'utilisateur
        request_post_data: Données de la requête POST
        config: Configuration (optionnel)
    
    Returns:
        Tuple (erreur: bool, id_devis: int, rapport: RapportImport)
    """
    # Import de votre fonction existante
    from ..import_assures import extraire_assures
    from .rapport import enregistrer_historique_import
    
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
        # ÉTAPE 2: Vérifier si déjà importé (HORS TRANSACTION)
        # ─────────────────────────────────────────────────────────────
        if config.verifier_hash_fichier:
            logger.info("→ Vérification import antérieur...")
            import_precedent = verifier_fichier_deja_importe(rapport.hash_fichier)
            
            if import_precedent and not config.autoriser_reimport_meme_fichier:
                rapport.statut = StatutImport.REFUSE
                rapport.details_erreur = "Fichier déjà importé"
                rapport.avertissements.append(
                    f"Ce fichier a déjà été importé le "
                    f"{import_precedent['date_import'].strftime('%d/%m/%Y à %H:%M')}"
                )
                rapport.duree_secondes = (datetime.now() - debut).total_seconds()
                
                # CORRECTION : Enregistrer l'historique MÊME en cas de refus
                # Mais HORS transaction car rien à rollback
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
            
            # Enregistrer l'historique HORS transaction
            enregistrer_historique_import(rapport)
            
            return (True, 0, rapport)
        
        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 4-6: Transaction atomique incluant import ET historique
        # ─────────────────────────────────────────────────────────────
        logger.info("→ Traitement avec anti-doublons...")
        
        # CORRECTION : Tout dans UNE SEULE transaction atomique
        with transaction.atomic():
            # Traiter les assurés
            id_devis = traiter_assures(
                assures=assures,
                request_post_data=request_post_data,
                config=config,
                rapport=rapport
            )
            
            rapport.id_devis = id_devis
            
            # Déterminer statut final
            if len(rapport.erreurs) > 0:
                if len(rapport.assures_nouveaux) > 0:
                    rapport.statut = StatutImport.PARTIEL
                else:
                    rapport.statut = StatutImport.ECHOUE
            else:
                rapport.statut = StatutImport.REUSSI
            
            rapport.duree_secondes = (datetime.now() - debut).total_seconds()
            
            # CORRECTION : Enregistrer dans l'historique DANS la transaction
            # Si erreur après, tout sera rollback (assurés + historique)
            enregistrer_historique_import(rapport)
            
            # Afficher le résumé
            logger.info(rapport.afficher_resume())
        
        # Si on arrive ici, la transaction a réussi
        erreur_survenue = rapport.statut in [StatutImport.ECHOUE, StatutImport.REFUSE]
        
        return (erreur_survenue, id_devis, rapport)
    
    except Exception as e:
        logger.error(f"Erreur lors de l'import: {str(e)}", exc_info=True)
        
        rapport.statut = StatutImport.ECHOUE
        rapport.details_erreur = str(e)
        rapport.duree_secondes = (datetime.now() - debut).total_seconds()
        
        # CORRECTION : En cas d'exception, enregistrer l'historique HORS transaction
        # (la transaction a déjà été rollback)
        try:
            enregistrer_historique_import(rapport)
        except Exception as e_hist:
            logger.error(f"Impossible d'enregistrer l'historique: {str(e_hist)}")
        
        return (True, 0, rapport)