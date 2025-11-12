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
)

admin.site.register(Devis)
admin.site.register(DevisDetail)
admin.site.register(DevisDetGarantie)
admin.site.register(TarifEcran)
admin.site.register(Contrat)
admin.site.register(ContratDetail)
admin.site.register(ContratDetGarantie)
admin.site.register(AyantDroitIa)

# Register your models here.
