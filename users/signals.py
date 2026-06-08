from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from common.media_compress import compress_model_file_field

from .models import User, UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        try:
            from chat.services import add_user_to_team_thread
            from core_settings.models import BrandMembership

            for mem in BrandMembership.objects.filter(user=instance).select_related('brand'):
                add_user_to_team_thread(instance, brand=mem.brand)
        except Exception:
            pass


@receiver(pre_save, sender=UserProfile)
def compress_profile_avatar(sender, instance, **kwargs):
    compress_model_file_field(instance, 'avatar', model=UserProfile)
