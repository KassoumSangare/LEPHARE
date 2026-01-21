"""
Tâches Celery pour la gestion des commissions
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
import logging

from .models import (
    SnapshotCommission,
    SnapshotCommissionCompagnie,
    CacheDashboard,
    NotificationCommission,
    DetailReversement,
    DetailPaiementCommission,
    User
)
from .services import CommissionCalculService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generer_snapshot_quotidien(self):
    """
    Génère un snapshot quotidien des statistiques de commission
    À exécuter via Celery Beat tous les jours à minuit
    """
    try:
        aujourd_hui = timezone.now().date()
        
        # Vérifier si le snapshot existe déjà
        if SnapshotCommission.objects.filter(date_snapshot=aujourd_hui).exists():
            logger.info(f"Snapshot pour {aujourd_hui} existe déjà")
            return f"Snapshot pour {aujourd_hui} existe déjà"
        
        # Calculer les statistiques globales
        kpi = CommissionCalculService.calculer_kpi_global()
        
        # Créer le snapshot
        snapshot = SnapshotCommission.objects.create(
            date_snapshot=aujourd_hui,
            commissions_dues_total=kpi['commissions_dues_total'],
            commissions_payees_total=kpi['commissions_payees_total'],
            commissions_en_attente_total=kpi['commissions_en_attente'],
            nombre_affaires_total=kpi['nombre_affaires_total'],
            nombre_affaires_payees=kpi['nombre_affaires_payees'],
            nombre_affaires_non_payees=kpi['nombre_affaires_non_payees'],
            nombre_affaires_partielles=kpi['nombre_affaires_partielles'],
            taux_recouvrement=kpi['taux_recouvrement'],
            delai_moyen_paiement_jours=kpi['delai_moyen_paiement']
        )
        
        # Calculer et sauvegarder les statistiques par compagnie
        stats_compagnies = CommissionCalculService.calculer_statistiques_par_compagnie()
        
        for stat in stats_compagnies:
            # Calculer le délai moyen pour cette compagnie
            delai_moyen = DetailPaiementCommission.objects.filter(
                est_annule=False,
                paiement__compagnie_id=stat['quittance__contrat__compagnie__id']
            ).aggregate(
                moyenne=models.Avg(
                    F('paiement__date_paiement') - F('detail_reversement__reversement__date_reversement')
                )
            )['moyenne']
            
            delai_jours = delai_moyen.days if delai_moyen else 0
            
            SnapshotCommissionCompagnie.objects.create(
                snapshot=snapshot,
                compagnie_id=stat['quittance__contrat__compagnie__id'],
                commissions_dues=Decimal(stat['commissions_dues']),
                commissions_payees=Decimal(stat['commissions_payees']),
                commissions_en_attente=Decimal(stat['commissions_en_attente']),
                nombre_affaires=stat['nombre_affaires'],
                delai_moyen_paiement_jours=delai_jours
            )
        
        logger.info(f"Snapshot généré avec succès pour {aujourd_hui}")
        return f"Snapshot créé: {snapshot.id}"
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du snapshot: {str(e)}")
        # Réessayer après 5 minutes
        raise self.retry(exc=e, countdown=300)


@shared_task
def nettoyer_cache_expire():
    """
    Nettoie les entrées de cache expirées
    À exécuter toutes les heures
    """
    try:
        maintenant = timezone.now()
        nb_supprimes = CacheDashboard.objects.filter(
            date_expiration__lt=maintenant
        ).delete()[0]
        
        logger.info(f"{nb_supprimes} entrées de cache expirées supprimées")
        return f"{nb_supprimes} entrées supprimées"
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage du cache: {str(e)}")
        raise


@shared_task
def precalculer_dashboards():
    """
    Précalcule les dashboards principaux pour améliorer les performances
    À exécuter plusieurs fois par jour (ex: toutes les 4 heures)
    """
    try:
        # Dashboard complet
        CommissionCalculService.calculer_kpi_global()
        CommissionCalculService.calculer_statistiques_par_compagnie()
        CommissionCalculService.calculer_commissions_par_anciennete()
        CommissionCalculService.calculer_top_affaires()
        CommissionCalculService.calculer_performance_paiement()
        CommissionCalculService.calculer_taux_conformite()
        
        logger.info("Dashboards précalculés avec succès")
        return "Dashboards précalculés"
        
    except Exception as e:
        logger.error(f"Erreur lors du précalcul des dashboards: {str(e)}")
        raise


@shared_task
def generer_rapport_hebdomadaire():
    """
    Génère et envoie un rapport hebdomadaire par email
    À exécuter tous les lundis matin
    """
    try:
        # Calculer les statistiques de la semaine dernière
        aujourd_hui = timezone.now().date()
        from datetime import timedelta
        semaine_derniere = aujourd_hui - timedelta(days=7)
        
        kpi = CommissionCalculService.calculer_kpi_global(
            date_debut=semaine_derniere,
            date_fin=aujourd_hui
        )
        
        # Construire le message HTML
        html_message = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; }}
                .content {{ padding: 20px; }}
                .metric {{ margin: 10px 0; }}
                .metric-label {{ font-weight: bold; }}
                .metric-value {{ color: #4CAF50; font-size: 1.2em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Rapport Hebdomadaire des Commissions</h1>
                <p>Période: {semaine_derniere} au {aujourd_hui}</p>
            </div>
            <div class="content">
                <h2>Résumé Financier</h2>
                <div class="metric">
                    <span class="metric-label">Commissions dues:</span>
                    <span class="metric-value">{kpi['commissions_dues_total']}€</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Commissions payées:</span>
                    <span class="metric-value">{kpi['commissions_payees_total']}€</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Commissions en attente:</span>
                    <span class="metric-value">{kpi['commissions_en_attente']}€</span>
                </div>
                
                <h2>Performance</h2>
                <div class="metric">
                    <span class="metric-label">Taux de recouvrement:</span>
                    <span class="metric-value">{kpi['taux_recouvrement']}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Délai moyen de paiement:</span>
                    <span class="metric-value">{kpi['delai_moyen_paiement']} jours</span>
                </div>
                
                <h2>Volume d'Affaires</h2>
                <div class="metric">
                    <span class="metric-label">Nombre total d'affaires:</span>
                    <span class="metric-value">{kpi['nombre_affaires_total']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Affaires payées:</span>
                    <span class="metric-value">{kpi['nombre_affaires_payees']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Affaires non payées:</span>
                    <span class="metric-value">{kpi['nombre_affaires_non_payees']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Affaires partiellement payées:</span>
                    <span class="metric-value">{kpi['nombre_affaires_partielles']}</span>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Message texte simple (fallback)
        text_message = f"""
        Rapport Hebdomadaire des Commissions
        
        Période: {semaine_derniere} au {aujourd_hui}
        
        Résumé Financier:
        - Commissions dues: {kpi['commissions_dues_total']}€
        - Commissions payées: {kpi['commissions_payees_total']}€
        - Commissions en attente: {kpi['commissions_en_attente']}€
        
        Performance:
        - Taux de recouvrement: {kpi['taux_recouvrement']}%
        - Délai moyen de paiement: {kpi['delai_moyen_paiement']} jours
        
        Volume d'Affaires:
        - Nombre total d'affaires: {kpi['nombre_affaires_total']}
        - Affaires payées: {kpi['nombre_affaires_payees']}
        - Affaires non payées: {kpi['nombre_affaires_non_payees']}
        - Affaires partiellement payées: {kpi['nombre_affaires_partielles']}
        """
        
        send_mail(
            subject=f'Rapport hebdomadaire commissions - {aujourd_hui}',
            message=text_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=getattr(settings, 'COMMISSION_REPORT_EMAILS', [settings.DEFAULT_FROM_EMAIL]),
            fail_silently=False
        )
        
        logger.info("Rapport hebdomadaire envoyé avec succès")
        return "Rapport envoyé"
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du rapport: {str(e)}")
        raise


@shared_task
def verifier_retards_paiement():
    """
    Vérifie les retards de paiement et crée des notifications
    À exécuter quotidiennement
    """
    try:
        from datetime import timedelta
        from django.contrib.contenttypes.models import ContentType
        
        # Seuil de retard: 60 jours après reversement
        date_limite = timezone.now().date() - timedelta(days=60)
        
        # Récupérer les affaires en retard
        affaires_retard = CommissionCalculService.get_affaires_annotees().filter(
            reversement__date_reversement__lt=date_limite,
            montant_commission_restant__gt=0
        )
        
        # Obtenir les utilisateurs staff pour les notifications
        utilisateurs_staff = User.objects.filter(is_staff=True, is_active=True)
        
        content_type = ContentType.objects.get_for_model(DetailReversement)
        
        nb_notifications = 0
        for affaire in affaires_retard:
            jours_retard = (timezone.now().date() - affaire.reversement.date_reversement).days
            
            for user in utilisateurs_staff:
                # Vérifier si une notification existe déjà pour cette affaire
                notif_existe = NotificationCommission.objects.filter(
                    type_notification='RETARD_PAIEMENT',
                    utilisateur=user,
                    content_type=content_type,
                    object_id=affaire.id,
                    lue=False
                ).exists()
                
                if not notif_existe:
                    NotificationCommission.objects.create(
                        type_notification='RETARD_PAIEMENT',
                        titre=f'Retard de paiement - {affaire.quittance.numero}',
                        message=f'Commission en attente depuis {jours_retard} jours. '
                                f'Montant restant: {affaire.montant_commission_restant}€',
                        utilisateur=user,
                        content_type=content_type,
                        object_id=affaire.id
                    )
                    nb_notifications += 1
        
        logger.info(f"{nb_notifications} notifications de retard créées")
        return f"{nb_notifications} notifications créées"
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des retards: {str(e)}")
        raise


@shared_task
def nettoyer_snapshots_anciens():
    """
    Nettoie les snapshots de plus de 2 ans
    À exécuter mensuellement
    """
    try:
        from datetime import timedelta
        
        date_limite = timezone.now().date() - timedelta(days=730)  # 2 ans
        
        nb_supprimes = SnapshotCommission.objects.filter(
            date_snapshot__lt=date_limite
        ).delete()[0]
        
        logger.info(f"{nb_supprimes} snapshots anciens supprimés")
        return f"{nb_supprimes} snapshots supprimés"
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des snapshots: {str(e)}")
        raise


@shared_task
def envoyer_notification_paiement_recu(paiement_id):
    """
    Envoie une notification lorsqu'un nouveau paiement est reçu
    """
    try:
        from .models import PaiementCommission
        from django.contrib.contenttypes.models import ContentType
        
        paiement = PaiementCommission.objects.get(id=paiement_id)
        
        # Obtenir les utilisateurs staff
        utilisateurs_staff = User.objects.filter(is_staff=True, is_active=True)
        
        content_type = ContentType.objects.get_for_model(PaiementCommission)
        
        for user in utilisateurs_staff:
            NotificationCommission.objects.create(
                type_notification='PAIEMENT_RECU',
                titre=f'Nouveau paiement reçu - {paiement.reference}',
                message=f'Paiement de {paiement.montant_total}€ reçu de {paiement.compagnie.nom}. '
                        f'{paiement.nombre_affaires()} affaires concernées.',
                utilisateur=user,
                content_type=content_type,
                object_id=paiement.id
            )
        
        logger.info(f"Notifications envoyées pour le paiement {paiement.reference}")
        return f"Notifications envoyées pour {paiement.reference}"
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi des notifications: {str(e)}")
        raise


@shared_task
def calculer_previsions_tresorerie():
    """
    Calcule les prévisions de trésorerie pour les 3 prochains mois
    À exécuter hebdomadairement
    """
    try:
        from datetime import timedelta
        
        # Calculer les KPI actuels
        kpi = CommissionCalculService.calculer_kpi_global()
        
        # Prévision simple basée sur la moyenne mensuelle
        # (à affiner selon votre logique métier)
        prevision_mensuelle = kpi['commissions_dues_total'] / 12
        
        previsions = []
        aujourd_hui = timezone.now().date()
        
        for i in range(1, 4):  # 3 prochains mois
            mois_futur = aujourd_hui + timedelta(days=30 * i)
            previsions.append({
                'mois': mois_futur.strftime('%Y-%m'),
                'montant_prevu': str(prevision_mensuelle),
                'date_calcul': timezone.now().isoformat()
            })
        
        logger.info(f"Prévisions calculées: {previsions}")
        return previsions
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul des prévisions: {str(e)}")
        raise