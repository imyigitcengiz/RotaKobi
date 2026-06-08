from django.db.models.signals import post_delete, pre_save, post_save
from django.dispatch import receiver

from config.live_sync import publish_live_event
from .models import SalesLead


@receiver(pre_save, sender=SalesLead)
def cache_sales_lead_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = SalesLead.objects.only('status').get(pk=instance.pk)
            instance._prev_status = old.status
        except SalesLead.DoesNotExist:
            instance._prev_status = None
    else:
        instance._prev_status = None


@receiver(post_save, sender=SalesLead)
def on_sales_lead_saved(sender, instance, created, **kwargs):
    brand_id = None
    if instance.customer_id:
        brand_id = getattr(instance.customer, 'brand_id', None)
    publish_live_event(
        kind='sales_lead',
        action='created' if created else 'updated',
        object_id=instance.id,
        message=f"Satış kaydı '{instance.customer.name}' {'eklendi' if created else 'güncellendi'}.",
        brand_id=brand_id,
    )
    # WhatsApp senaryoları otomatik gönderilmez; kullanıcı onayı views + whatsapp_status_prompt ile yapılır.


@receiver(post_delete, sender=SalesLead)
def on_sales_lead_deleted(sender, instance, **kwargs):
    brand_id = None
    if instance.customer_id:
        brand_id = getattr(instance.customer, 'brand_id', None)
    publish_live_event(
        kind='sales_lead',
        action='deleted',
        object_id=instance.id,
        message=f"Satış kaydı '{instance.customer.name}' silindi.",
        brand_id=brand_id,
    )
