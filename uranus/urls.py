"""
Configuration des URLs principales du projet
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("account.urls")),
    path("api/", include("configuration_api.urls")),
    path("api/", include("customer.urls")),
    path("api/", include("production.urls")),
    path("api/", include("asaci.urls")),
    path("api/", include("sante.urls")),
    path("api/", include("reporting.urls")),
    path("api/", include("payment.urls")),
   path('api/autorisations/', include('autorisations.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Personnalisation de l'admin
admin.site.site_header = "Administration - Système d'Autorisation"
admin.site.site_title = "Admin"
admin.site.index_title = "Bienvenue sur l'interface d'administration"