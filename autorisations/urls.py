"""
Configuration des URLs pour l'application autorisations
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DemandeAutorisationViewSet,
    JetonAutorisationViewSet,
    PermissionViewSet
)

# Créer le router
router = DefaultRouter()

# Enregistrer les ViewSets
router.register(r'demandes', DemandeAutorisationViewSet, basename='demande')
router.register(r'jetons', JetonAutorisationViewSet, basename='jeton')
router.register(r'permissions', PermissionViewSet, basename='permission')

# Configuration des URLs
app_name = 'autorisations'

urlpatterns = [
    path('', include(router.urls)),
]

"""
ENDPOINTS GÉNÉRÉS AUTOMATIQUEMENT:

═══════════════════════════════════════════════════════════════════
DEMANDES D'AUTORISATION - /api/autorisations/demandes/
═══════════════════════════════════════════════════════════════════

CRUD Standard:
├─ GET     /api/autorisations/demandes/                     → Liste des demandes
├─ POST    /api/autorisations/demandes/                     → Créer une demande
├─ GET     /api/autorisations/demandes/{id}/                → Détails d'une demande
├─ PUT     /api/autorisations/demandes/{id}/                → Modifier complètement
├─ PATCH   /api/autorisations/demandes/{id}/                → Modifier partiellement
└─ DELETE  /api/autorisations/demandes/{id}/                → Supprimer

Actions personnalisées:
├─ GET     /api/autorisations/demandes/mes_demandes/        → Mes demandes
├─ GET     /api/autorisations/demandes/en_attente/          → Demandes en attente (approbateurs)
├─ GET     /api/autorisations/demandes/approuvees/          → Demandes approuvées
├─ GET     /api/autorisations/demandes/rejetees/            → Demandes rejetées
├─ GET     /api/autorisations/demandes/utilisees/           → Demandes utilisées
├─ GET     /api/autorisations/demandes/statistiques/        → Statistiques
├─ POST    /api/autorisations/demandes/{id}/approuver/      → Approuver (+ génère jeton)
└─ POST    /api/autorisations/demandes/{id}/rejeter/        → Rejeter

═══════════════════════════════════════════════════════════════════
JETONS D'AUTORISATION - /api/autorisations/jetons/
═══════════════════════════════════════════════════════════════════

Lecture seule:
├─ GET     /api/autorisations/jetons/                       → Liste des jetons
└─ GET     /api/autorisations/jetons/{id}/                  → Détails d'un jeton

Actions personnalisées:
├─ GET     /api/autorisations/jetons/mes_jetons/            → Mes jetons
└─ POST    /api/autorisations/jetons/verifier/              → Vérifier validité

═══════════════════════════════════════════════════════════════════
PERMISSIONS - /api/autorisations/permissions/
═══════════════════════════════════════════════════════════════════

CRUD (Admin uniquement):
├─ GET     /api/autorisations/permissions/                  → Liste des permissions
├─ POST    /api/autorisations/permissions/                  → Créer une permission
├─ GET     /api/autorisations/permissions/{id}/             → Détails
├─ PUT     /api/autorisations/permissions/{id}/             → Modifier complètement
├─ PATCH   /api/autorisations/permissions/{id}/             → Modifier partiellement
└─ DELETE  /api/autorisations/permissions/{id}/             → Supprimer

Actions personnalisées (Tous utilisateurs):
├─ GET     /api/autorisations/permissions/mes_permissions/  → Mes permissions
└─ GET     /api/autorisations/permissions/approbateurs/     → Liste des approbateurs

═══════════════════════════════════════════════════════════════════
FILTRES & RECHERCHE
═══════════════════════════════════════════════════════════════════

Demandes:
  ?statut=PENDING                    Filtrer par statut
  ?type_operation=ANNUL_ENC          Filtrer par type
  ?demandeur=5                       Filtrer par demandeur
  ?approbateur=2                     Filtrer par approbateur
  ?search=encaissement               Recherche texte
  ?ordering=-date_demande            Tri (- pour desc)
  ?page=2                            Pagination
  ?page_size=50                      Taille de page

Jetons:
  ?utilise=false                     Filtrer par utilisation
  ?demande__statut=APPROVED          Filtrer par statut demande
  ?ordering=-date_generation         Tri

Permissions:
  ?type_operation=ANNUL_ENC          Filtrer par type
  ?actif=true                        Filtrer actifs/inactifs
  ?utilisateur=5                     Filtrer par utilisateur
  ?search=john                       Recherche utilisateur

═══════════════════════════════════════════════════════════════════
EXEMPLES D'UTILISATION
═══════════════════════════════════════════════════════════════════

# 1. Créer une demande d'annulation d'encaissement
POST /api/autorisations/demandes/
{
    "type_operation": "ANNUL_ENC",
    "objet": "Annulation encaissement REF123",
    "motif": "Erreur de saisie",
    "app_label": "encaissements",
    "model_name": "encaissement",
    "object_id": 42
}

# 2. Lister les demandes en attente (approbateur)
GET /api/autorisations/demandes/en_attente/

# 3. Approuver une demande
POST /api/autorisations/demandes/15/approuver/
{
    "duree_validite_heures": 24
}

# 4. Vérifier un jeton
POST /api/autorisations/jetons/verifier/
{
    "code": "A7BK9X2M"
}

# 5. Voir mes permissions
GET /api/autorisations/permissions/mes_permissions/

# 6. Voir qui peut approuver un type d'opération
GET /api/autorisations/permissions/approbateurs/?type_operation=ANNUL_ENC

# 7. Statistiques
GET /api/autorisations/demandes/statistiques/

═══════════════════════════════════════════════════════════════════
"""