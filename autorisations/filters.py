from django_filters import rest_framework as filters
from datetime import datetime
from .models import DemandeAutorisation

class DemandeAutorisationFilter(filters.FilterSet):
    date_demande_min = filters.DateFilter(
        field_name='date_demande', 
        lookup_expr='gte',
        label='Date de début (YYYY-MM-DD)'
    )
    date_demande_max = filters.DateFilter(
        field_name='date_demande', 
        lookup_expr='lte',
        label='Date de fin (YYYY-MM-DD)'
    )
    date_traitement_min = filters.DateFilter(
        field_name='date_traitement', 
        lookup_expr='gte',
        label='Date de traitement de début (YYYY-MM-DD)'
    )
    date_traitement_max = filters.DateFilter(
        field_name='date_traitement', 
        lookup_expr='lte',
        label='Date de traitement de fin (YYYY-MM-DD)'
    )
    
    class Meta:
        model = DemandeAutorisation
        fields = ['statut', 'type_operation', 'demandeur', 'approbateur']
