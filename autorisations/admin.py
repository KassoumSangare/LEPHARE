from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    DemandeAutorisation,
    JetonAutorisation,
    Permission,
    TypeOperation,
    StatutDemande
)


@admin.register(DemandeAutorisation)
class DemandeAutorisationAdmin(admin.ModelAdmin):
    """Interface admin pour les demandes d'autorisation"""
    
    list_display = [
        'id',
        'demandeur_display',
        'type_operation_display',
        'objet_short',
        'statut_badge',
        'approbateur_display',
        'date_demande',
        'jeton_info',
        'actions_admin'
    ]
    
    list_filter = [
        'statut',
        'type_operation',
        'jeton_genere',
        'date_demande',
        'date_traitement'
    ]
    
    search_fields = [
        'objet',
        'motif',
        'demandeur__username',
        'demandeur__email',
        'approbateur__username',
        'approbateur__email'
    ]
    
    readonly_fields = [
        'demandeur',
        'date_demande',
        'created_at',
        'updated_at',
        'approbateur',
        'date_traitement',
        'jeton_genere',
        'objet_concerne_info'
    ]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('demandeur', 'type_operation', 'objet', 'motif', 'date_demande')
        }),
        ('Objet concerné', {
            'fields': ('content_type', 'object_id', 'objet_concerne_info', 'metadata')
        }),
        ('Statut', {
            'fields': ('statut', 'jeton_genere', 'date_expiration')
        }),
        ('Traitement', {
            'fields': ('approbateur', 'date_traitement', 'motif_rejet'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    ordering = ['-date_demande']
    date_hierarchy = 'date_demande'
    
    def demandeur_display(self, obj):
        """Affichage formaté du demandeur"""
        if obj.demandeur:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.demandeur.get_full_name() or obj.demandeur.username,
                obj.demandeur.email
            )
        return '-'
    demandeur_display.short_description = 'Demandeur'
    
    def approbateur_display(self, obj):
        """Affichage formaté de l'approbateur"""
        if obj.approbateur:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.approbateur.get_full_name() or obj.approbateur.username,
                obj.approbateur.email
            )
        return '-'
    approbateur_display.short_description = 'Approbateur'
    
    def type_operation_display(self, obj):
        """Affichage du type d'opération"""
        colors = {
            'ANNUL_ENC': '#dc3545',
            'ANNUL_REV': '#fd7e14',
            'MODIF_CNT': '#ffc107',
        }
        color = colors.get(obj.type_operation, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_type_operation_display()
        )
    type_operation_display.short_description = 'Type'
    
    def objet_short(self, obj):
        """Objet tronqué"""
        if len(obj.objet) > 50:
            return obj.objet[:50] + '...'
        return obj.objet
    objet_short.short_description = 'Objet'
    
    def statut_badge(self, obj):
        """Badge coloré pour le statut"""
        colors = {
            'PENDING': '#ffc107',
            'APPROVED': '#28a745',
            'REJECTED': '#dc3545',
            'EXPIRED': '#6c757d',
            'USED': '#17a2b8',
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def jeton_info(self, obj):
        """Informations sur le jeton"""
        if obj.jeton_genere:
            try:
                jeton = obj.jeton
                if jeton.utilise:
                    return format_html(
                        '<span style="color: #28a745;">✓ Utilisé</span><br>'
                        '<small>{}</small>',
                        jeton.date_utilisation.strftime('%d/%m/%Y %H:%M')
                    )
                elif timezone.now() > jeton.date_expiration:
                    return format_html('<span style="color: #dc3545;">⏰ Expiré</span>')
                else:
                    return format_html(
                        '<span style="color: #28a745;">✓ Valide</span><br>'
                        '<small>Expire le {}</small>',
                        jeton.date_expiration.strftime('%d/%m/%Y %H:%M')
                    )
            except JetonAutorisation.DoesNotExist:
                return format_html('<span style="color: #ffc107;">⚠ Erreur</span>')
        return '-'
    jeton_info.short_description = 'Jeton'
    
    def objet_concerne_info(self, obj):
        """Informations sur l'objet concerné"""
        if obj.objet_concerne:
            return format_html(
                '<strong>Type:</strong> {}<br>'
                '<strong>ID:</strong> {}<br>'
                '<strong>Représentation:</strong> {}',
                obj.content_type,
                obj.object_id,
                str(obj.objet_concerne)
            )
        return 'Aucun objet lié'
    objet_concerne_info.short_description = 'Objet concerné'
    
    def actions_admin(self, obj):
        """Actions rapides"""
        if obj.statut == StatutDemande.EN_ATTENTE:
            return format_html(
                '<a class="button" href="#">Approuver</a> '
                '<a class="button" href="#">Rejeter</a>'
            )
        return '-'
    actions_admin.short_description = 'Actions'
    
    def has_delete_permission(self, request, obj=None):
        """Empêche la suppression sauf pour les superusers"""
        return request.user.is_admin


@admin.register(JetonAutorisation)
class JetonAutorisationAdmin(admin.ModelAdmin):
    """Interface admin pour les jetons"""
    
    list_display = [
        'code',
        'demande_info',
        'statut_badge',
        'date_generation',
        'date_expiration_display',
        'utilisation_info'
    ]
    
    list_filter = [
        'utilise',
        'date_generation',
        'date_expiration'
    ]
    
    search_fields = [
        'code',
        'demande__objet',
        'demande__demandeur__username',
        'ip_utilisation'
    ]
    
    readonly_fields = [
        'demande',
        'code',
        'date_generation',
        'date_expiration',
        'utilise',
        'date_utilisation',
        'ip_utilisation',
        'user_agent',
        'validite_info'
    ]
    
    fieldsets = (
        ('Informations du jeton', {
            'fields': ('code', 'demande', 'validite_info')
        }),
        ('Dates', {
            'fields': ('date_generation', 'date_expiration')
        }),
        ('Utilisation', {
            'fields': ('utilise', 'date_utilisation', 'ip_utilisation', 'user_agent')
        })
    )
    
    ordering = ['-date_generation']
    date_hierarchy = 'date_generation'
    
    def demande_info(self, obj):
        """Lien vers la demande"""
        url = reverse('admin:autorisations_demandeautorisation_change', args=[obj.demande.id])
        return format_html(
            '<a href="{}">{}</a><br><small>Par: {}</small>',
            url,
            obj.demande.objet[:30] + '...' if len(obj.demande.objet) > 30 else obj.demande.objet,
            obj.demande.demandeur.username
        )
    demande_info.short_description = 'Demande'
    
    def statut_badge(self, obj):
        """Badge du statut"""
        if obj.utilise:
            color = '#17a2b8'
            texte = 'Utilisé'
        elif timezone.now() > obj.date_expiration:
            color = '#dc3545'
            texte = 'Expiré'
        else:
            color = '#28a745'
            texte = 'Valide'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            texte
        )
    statut_badge.short_description = 'Statut'
    
    def date_expiration_display(self, obj):
        """Affichage de la date d'expiration"""
        now = timezone.now()
        if obj.date_expiration < now:
            return format_html(
                '<span style="color: #dc3545;">{}</span>',
                obj.date_expiration.strftime('%d/%m/%Y %H:%M')
            )
        return obj.date_expiration.strftime('%d/%m/%Y %H:%M')
    date_expiration_display.short_description = 'Expiration'
    
    def utilisation_info(self, obj):
        """Informations d'utilisation"""
        if obj.utilise:
            return format_html(
                '<strong>{}</strong><br>'
                '<small>IP: {}</small>',
                obj.date_utilisation.strftime('%d/%m/%Y %H:%M'),
                obj.ip_utilisation or 'N/A'
            )
        return '-'
    utilisation_info.short_description = 'Utilisation'
    
    def validite_info(self, obj):
        """Informations détaillées sur la validité"""
        now = timezone.now()
        est_valide = obj.est_valide()
        
        info = []
        if obj.utilise:
            info.append(f'❌ Jeton déjà utilisé le {obj.date_utilisation.strftime("%d/%m/%Y à %H:%M")}')
        else:
            info.append('✅ Jeton non utilisé')
        
        if now > obj.date_expiration:
            info.append(f'❌ Jeton expiré depuis le {obj.date_expiration.strftime("%d/%m/%Y à %H:%M")}')
        else:
            temps_restant = obj.date_expiration - now
            heures = int(temps_restant.total_seconds() / 3600)
            info.append(f'✅ Valide encore {heures}h')
        
        if est_valide:
            info.append('✅ JETON VALIDE')
        else:
            info.append('❌ JETON INVALIDE')
        
        return format_html('<br>'.join(info))
    validite_info.short_description = 'Validité détaillée'
    
    def has_add_permission(self, request):
        """Empêche la création manuelle"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Empêche la suppression"""
        return request.user.is_admin


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Interface admin pour les permissions"""
    
    list_display = [
        'utilisateur_display',
        'type_operation_display',
        'actif_badge',
        'created_at'
    ]
    
    list_filter = [
        'type_operation',
        'actif',
        'created_at'
    ]
    
    search_fields = [
        'utilisateur__username',
        'utilisateur__email',
        'utilisateur__name',
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Permission', {
            'fields': ('utilisateur', 'type_operation', 'actif')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    ordering = ['-created_at']
    
    def utilisateur_display(self, obj):
        """Affichage formaté de l'utilisateur"""
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.utilisateur.get_full_name() or obj.utilisateur.username,
            obj.utilisateur.email
        )
    utilisateur_display.short_description = 'Utilisateur'
    
    def type_operation_display(self, obj):
        """Affichage du type d'opération"""
        return obj.get_type_operation_display()
    type_operation_display.short_description = 'Type d\'opération'
    
    def actif_badge(self, obj):
        """Badge actif/inactif"""
        if obj.actif:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">✓ Actif</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">✗ Inactif</span>'
        )
    actif_badge.short_description = 'Statut'