"""
Configuration des URLs principales du projet
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from core.fichiers import servir_media
from core.views import etat_serveur


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/etat-serveur/", etat_serveur),
    path("api/", include("account.urls")),
    path("api/", include("configuration_api.urls")),
    path("api/", include("customer.urls")),
    path("api/", include("production.urls")),
    path("api/", include("asaci.urls")),
    path("api/", include("sante.urls")),
    path("api/", include("reporting.urls")),
    path("api/", include("payment.urls")),
    path('api/autorisations/', include('autorisations.urls')),
    # Utilisateurs, rôles, droits et journal d'audit (autorisations/views_securite.py)
    path('api/securite/', include('autorisations.urls_securite')),
    # ✨ API Commissions
    path('api/commissions/', include('commissions.urls')),
    # 🏛️ API Institutionnel V2 LE PHARE (CRM, Sinistres, Conventions, GED, Audit CIMA)
    path('api/', include('institutionnel.urls')),
    # Fichiers envoyés (GED, pièces jointes, pièces Santé) : lien signé obligatoire (core/fichiers.py), en DEBUG
    # comme en production ; ils ne sont plus servis en accès libre
    re_path(r"^media/(?P<chemin>.+)$", servir_media, name="media_signe"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Personnalisation de l'admin
admin.site.site_header = "Administration - Système d'Autorisation"
admin.site.site_title = "Admin"
admin.site.index_title = "Bienvenue sur l'interface d'administration"