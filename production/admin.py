from django.contrib import admin


from .models import (
    Devis,
    DevisDetail,
    DevisDetGarantie,
    TarifEcran,
    Contrat,
    ContratDetail,
    ContratDetGarantie,
    AyantDroitIa,
    ImpositionPrime,
)

admin.site.register(Devis)
admin.site.register(DevisDetail)
admin.site.register(DevisDetGarantie)
admin.site.register(TarifEcran)
admin.site.register(Contrat)
admin.site.register(ContratDetail)
admin.site.register(ContratDetGarantie)
admin.site.register(AyantDroitIa)

   
@admin.register(ImpositionPrime)
class ImpositionPrimeAdmin(admin.ModelAdmin):
    list_display = [
           'type_imposition', 'id_cible', 'montant_impose', 
           'user_nom', 'date_imposition', 'actif'
       ]
    list_filter = ['type_imposition', 'actif', 'date_imposition']
    search_fields = ['user_nom', 'motif', 'motif_levee']
    readonly_fields = [
           'date_imposition', 'date_levee', 'ancien_montant_nette', 
           'ancien_montant_ttc'
       ]
    fieldsets = (
           ('Informations principales', {
               'fields': (
                   'type_imposition', 'id_cible', 'montant_impose', 'actif'
               )
           }),
           ('Montants avant imposition', {
               'fields': ('ancien_montant_nette', 'ancien_montant_ttc')
           }),
           ('Traçabilité création', {
               'fields': (
                   'user_id', 'user_nom', 'date_imposition', 'motif'
               )
           }),
           ('Traçabilité levée', {
               'fields': (
                   'date_levee', 'levee_par_user_id', 
                   'levee_par_user_nom', 'motif_levee'
               ),
               'classes': ('collapse',)
           }),
       )

