

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    MenuParent,
    Menu,
    Garantie,
    SousGarantie,
    GarantieRisque,
    Energie,
    Categorie,
    Tarif,
    TarifDetail,
    Offre,
    OffreDetail,
    Profession,
    Avenant,
    Branche,
    Risque,
    Acte,
    Commission,
    Compagnie,
    Pays,
    Region,
    Ville,
    Intermediaire,
    Carrosserie,
    Qualite,
    Marque,
    SystemeSecurite,
    ModeleVehicule,
    UsageVehicule,
    TypeReduction,
    OffreGarantie,
    Continent,
    ZoneVoyage,
    QualiteAyantDroit,
    UsageVehiculeAsaci,
    TypeVehicule,
    TypeSouscripteur,
    TypeAssure,
    Commune,
    CategoriePermis,
    Produit,
    ProfessionIa,
    Banque,
    ModeEncaissement,
    ParametreSite,
    DelaiAvisEcheance,
    UsageHabitation,
    SousGarantieMRH,
    SousGarantieUsage,
    ParametresCalcul,
    Option,
    OptionUsage,
    CleRepartition,
    SousGarantieForfait
)

admin.site.register(Menu)
admin.site.register(MenuParent)
admin.site.register(Branche)
admin.site.register(Risque)
admin.site.register(Garantie)
admin.site.register(SousGarantie)
admin.site.register(Acte)
admin.site.register(Commission)
admin.site.register(Compagnie)
admin.site.register(Pays)
admin.site.register(Region)
admin.site.register(Ville)
admin.site.register(Commune)
admin.site.register(Intermediaire)
admin.site.register(GarantieRisque)
admin.site.register(Categorie)
admin.site.register(Tarif)
admin.site.register(TarifDetail)
admin.site.register(Offre)
admin.site.register(OffreDetail)
admin.site.register(Profession)
admin.site.register(Energie)
admin.site.register(Avenant)
admin.site.register(Carrosserie)
admin.site.register(Qualite)
admin.site.register(Marque)
admin.site.register(SystemeSecurite)
admin.site.register(ModeleVehicule)
admin.site.register(UsageVehicule)
admin.site.register(TypeReduction)
admin.site.register(OffreGarantie)
admin.site.register(Continent)
admin.site.register(ZoneVoyage)
admin.site.register(QualiteAyantDroit)
admin.site.register(UsageVehiculeAsaci)
admin.site.register(TypeVehicule)
admin.site.register(TypeAssure)
admin.site.register(TypeSouscripteur)
admin.site.register(CategoriePermis)
admin.site.register(Produit)
admin.site.register(ProfessionIa)
admin.site.register(Banque)
admin.site.register(ModeEncaissement)
admin.site.register(ParametreSite)
admin.site.register(DelaiAvisEcheance)

####################################################################################################


# ============================================================================
# ADMIN 1 : USAGE HABITATION
# ============================================================================
@admin.register(UsageHabitation)
class UsageHabitationAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'actif', 'date_creation']
    list_filter = ['actif']
    search_fields = ['code', 'libelle', 'description']
    readonly_fields = ['date_creation', 'date_modification']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('code', 'libelle', 'description', 'actif')
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# ADMIN 2 : GARANTIE MRH
# ============================================================================
@admin.register(SousGarantieMRH)
class SousGarantieMRHAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'type', 'sous_garantie_std_info', 'actif', 'date_creation']
    list_filter = ['type', 'actif']
    search_fields = ['code', 'libelle', 'description']
    readonly_fields = ['date_creation', 'date_modification']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('code', 'libelle', 'type', 'description', 'actif')
        }),
        ('Lien avec stdsousgarantie', {
            'fields': ('sous_garantie_std',),
            'description': 'Lien optionnel avec la table stdsousgarantie existante'
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    def sous_garantie_std_info(self, obj):
        """Affiche les infos de la sous-garantie standard liée"""
        if obj.sous_garantie_std:
            return format_html(
                '<strong>{}</strong> (ID: {})',
                obj.sous_garantie_std.CodeSousGarantie,
                obj.sous_garantie_std.IdSousGarantie
            )
        return format_html('<span style="color: #999;">Non liée</span>')
    sous_garantie_std_info.short_description = 'Sous-Garantie Std'


# ============================================================================
# ADMIN 3 : GARANTIE ↔ USAGE (Inline et Principal)
# ============================================================================
class SousGarantieUsageInline(admin.TabularInline):
    model = SousGarantieUsage
    extra = 1
    fields = ['sous_garantie', 'obligatoire', 'taux_repartition', 'ordre_affichage', 'actif']
    autocomplete_fields = ['sous_garantie']


@admin.register(SousGarantieUsage)
class SousGarantieUsageAdmin(admin.ModelAdmin):
    list_display = ['usage', 'sous_garantie', 'obligatoire', 'taux_repartition', 'ordre_affichage', 'actif']
    list_filter = ['usage', 'obligatoire', 'actif']
    search_fields = ['usage__libelle', 'sous_garantie__libelle']
    autocomplete_fields = ['usage', 'sous_garantie']
    list_editable = ['taux_repartition', 'ordre_affichage']
    
    fieldsets = (
        ('Association', {
            'fields': ('usage', 'sous_garantie')
        }),
        ('Configuration', {
            'fields': ('obligatoire', 'taux_repartition', 'ordre_affichage', 'actif')
        }),
    )


# ============================================================================
# ADMIN 4 : PARAMÈTRES DE CALCUL (Inline)
# ============================================================================
class ParametresCalculInline(admin.StackedInline):
    model = ParametresCalcul
    can_delete = False
    fields = [
        ('coeff_valeur_batiment', 'coeff_valeur_contenu'),
        ('coeff_loyer', 'coeff_capital_rvt'),
        ('coeff_reduction', 'forfait_fixe'),
        ('param_valeur_batiment_requis', 'param_valeur_contenu_requis'),
        ('param_loyer_requis', 'param_capital_rvt_requis'),
        'formule_texte',
        'actif'
    ]


@admin.register(ParametresCalcul)
class ParametresCalculAdmin(admin.ModelAdmin):
    list_display = ['usage', 'formule_texte_court', 'coeff_reduction', 'actif']
    list_filter = ['actif']
    search_fields = ['usage__libelle', 'formule_texte']
    readonly_fields = ['date_creation', 'date_modification']
    
    fieldsets = (
        ('Usage', {
            'fields': ('usage',)
        }),
        ('Coefficients', {
            'fields': (
                ('coeff_valeur_batiment', 'coeff_valeur_contenu'),
                ('coeff_loyer', 'coeff_capital_rvt'),
                ('coeff_reduction', 'forfait_fixe')
            )
        }),
        ('Paramètres requis', {
            'fields': (
                ('param_valeur_batiment_requis', 'param_valeur_contenu_requis'),
                ('param_loyer_requis', 'param_capital_rvt_requis')
            )
        }),
        ('Documentation', {
            'fields': ('formule_texte',)
        }),
        ('État', {
            'fields': ('actif',)
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    def formule_texte_court(self, obj):
        """Affiche une version courte de la formule"""
        if obj.formule_texte:
            return obj.formule_texte[:50] + '...' if len(obj.formule_texte) > 50 else obj.formule_texte
        return '-'
    formule_texte_court.short_description = 'Formule'


# ============================================================================
# ADMIN 5 : OPTION
# ============================================================================
@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'type_option', 'type_ajustement', 'sous_garantie_cible', 'impact_display', 'actif']
    list_filter = ['type_option', 'type_ajustement', 'actif']
    search_fields = ['code', 'libelle', 'description']
    autocomplete_fields = ['sous_garantie_cible']
    readonly_fields = ['date_creation', 'date_modification']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('code', 'libelle', 'description', 'type_option', 'actif')
        }),
        ('Impact', {
            'fields': (
                'type_ajustement',
                'sous_garantie_cible',
                'taux_ajustement',
                'montant_forfait',
                'signe_ajustement'
            )
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    def impact_display(self, obj):
        """Affiche l'impact de l'option de manière lisible"""
        signe = obj.signe_ajustement or ''
        if obj.type_ajustement == 'TYPE1':
            return format_html('<span style="color: {};">{}{} ‰</span>', 
                             'red' if signe == '+' else 'green',
                             signe, obj.taux_ajustement)
        elif obj.type_ajustement == 'TYPE2':
            return format_html('<span style="color: {};">{}{} %</span>', 
                             'red' if signe == '+' else 'green',
                             signe, obj.taux_ajustement)
        elif obj.type_ajustement == 'FORFAIT':
            return format_html('<span style="color: {};">{}{} FCFA</span>', 
                             'red' if signe == '+' else 'green',
                             signe, obj.montant_forfait)
        return '-'
    impact_display.short_description = 'Impact'


# ============================================================================
# ADMIN 6 : OPTION ↔ USAGE
# ============================================================================
class OptionUsageInline(admin.TabularInline):
    model = OptionUsage
    extra = 1
    fields = ['option', 'actif']
    autocomplete_fields = ['option']


@admin.register(OptionUsage)
class OptionUsageAdmin(admin.ModelAdmin):
    list_display = ['option', 'usage', 'actif']
    list_filter = ['usage', 'actif']
    search_fields = ['option__libelle', 'usage__libelle']
    autocomplete_fields = ['option', 'usage']
    
    fieldsets = (
        ('Association', {
            'fields': ('option', 'usage', 'actif')
        }),
    )


# ============================================================================
# ADMIN 7 : CLÉ DE RÉPARTITION
# ============================================================================
@admin.register(CleRepartition)
class CleRepartitionAdmin(admin.ModelAdmin):
    list_display = ['usage', 'sous_garantie', 'type_repartition', 'valeur_display', 'groupe', 'ordre_calcul', 'actif']
    list_filter = ['usage', 'type_repartition', 'groupe', 'actif']
    search_fields = ['usage__libelle', 'sous_garantie__libelle']
    autocomplete_fields = ['usage', 'sous_garantie']
    list_editable = ['ordre_calcul']
    
    fieldsets = (
        ('Association', {
            'fields': ('usage', 'sous_garantie')
        }),
        ('Répartition', {
            'fields': (
                'type_repartition',
                'montant_fixe',
                'taux_pourcentage'
            )
        }),
        ('Ordre', {
            'fields': ('groupe', 'ordre_calcul')
        }),
        ('État', {
            'fields': ('actif',)
        }),
    )
    
    def valeur_display(self, obj):
        """Affiche la valeur selon le type"""
        if obj.type_repartition == 'FIXE':
            return format_html('<strong>{} FCFA</strong>', obj.montant_fixe)
        elif obj.type_repartition == 'POURCENTAGE':
            return format_html('<strong>{} %</strong>', obj.taux_pourcentage)
        return '-'
    valeur_display.short_description = 'Valeur'


# ============================================================================
# ADMIN 8 : GARANTIE FORFAIT
# ============================================================================
@admin.register(SousGarantieForfait)
class SousGarantieForfaitAdmin(admin.ModelAdmin):
    list_display = ['sous_garantie', 'prime_nette', 'actif', 'date_creation']
    list_filter = ['actif']
    search_fields = ['sous_garantie__libelle', 'description']
    autocomplete_fields = ['sous_garantie']
    readonly_fields = ['date_creation', 'date_modification']
    
    fieldsets = (
        ('Sous Garantie', {
            'fields': ('sous_garantie', 'prime_nette', 'description', 'actif')
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# PERSONNALISATION ADMIN USAGE AVEC INLINES
# ============================================================================
# On réenregistre UsageHabitation avec les inlines
admin.site.unregister(UsageHabitation)

@admin.register(UsageHabitation)
class UsageHabitationAdminWithInlines(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'nombre_sous_garanties', 'actif', 'date_creation']
    list_filter = ['actif']
    search_fields = ['code', 'libelle', 'description']
    readonly_fields = ['date_creation', 'date_modification']
    inlines = [ParametresCalculInline, SousGarantieUsageInline, OptionUsageInline]
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('code', 'libelle', 'description', 'actif')
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    def nombre_sous_garanties(self, obj):
        """Compte le nombre de sous-garanties liées"""
        return obj.sous_garanties_liees.filter(actif=True).count()
    nombre_sous_garanties.short_description = 'Nb garanties'


# ============================================================================
# CONFIGURATION DU SITE ADMIN
# ============================================================================
admin.site.site_header = "Administration Uranus"
admin.site.site_title = "Uranus Admin"
admin.site.index_title = "Gestion des contrats d'assurance"

####################################################################################################
