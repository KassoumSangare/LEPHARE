"""
Services de logique métier pour la gestion des commissions
"""
from django.db.models import Sum, Count, Avg, F, Q, Case, When, DecimalField, OuterRef, Subquery, Max, Value, CharField
from django.db.models.functions import Coalesce, TruncMonth
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from .models import (
    DetailReversement,
    DetailPaiementCommission,
    PaiementCommission,
    CacheDashboard
)


class CommissionCalculService:
    """
    Service centralisé pour tous les calculs de commission
    """
    
    @staticmethod
    def get_montant_paye_subquery():
        """Sous-requête réutilisable pour le montant payé"""
        return DetailPaiementCommission.objects.filter(
            detail_reversement=OuterRef('id_detail_reversement'),
            est_annule=False
        ).values('detail_reversement').annotate(
            total=Sum('montant_commission_paye')
        ).values('total')
    
    @staticmethod
    def get_affaires_annotees():
        """
        Retourne un queryset annoté avec tous les calculs nécessaires
        """
        montant_paye_subquery = CommissionCalculService.get_montant_paye_subquery()
        
        return DetailReversement.objects.select_related(
            'ligne_encaissement__numeroquittance__client',
            'ligne_encaissement__numeroquittance__contrat__idcompagnie',
            'reversement'
        ).annotate(
            # Calcul du montant commission dû
            montant_commission_du=F('montant_reverse') * F('ligne_encaissement__numeroquittance__taux_commission') / 100,
            
            # Montant payé
            montant_commission_paye=Coalesce(
                Subquery(montant_paye_subquery),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            ),
            
            # Montant restant
            montant_commission_restant=F('montant_commission_du') - F('montant_commission_paye'),
            
            # Statut de paiement
            statut_paiement=Case(
                When(montant_commission_restant=0, then=Value('PAYE')),
                When(
                    Q(montant_commission_paye__gt=0) & Q(montant_commission_restant__gt=0),
                    then=Value('PARTIELLEMENT_PAYE')
                ),
                default=Value('NON_PAYE'),
                output_field=CharField()
            )
        )
    
    @staticmethod
    def calculer_kpi_global(date_debut=None, date_fin=None):
        """
        Calcule les KPI globaux
        """
        queryset = CommissionCalculService.get_affaires_annotees()
        
        # Filtrer par période si spécifié
        if date_debut:
            queryset = queryset.filter(reversement__date_reversement__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(reversement__date_reversement__lte=date_fin)
        
        # Agrégations
        aggregations = queryset.aggregate(
            commissions_dues_total=Coalesce(
                Sum('montant_commission_du'),
                Decimal('0.00')
            ),
            commissions_payees_total=Coalesce(
                Sum('montant_commission_paye'),
                Decimal('0.00')
            ),
            commissions_en_attente=Coalesce(
                Sum('montant_commission_restant'),
                Decimal('0.00')
            ),
            nombre_affaires_total=Count('id'),
            nombre_affaires_payees=Count('id', filter=Q(statut_paiement='PAYE')),
            nombre_affaires_non_payees=Count('id', filter=Q(statut_paiement='NON_PAYE')),
            nombre_affaires_partielles=Count('id', filter=Q(statut_paiement='PARTIELLEMENT_PAYE')),
        )
        
        # Calcul du taux de recouvrement
        if aggregations['commissions_dues_total'] > 0:
            aggregations['taux_recouvrement'] = (
                aggregations['commissions_payees_total'] / 
                aggregations['commissions_dues_total'] * 100
            )
        else:
            aggregations['taux_recouvrement'] = Decimal('0.00')
        
        # Calcul du délai moyen de paiement
        aggregations['delai_moyen_paiement'] = CommissionCalculService.calculer_delai_moyen_paiement()
        
        return aggregations
    
    @staticmethod
    def calculer_delai_moyen_paiement():
        """
        Calcule le délai moyen entre reversement et paiement de commission
        """
        paiements_avec_delai = DetailPaiementCommission.objects.filter(
            est_annule=False
        ).select_related(
            'detail_reversement__reversement',
            'paiement'
        ).annotate(
            delai=F('paiement__date_paiement') - F('detail_reversement__reversement__date_reversement')
        )
        
        delai_moyen = paiements_avec_delai.aggregate(
            moyenne=Avg('delai')
        )['moyenne']
        
        if delai_moyen:
            return delai_moyen.days
        return 0
    
    @staticmethod
    def calculer_statistiques_par_compagnie(date_debut=None, date_fin=None):
        """
        Statistiques détaillées par compagnie
        """
        queryset = CommissionCalculService.get_affaires_annotees()
        
        if date_debut:
            queryset = queryset.filter(reversement__date_reversement__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(reversement__date_reversement__lte=date_fin)
        
        stats = queryset.values(
            'quittance__contrat__idcompagnie__IdCompagnie',
            'quittance__contrat__idcompagnie__RaisonSociale'
        ).annotate(
            commissions_dues=Coalesce(Sum('montant_commission_du'), Decimal('0.00')),
            commissions_payees=Coalesce(Sum('montant_commission_paye'), Decimal('0.00')),
            commissions_en_attente=Coalesce(Sum('montant_commission_restant'), Decimal('0.00')),
            nombre_affaires=Count('id'),
            nombre_payees=Count('id', filter=Q(statut_paiement='PAYE')),
            nombre_non_payees=Count('id', filter=Q(statut_paiement='NON_PAYE')),
            nombre_partielles=Count('id', filter=Q(statut_paiement='PARTIELLEMENT_PAYE')),
        ).order_by('-commissions_dues')
        
        # Calcul du taux de recouvrement par compagnie
        result = []
        for stat in stats:
            stat_dict = dict(stat)
            if stat_dict['commissions_dues'] and stat_dict['commissions_dues'] > 0:
                stat_dict['taux_recouvrement'] = (
                    stat_dict['commissions_payees'] / stat_dict['commissions_dues'] * 100
                )
            else:
                stat_dict['taux_recouvrement'] = Decimal('0.00')
            result.append(stat_dict)
        
        return result
    
    @staticmethod
    def calculer_evolution_mensuelle(annee=None):
        """
        Évolution mensuelle des commissions
        """
        if not annee:
            annee = timezone.now().year
        
        queryset = CommissionCalculService.get_affaires_annotees().filter(
            reversement__date_reversement__year=annee
        )
        
        # Grouper par mois
        evolution = queryset.annotate(
            mois=TruncMonth('reversement__date_reversement')
        ).values('mois').annotate(
            commissions_dues=Coalesce(Sum('montant_commission_du'), Decimal('0.00')),
            commissions_payees=Coalesce(Sum('montant_commission_paye'), Decimal('0.00')),
            commissions_en_attente=Coalesce(Sum('montant_commission_restant'), Decimal('0.00')),
            nombre_affaires=Count('id'),
        ).order_by('mois')
        
        return list(evolution)
    
    @staticmethod
    def calculer_commissions_par_anciennete():
        """
        Répartition des commissions en attente par ancienneté
        """
        aujourd_hui = timezone.now().date()
        
        queryset = CommissionCalculService.get_affaires_annotees().filter(
            montant_commission_restant__gt=0
        )
        
        # Grouper par tranche d'ancienneté
        tranches = [
            ('0-30 jours', 0, 30),
            ('31-60 jours', 31, 60),
            ('61-90 jours', 61, 90),
            ('91-120 jours', 91, 120),
            ('Plus de 120 jours', 121, 99999),
        ]
        
        resultats = []
        for label, jours_min, jours_max in tranches:
            # Calculer l'ancienneté pour chaque affaire
            affaires_tranche = []
            for affaire in queryset:
                jours_attente = (aujourd_hui - affaire.reversement.date_reversement).days
                if jours_min <= jours_attente <= jours_max:
                    affaires_tranche.append(affaire)
            
            montant = sum(a.montant_commission_restant for a in affaires_tranche)
            nombre = len(affaires_tranche)
            
            resultats.append({
                'tranche': label,
                'montant': montant,
                'nombre': nombre
            })
        
        return resultats
    
    @staticmethod
    def calculer_top_affaires(limite=10, critere='commission_due'):
        """
        Top des affaires par critère
        critere: 'commission_due', 'commission_payee', 'commission_restante'
        """
        queryset = CommissionCalculService.get_affaires_annotees()
        
        # Définir le tri selon le critère
        if critere == 'commission_due':
            ordre = '-montant_commission_du'
        elif critere == 'commission_payee':
            ordre = '-montant_commission_paye'
        else:  # commission_restante
            ordre = '-montant_commission_restant'
        
        top = queryset.order_by(ordre)[:limite]
        
        return [
            {
                'detail_reversement_id': item.id,
                'quittance_numero': item.quittance.numeroquittance,
                'contrat_numero': item.quittance.police,
                'client_nom': f"{item.quittance.client.Prenoms} {item.quittance.client.Nom}",
                'compagnie_nom': item.quittance.contrat.idcompagnie.RaisonSociale,
                'montant_commission_du': str(item.montant_commission_du),
                'montant_commission_paye': str(item.montant_commission_paye),
                'montant_commission_restant': str(item.montant_commission_restant),
                'statut': item.statut_paiement,
            }
            for item in top
        ]
    
    @staticmethod
    def calculer_performance_paiement():
        """
        Indicateurs de performance des paiements
        """
        # Délai moyen par compagnie
        delais_compagnie = DetailPaiementCommission.objects.filter(
            est_annule=False
        ).select_related(
            'detail_reversement__reversement',
            'paiement__compagnie'
        ).values(
            'paiement__compagnie__IdCompagnie',
            'paiement__compagnie__RaisonSociale'
        ).annotate(
            delai_moyen=Avg(
                F('paiement__date_paiement') - F('detail_reversement__reversement__date_reversement')
            ),
            nombre_paiements=Count('id')
        )
        
        resultats = []
        for item in delais_compagnie:
            delai_jours = item['delai_moyen'].days if item['delai_moyen'] else 0
            resultats.append({
                'compagnie_id': item['paiement__compagnie__IdCompagnie'],
                'compagnie_nom': item['paiement__compagnie__RaisonSociale'],
                'delai_moyen_jours': delai_jours,
                'nombre_paiements': item['nombre_paiements']
            })
        
        return resultats
    
    @staticmethod
    def calculer_taux_conformite():
        """
        Taux de conformité (paiements sans écart)
        """
        total_paiements = DetailPaiementCommission.objects.filter(
            est_annule=False
        ).count()
        
        if total_paiements == 0:
            return {
                'taux_conformite': Decimal('100.00'),
                'nombre_ecarts': 0,
                'nombre_paiements': 0
            }
        
        # Pour l'instant, nombre d'écarts = 0 (à adapter si vous implémentez le modèle EcartCommission)
        nombre_ecarts = 0
        
        taux = ((total_paiements - nombre_ecarts) / total_paiements * 100)
        
        return {
            'taux_conformite': taux,
            'nombre_ecarts': nombre_ecarts,
            'nombre_paiements': total_paiements
        }


class CommissionCacheService:
    """
    Service de gestion du cache pour les dashboards
    """
    
    @staticmethod
    def get_or_calculate(cle, fonction_calcul, duree_minutes=60, **kwargs):
        """
        Récupère depuis le cache ou calcule et met en cache
        """
        # Vérifier le cache
        donnees_cache = CacheDashboard.get_cache(cle)
        
        if donnees_cache is not None:
            return donnees_cache
        
        # Calculer
        donnees = fonction_calcul(**kwargs)
        
        # Convertir les Decimal en string pour le JSON
        donnees = CommissionCacheService._serialiser_decimals(donnees)
        
        # Mettre en cache
        CacheDashboard.set_cache(cle, donnees, duree_minutes)
        
        return donnees
    
    @staticmethod
    def _serialiser_decimals(obj):
        """Convertit récursivement les Decimal en string"""
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: CommissionCacheService._serialiser_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [CommissionCacheService._serialiser_decimals(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    @staticmethod
    def invalider_cache(pattern=None):
        """
        Invalide le cache (tout ou par pattern)
        """
        CacheDashboard.invalider_cache(pattern)


class AffaireCommissionService:
    """
    Service pour les opérations sur les affaires de commission
    """
    
    @staticmethod
    def get_affaires_eligibles(filtres=None):
        """
        Retourne les affaires éligibles au paiement avec filtres
        """
        queryset = CommissionCalculService.get_affaires_annotees().filter(
            statut_paiement__in=['NON_PAYE', 'PARTIELLEMENT_PAYE']
        )
        
        if not filtres:
            return queryset
        
        # Appliquer les filtres
        if filtres.get('compagnie_id'):
            queryset = queryset.filter(
                quittance__contrat__compagnie_IdCompagnie=filtres['compagnie_id']
            )
        
        if filtres.get('client_nom'):
            queryset = queryset.filter(
                Q(quittance__client__Nom__icontains=filtres['client_nom']) |
                Q(quittance__client__Prenoms__icontains=filtres['client_nom'])
            )
        
        if filtres.get('date_reversement_debut'):
            queryset = queryset.filter(
                reversement__date_reversement__gte=filtres['date_reversement_debut']
            )
        
        if filtres.get('date_reversement_fin'):
            queryset = queryset.filter(
                reversement__date_reversement__lte=filtres['date_reversement_fin']
            )
        
        if filtres.get('montant_restant_min'):
            queryset = queryset.filter(
                montant_commission_restant__gte=filtres['montant_restant_min']
            )
        
        if filtres.get('montant_restant_max'):
            queryset = queryset.filter(
                montant_commission_restant__lte=filtres['montant_restant_max']
            )
        
        if filtres.get('quittance_numero'):
            queryset = queryset.filter(
                quittance__numeroquittance__icontains=filtres['quittance_numero']
            )
        
        if filtres.get('contrat_numero'):
            queryset = queryset.filter(
                quittance__police__icontains=filtres['contrat_numero']
            )
        
        if filtres.get('statut'):
            queryset = queryset.filter(
                statut_paiement=filtres['statut']
            )
        
        # Tri
        ordre = filtres.get('ordre', 'date_reversement_asc')
        if ordre == 'date_reversement_desc':
            queryset = queryset.order_by('-reversement__date_reversement')
        elif ordre == 'montant_restant_desc':
            queryset = queryset.order_by('-montant_commission_restant')
        elif ordre == 'montant_restant_asc':
            queryset = queryset.order_by('montant_commission_restant')
        else:  # date_reversement_asc (défaut)
            queryset = queryset.order_by('reversement__date_reversement')
        
        # Limite
        if filtres.get('limite'):
            queryset = queryset[:filtres['limite']]
        
        return queryset
    
    @staticmethod
    def serialiser_affaire(affaire):
        """
        Sérialise une affaire en dictionnaire
        """
        
        return {
            'detail_reversement_id': affaire.id_detail_reversement,
            'quittance_id': affaire.quittance.id,
            'quittance_numero': affaire.quittance.numero,
            'contrat_id': affaire.quittance.contrat.id,
            'contrat_numero': affaire.quittance.contrat.numero,
            'client_id': affaire.quittance.contrat.client.id,
            'client_nom': affaire.quittance.contrat.client.nom,
            'client_prenom': affaire.quittance.contrat.client.prenom,
            'client_nom_complet': f"{affaire.quittance.contrat.client.prenom} {affaire.quittance.contrat.client.nom}",
            'compagnie_id': affaire.quittance.contrat.compagnie.id,
            'compagnie_nom': affaire.quittance.contrat.compagnie.nom,
            'reversement_id': affaire.reversement.id,
            'date_reversement': affaire.reversement.date_reversement,
            'montant_prime_reversee': str(affaire.montant_reverse),
            'taux_commission': str(affaire.taux_commission),
            'montant_commission_du': str(affaire.montant_commission_du),
            'montant_commission_paye': str(affaire.montant_commission_paye),
            'montant_commission_restant': str(affaire.montant_commission_restant),
            'derniere_date_paiement': AffaireCommissionService._get_derniere_date_paiement(affaire),
            'statut_paiement': affaire.statut_paiement,
        }
    
    @staticmethod
    def _get_derniere_date_paiement(affaire):
        """Récupère la dernière date de paiement pour une affaire"""
        dernier_paiement = DetailPaiementCommission.objects.filter(
            detail_reversement=affaire,
            est_annule=False
        ).order_by('-paiement__date_paiement').first()
        
        if dernier_paiement:
            return dernier_paiement.paiement.date_paiement
        return None


class PaiementCommissionService:
    """
    Service pour les opérations de paiement de commission
    """
    
    @staticmethod
    def creer_paiement_batch(data, user):
        """
        Crée un paiement de commission par lot
        """
        from django.db import transaction
        from .models import Compagnie
        
        with transaction.atomic():
            # Calculer le montant total
            montant_total = sum(
                item['montant_commission_paye'] 
                for item in data['affaires']
            )
            
            # Créer le paiement principal
            paiement = PaiementCommission.objects.create(
                reference=data['reference'],
                compagnie_id=data['compagnie_id'],
                date_paiement=data['date_paiement'],
                montant_total=montant_total,
                fichier_detail=data.get('fichier_detail'),
                notes=data.get('notes', ''),
                created_by=user,
                statut='EN_ATTENTE'
            )
            
            # Récupérer les informations des reversements
            detail_reversement_ids = [
                item['detail_reversement_id'] 
                for item in data['affaires']
            ]
            
            reversements = DetailReversement.objects.filter(
                id_detail_reversement__in=detail_reversement_ids
            ).select_related('ligne_encaissement__numeroquittance')
            
            reversements_dict = {r.id: r for r in reversements}
            
            # Créer les détails
            for item in data['affaires']:
                reversement = reversements_dict[item['detail_reversement_id']]
                
                # Calculer le montant commission dû
                montant_commission_du = (
                    reversement.montant_reverse * reversement.ligne_encaissement.numeroquittance.taux_commission / Decimal('100')
                )
                
                DetailPaiementCommission.objects.create(
                    paiement=paiement,
                    quittance=reversement.ligne_encaissement.numeroquittance,
                    detail_reversement=reversement,
                    montant_prime_reversee=reversement.montant_reverse,
                    taux_commission=reversement.ligne_encaissement.numeroquittance.taux_commission,
                    montant_commission_du=montant_commission_du,
                    montant_commission_paye=item['montant_commission_paye'],
                    reference_affaire=item.get('reference_affaire', ''),
                )
            
            return paiement
    
    @staticmethod
    def annuler_paiements(data, user):
        """
        Annule une sélection de paiements
        """
        from django.db import transaction
        from .models import AnnulationPaiementCommission, DetailAnnulation
        
        with transaction.atomic():
            # Créer l'annulation
            annulation = AnnulationPaiementCommission.objects.create(
                reference=data['reference'],
                motif=data['motif'],
                annule_par=user
            )
            
            # Récupérer les détails à annuler
            details = DetailPaiementCommission.objects.filter(
                id__in=data['details_paiement_ids'],
                est_annule=False
            )
            
            # Marquer les détails comme annulés et créer les liens
            commentaires = data.get('commentaires', {})
            for detail in details:
                detail.est_annule = True
                detail.save()
                
                DetailAnnulation.objects.create(
                    annulation=annulation,
                    detail_paiement=detail,
                    commentaire=commentaires.get(str(detail.id), '')
                )
            
            return annulation