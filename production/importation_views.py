"""
FICHIER: production/importation_views.py
RÔLE: Vues API REST pour l'importation d'assurés

DÉPENDANCES:
- Django REST Framework
- anti_doublons/
"""

import os
import tempfile
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView, RetrieveAPIView

from .anti_doublons import importer_assures_anti_doublons, ConfigurationImport
from .anti_doublons.rapport import ModeImport 
from .models import ImportsHistorique
from .serializers import (
    ImportationAssureIaSerializer,
    ImportResultatSerializer,
    ImportsHistoriqueSerializer,
    ImportsHistoriqueDetailSerializer
)


# =====================================================================
# VUE API : Import d'Assurés
# =====================================================================

class ImportAssuresAPIView(APIView):
    """
    API pour importer des assurés depuis un fichier Excel.
    
    POST /api/importationassureia/
    
    Paramètres (multipart/form-data):
        - fichier_excel: Fichier Excel (.xlsx ou .xls)
        - mode_import: creer_seulement (défaut), mettre_a_jour, erreur_si_doublon
        - autoriser_reimport: true/false (défaut: false)
    
    Retourne:
        - 200: Import réussi
        - 400: Erreur de validation ou d'import
        - 401: Non authentifié
    """
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, *args, **kwargs):
        """
        Traite l'upload et l'import du fichier Excel.
        """
        # Validation des données
        serializer = ImportationAssureIaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'message': 'Données invalides',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fichier = serializer.validated_data['FichierExcel']
        mode_import = serializer.validated_data.get('ModeImport', 'mettre_a_jour')
        autoriser_reimport = serializer.validated_data.get('AutoriserReimport', True)
        
        # Sauvegarder temporairement le fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            for chunk in fichier.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            # Configuration de l'import
            config = ConfigurationImport()
            config.autoriser_reimport_meme_fichier = autoriser_reimport
            config.mode_import = ModeImport[mode_import.upper()]
            config.verifier_hash_fichier = False
            
            # Lancer l'import
            erreur, id_devis, rapport = importer_assures_anti_doublons(
                filepath=temp_path,
                user_id=request.user.id,
                request_post_data=request.data,
                config=config
            )
            
            # Préparer la réponse
            resume = rapport.generer_resume()
            
            response_data = {
                'success': not erreur,
                'statut': rapport.statut.value,
                'message': self._generer_message(rapport, erreur),
                'statistiques': {
                    'total': resume['total'],
                    'nouveaux': resume['nouveaux'],
                    'ignores': resume['ignores'],
                    'mis_a_jour': resume['mis_a_jour'],
                    'erreurs': resume['erreurs'],
                    'taux_reussite': resume['taux_reussite'],
                    'duree_secondes': resume['duree_secondes'],
                },
                'id_devis': id_devis,
                'hash_fichier': rapport.hash_fichier,
            }
            
            # ✅ CORRECTION : Toujours inclure les erreurs si présentes
            if rapport.erreurs:
                # Toujours inclure au moins les 10 premières erreurs
                response_data['erreurs'] = rapport.erreurs[:10]
                
                # Si plus de 10 erreurs, indiquer combien restent
                if len(rapport.erreurs) > 10:
                    response_data['erreurs_supplementaires'] = len(rapport.erreurs) - 10
                    response_data['message_erreurs'] = (
                        f"{len(rapport.erreurs)} erreurs détectées. "
                        f"Les 10 premières sont affichées ci-dessous. "
                        f"Utilisez ?details=true pour voir toutes les erreurs."
                    )
            
            # Toujours inclure les avertissements si présents
            if rapport.avertissements:
                response_data['avertissements'] = rapport.avertissements
            
            # Ajouter le détail de l'erreur principale si échec
            if erreur and rapport.details_erreur:
                response_data['details_erreur'] = rapport.details_erreur
            
            # Ajouter les détails complets si demandés
            if request.query_params.get('details', 'false').lower() == 'true':
                response_data['details'] = {
                    'nouveaux': [
                        {
                            'nom': a.nom,
                            'prenoms': a.prenoms,
                            'id_client': a.id_client,
                            'cle_unique': a.cle_unique,
                            'numero_ligne': a.numero_ligne,
                        }
                        for a in rapport.assures_nouveaux
                    ],
                    'ignores': [
                        {
                            'nom': a.nom,
                            'prenoms': a.prenoms,
                            'raison': a.message,
                            'numero_ligne': a.numero_ligne,
                        }
                        for a in rapport.assures_ignores
                    ],
                    'erreurs': rapport.erreurs,  # Toutes les erreurs
                    'avertissements': rapport.avertissements,
                }
            
            # Serializer la réponse
            result_serializer = ImportResultatSerializer(data=response_data)
            if result_serializer.is_valid():
                if erreur:
                    return Response(
                        result_serializer.validated_data,
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    return Response(
                        result_serializer.validated_data,
                        status=status.HTTP_200_OK
                    )
            else:
                return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': f'Erreur inattendue: {str(e)}',
                    'statut': 'ECHOUE'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def _generer_message(self, rapport, erreur):
        """
        Génère un message descriptif et exploitable du résultat.
        
        ✅ CORRECTION : Messages plus explicites avec détails des erreurs
        """
        if erreur:
            if rapport.statut.value == 'REFUSE':
                # Import refusé (fichier déjà importé, etc.)
                return f"Import refusé : {rapport.details_erreur or 'Voir détails'}"
            else:
                # Import échoué avec erreurs
                nb_erreurs = len(rapport.erreurs)
                
                if nb_erreurs == 0 and rapport.details_erreur:
                    # Erreur système sans erreur de ligne
                    return f"Erreur système : {rapport.details_erreur}"
                elif nb_erreurs > 0:
                    # Erreurs sur des lignes spécifiques
                    premiere_erreur = rapport.erreurs[0] if rapport.erreurs else ""
                    
                    msg = f"Import échoué avec {nb_erreurs} erreur(s). "
                    
                    if premiere_erreur:
                        msg += f"Première erreur : {premiere_erreur}"
                    
                    if nb_erreurs > 1:
                        msg += f" (et {nb_erreurs - 1} autre(s) - voir 'erreurs' ci-dessous)"
                    
                    return msg
                else:
                    # Erreur générique
                    return f"Import échoué : {rapport.details_erreur or 'Erreur inconnue - consultez les logs'}"
        else:
            # Import réussi
            msg_parts = []
            
            if len(rapport.assures_nouveaux) > 0:
                msg_parts.append(f"{len(rapport.assures_nouveaux)} assuré(s) créé(s)")
            
            if len(rapport.assures_ignores) > 0:
                msg_parts.append(f"{len(rapport.assures_ignores)} ignoré(s) (doublons)")
            
            if len(rapport.assures_mis_a_jour) > 0:
                msg_parts.append(f"{len(rapport.assures_mis_a_jour)} mis à jour")
            
            if not msg_parts:
                return "Import terminé : aucun changement"
            
            return "Import réussi : " + ", ".join(msg_parts)


# =====================================================================
# VUE API : Historique des Imports
# =====================================================================

class ImportsHistoriqueListAPIView(ListAPIView):
    """
    API pour lister l'historique des imports.
    
    GET /api/imports-historique/
    
    Paramètres de query:
        - page: Numéro de page (défaut: 1)
        - page_size: Nombre d'éléments par page (défaut: 20, max: 100)
        - statut: Filtrer par statut (REUSSI, ECHOUE, PARTIEL, REFUSE)
        - user_id: Filtrer par utilisateur
        - date_debut: Filtrer par date (format: YYYY-MM-DD)
        - date_fin: Filtrer par date (format: YYYY-MM-DD)
    
    Retourne:
        Liste paginée des imports avec leurs statistiques.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ImportsHistoriqueSerializer
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        """
        Retourne les imports filtrés selon les paramètres.
        """
        queryset = ImportsHistorique.objects.all().order_by('-date_import')
        
        # Filtrer par statut
        statut = self.request.query_params.get('statut', None)
        if statut:
            queryset = queryset.filter(statut=statut.upper())
        
        # Filtrer par utilisateur
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filtrer par date
        date_debut = self.request.query_params.get('date_debut', None)
        if date_debut:
            queryset = queryset.filter(date_import__date__gte=date_debut)
        
        date_fin = self.request.query_params.get('date_fin', None)
        if date_fin:
            queryset = queryset.filter(date_import__date__lte=date_fin)
        
        return queryset


class ImportsHistoriqueDetailAPIView(RetrieveAPIView):
    """
    API pour récupérer le détail d'un import.
    
    GET /api/imports-historique/{id}/
    
    Retourne:
        Détails complets de l'import incluant le JSON détaillé.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ImportsHistoriqueDetailSerializer
    queryset = ImportsHistorique.objects.all()


# =====================================================================
# VUE API : Statistiques Globales
# =====================================================================

class StatistiquesImportsAPIView(APIView):
    """
    API pour obtenir des statistiques globales sur les imports.
    
    GET /api/imports-statistiques/
    
    Retourne:
        Statistiques agrégées de tous les imports.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        Retourne les statistiques globales.
        """
        stats = ImportsHistorique.statistiques_globales()
        
        return Response({
            'total_imports': stats['total_imports'] or 0,
            'total_assures_crees': stats['total_assures_crees'] or 0,
            'total_assures_ignores': stats['total_assures_ignores'] or 0,
            'total_erreurs': stats['total_erreurs'] or 0,
            'duree_moyenne_secondes': float(stats['duree_moyenne'] or 0),
            'repartition_statuts': {
                'reussis': stats['nb_reussis'] or 0,
                'echecs': stats['nb_echecs'] or 0,
                'refuses': stats['nb_refuses'] or 0,
            }
        })


# =====================================================================
# VUE API : Vérifier un Fichier (sans importer)
# =====================================================================

class VerifierFichierAPIView(APIView):
    """
    API pour vérifier si un fichier a déjà été importé sans l'importer.
    
    POST /api/verifier-fichier/
    
    Paramètres (multipart/form-data):
        - fichier_excel: Fichier Excel à vérifier
    
    Retourne:
        - deja_importe: true/false
        - import_precedent: Détails de l'import précédent si existant
    """
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, *args, **kwargs):
        """
        Vérifie si le fichier a déjà été importé.
        """
        from .anti_doublons.utils import calculer_hash_fichier
        from .anti_doublons.cle_unique import verifier_fichier_deja_importe
        
        if 'fichier_excel' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier fourni'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fichier = request.FILES['fichier_excel']
        
        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            for chunk in fichier.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            # Calculer le hash
            hash_fichier = calculer_hash_fichier(temp_path)
            
            # Vérifier si déjà importé
            import_precedent = verifier_fichier_deja_importe(hash_fichier)
            
            if import_precedent:
                return Response({
                    'deja_importe': True,
                    'hash_fichier': hash_fichier,
                    'import_precedent': {
                        'id': import_precedent['id'],
                        'nom_fichier': import_precedent['nom_fichier'],
                        'date_import': import_precedent['date_import'].isoformat(),
                        'statut': import_precedent['statut'],
                        'nb_assures_nouveaux': import_precedent['nb_assures_nouveaux'],
                    }
                })
            else:
                return Response({
                    'deja_importe': False,
                    'hash_fichier': hash_fichier,
                    'message': 'Ce fichier n\'a pas encore été importé'
                })
        
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)