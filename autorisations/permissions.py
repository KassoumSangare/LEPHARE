from rest_framework import permissions
from .models import Permission as PermissionModel


class EstApprobateur(permissions.BasePermission):
    """
    Permission pour vérifier si l'utilisateur est habilité à approuver
    des demandes d'un type donné
    """
    message = "Vous n'êtes pas habilité à approuver ce type de demande"
    
    def has_permission(self, request, view):
        """Vérification au niveau de la vue"""
        if not request.user.is_authenticated:
            return False
        
        # Les superusers ont toutes les permissions
        if request.user.is_admin:
            return True
        
        return True  # Validation détaillée dans has_object_permission
    
    def has_object_permission(self, request, view, obj):
        """Vérification au niveau de l'objet (DemandeAutorisation)"""
        if not request.user.is_authenticated:
            return False
        
        # Les superusers ont toutes les permissions
        if request.user.is_admin:
            return True
        
        # Vérifier si l'utilisateur a la permission pour ce type d'opération
        return PermissionModel.objects.filter(
            utilisateur=request.user,
            type_operation=obj.type_operation,
            actif=True
        ).exists()


class EstDemandeur(permissions.BasePermission):
    """
    Permission pour vérifier si l'utilisateur est le demandeur
    """
    message = "Vous n'êtes pas autorisé à accéder à cette demande"
    
    def has_object_permission(self, request, view, obj):
        """Vérification au niveau de l'objet"""
        if not request.user.is_authenticated:
            return False
        
        # Les superusers ont accès à tout
        if request.user.is_admin:
            return True
        
        # Vérifier si l'utilisateur est le demandeur
        return obj.demandeur == request.user


class PeutCreerDemande(permissions.BasePermission):
    """
    Permission pour créer une demande d'autorisation
    """
    message = "Vous n'êtes pas autorisé à créer des demandes"
    
    def has_permission(self, request, view):
        """Tout utilisateur authentifié peut créer une demande"""
        return request.user.is_authenticated


class PeutAnnulerEncaissement(permissions.BasePermission):
    """
    Permission pour annuler un encaissement
    """
    message = "Vous n'êtes pas autorisé à annuler des encaissements"
    
    def has_permission(self, request, view):
        """
        L'utilisateur doit être authentifié et avoir un jeton valide
        (vérifié dans le serializer)
        """
        return request.user.is_authenticated