from django.db.models.signals import post_save
from .models import UranusUser
from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import Profile


@receiver(post_save, sender=UranusUser)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(utilisateur=instance)


@receiver(post_save, sender=UranusUser)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()
