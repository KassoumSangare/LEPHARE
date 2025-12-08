from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model
from .models import DemandeAutorisation, JetonAutorisation, Permission
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,)
)
def envoyer_notification_nouvelle_demande(self, demande_id):
    """
    Envoie une notification aux approbateurs pour une nouvelle demande
    
    Args:
        demande_id: ID de la demande d'autorisation
    """
    try:
        demande = DemandeAutorisation.objects.select_related(
            'demandeur', 'content_type'
        ).get(id=demande_id)
        
        # Obtenir les approbateurs pour ce type d'opération
        approbateurs = Permission.obtenir_approbateurs(demande.type_operation)
        
        if not approbateurs.exists():
            logger.warning(
                f"Aucun approbateur trouvé pour la demande {demande_id} "
                f"de type {demande.type_operation}"
            )
            return
        
        # Préparer les emails des destinataires
        destinataires = [user.email for user in approbateurs if user.email]
        
        if not destinataires:
            logger.warning(f"Aucun email valide pour les approbateurs de la demande {demande_id}")
            return
        
        # Contexte pour le template
        context = {
            'demande': demande,
            'demandeur': demande.demandeur,
            'type_operation': demande.get_type_operation_display(),
            'objet': demande.objet,
            'motif': demande.motif,
            'date_demande': demande.date_demande,
            'url_application': settings.FRONTEND_URL,
        }
        
        # Informations spécifiques selon le type - Accès à l'objet via GenericForeignKey
        if demande.objet_concerne:
            objet = demande.objet_concerne
            context['objet_concerne'] = objet
            
            # Si c'est un encaissement, ajouter les détails
            if hasattr(objet, 'numeropiece') and hasattr(objet, 'montantencaissement'):
                context.update({
                    'reference': objet.numeropiece,
                    'montant': objet.montantencaissement,
                })

        
        # Générer le contenu HTML
        html_content = render_to_string(
            'emails/nouvelle_demande_autorisation.html',
            context
        )
        
        # Générer le contenu texte (fallback)
        text_content = strip_tags(html_content)
        
        # Créer et envoyer l'email
        subject = f"[Autorisation requise] {demande.get_type_operation_display()}"
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinataires,
        )
        email.attach_alternative(html_content, "text/html")
        
        sent_count = email.send(fail_silently=False)
        
        logger.info(
            f"Notification envoyée pour la demande {demande_id} "
            f"à {len(destinataires)} approbateurs"
        )
        
        return {
            'demande_id': demande_id,
            'destinataires_count': len(destinataires),
            'sent': sent_count
        }
        
    except DemandeAutorisation.DoesNotExist:
        logger.error(f"Demande {demande_id} introuvable")
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de notification pour demande {demande_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,)
)
def envoyer_jeton_autorisation(self, jeton_id):
    """
    Envoie le jeton d'autorisation au demandeur
    
    Args:
        jeton_id: ID du jeton d'autorisation
    """
    try:
        jeton = JetonAutorisation.objects.select_related(
            'demande__demandeur',
            'demande__approbateur',
            'demande__content_type'
        ).get(id=jeton_id)
        
        demande = jeton.demande
        destinataire = demande.demandeur.email
        
        if not destinataire:
            logger.warning(
                f"Le demandeur {demande.demandeur.username} "
                f"n'a pas d'email configuré"
            )
            return
        
        # Contexte pour le template
        context = {
            'demande': demande,
            'jeton': jeton,
            'demandeur': demande.demandeur,
            'approbateur': demande.approbateur,
            'code': jeton.code,
            'date_expiration': jeton.date_expiration,
            'type_operation': demande.get_type_operation_display(),
            'url_application': settings.FRONTEND_URL,
        }
        
        # Informations spécifiques - Accès via GenericForeignKey
        if demande.objet_concerne:
            objet = demande.objet_concerne
            context['objet_concerne'] = objet
            
            # Si c'est un encaissement
            if hasattr(objet, 'numeropiece') and hasattr(objet, 'montantencaissement'):
                context.update({
                    'reference': objet.numeropiece,
                    'montant': objet.montantencaissement,
                })
        
        # Générer le contenu
        html_content = render_to_string(
            'emails/jeton_autorisation.html',
            context
        )
        text_content = strip_tags(html_content)
        
        # Créer et envoyer l'email
        subject = f"[Autorisation accordée] Votre code d'autorisation : {jeton.code}"
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinataire],
        )
        email.attach_alternative(html_content, "text/html")
        
        sent_count = email.send(fail_silently=False)
        
        logger.info(
            f"Jeton {jeton.code} envoyé au demandeur "
            f"{demande.demandeur.username}"
        )
        
        return {
            'jeton_id': jeton_id,
            'code': jeton.code,
            'destinataire': destinataire,
            'sent': sent_count
        }
        
    except JetonAutorisation.DoesNotExist:
        logger.error(f"Jeton {jeton_id} introuvable")
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du jeton {jeton_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,)
)
def envoyer_notification_rejet(self, demande_id):
    """
    Envoie une notification de rejet au demandeur
    
    Args:
        demande_id: ID de la demande d'autorisation
    """
    try:
        demande = DemandeAutorisation.objects.select_related(
            'demandeur',
            'approbateur',
            'content_type'
        ).get(id=demande_id)
        
        destinataire = demande.demandeur.email
        
        if not destinataire:
            logger.warning(
                f"Le demandeur {demande.demandeur.username} "
                f"n'a pas d'email configuré"
            )
            return
        
        # Contexte pour le template
        context = {
            'demande': demande,
            'demandeur': demande.demandeur,
            'approbateur': demande.approbateur,
            'type_operation': demande.get_type_operation_display(),
            'motif_rejet': demande.motif_rejet,
            'date_traitement': demande.date_traitement,
            'url_application': settings.FRONTEND_URL,
        }
        
        # Informations spécifiques - Accès via GenericForeignKey
        if demande.objet_concerne:
            objet = demande.objet_concerne
            context['objet_concerne'] = objet
            
            # Si c'est un encaissement
            if hasattr(objet, 'numeropiece') and hasattr(objet, 'montantencaissement'):
                context.update({
                    'reference': objet.numeropiece,
                    'montant': objet.montantencaissement,
                })
        
        # Générer le contenu
        html_content = render_to_string(
            'emails/demande_rejetee.html',
            context
        )
        text_content = strip_tags(html_content)
        
        # Créer et envoyer l'email
        subject = f"[Demande rejetée] {demande.get_type_operation_display()}"
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinataire],
        )
        email.attach_alternative(html_content, "text/html")
        
        sent_count = email.send(fail_silently=False)
        
        logger.info(
            f"Notification de rejet envoyée au demandeur "
            f"{demande.demandeur.username} pour la demande {demande_id}"
        )
        
        return {
            'demande_id': demande_id,
            'destinataire': destinataire,
            'sent': sent_count
        }
        
    except DemandeAutorisation.DoesNotExist:
        logger.error(f"Demande {demande_id} introuvable")
        raise
    except Exception as e:
        logger.error(
            f"Erreur lors de l'envoi de notification de rejet "
            f"pour demande {demande_id}: {str(e)}"
        )
        raise self.retry(exc=e)


@shared_task
def nettoyer_jetons_expires():
    """
    Tâche périodique pour nettoyer les jetons expirés
    À exécuter quotidiennement via Celery Beat
    """
    from django.utils import timezone
    
    jetons_expires = JetonAutorisation.objects.filter(
        date_expiration__lt=timezone.now(),
        utilise=False
    )
    
    count = jetons_expires.count()
    
    # Mettre à jour les demandes associées
    DemandeAutorisation.objects.filter(
        jeton__in=jetons_expires
    ).update(statut='EXPIRED')
    
    logger.info(f"{count} jetons expirés nettoyés")
    
    return {'jetons_expires': count}