"""Routes /api/securite/ : utilisateur connecté, utilisateurs, rôles, droits, journal d'audit."""

from django.urls import path

from . import views_securite as v

urlpatterns = [
    path("moi/", v.moi, name="securite-moi"),
    path("moi/mot-de-passe/", v.changer_mon_mot_de_passe, name="securite-mon-mot-de-passe"),
    path("utilisateurs/", v.utilisateurs, name="securite-utilisateurs"),
    path("utilisateurs/<int:pk>/", v.utilisateur, name="securite-utilisateur"),
    path("utilisateurs/<int:pk>/mot-de-passe/", v.reinitialiser_mot_de_passe, name="securite-utilisateur-mot-de-passe"),
    path("utilisateurs/<int:pk>/activer/", v.activer_utilisateur, {"operation": "activer"}, name="securite-utilisateur-activer"),
    path("utilisateurs/<int:pk>/desactiver/", v.activer_utilisateur, {"operation": "desactiver"},
         name="securite-utilisateur-desactiver"),
    path("roles/", v.roles, name="securite-roles"),
    path("roles/<int:pk>/", v.role, name="securite-role"),
    path("droits/", v.droits, name="securite-droits"),
    path("droits/<str:code>/", v.droit, name="securite-droit"),
    path("journal/", v.journal, name="securite-journal"),
    path("journal/filtres/", v.filtres_journal, name="securite-journal-filtres"),
    path("journal/export/", v.export_journal, name="securite-journal-export"),
    path("journal/<int:pk>/", v.entree_journal, name="securite-journal-entree"),
]
