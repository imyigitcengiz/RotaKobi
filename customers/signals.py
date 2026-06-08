from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from config.live_sync import publish_live_event
from .models import Customer


@receiver(post_save, sender=Customer)
def on_customer_saved(sender, instance, created, **kwargs):
    publish_live_event(
        kind="customer",
        action="created" if created else "updated",
        object_id=instance.id,
        message=f"Müşteri '{instance.name}' {'eklendi' if created else 'güncellendi'}.",
        brand_id=getattr(instance, 'brand_id', None),
    )
    # WhatsApp: müşteri oluşturma mesajı kullanıcı onayı ile (customers/views.py).


@receiver(post_delete, sender=Customer)
def on_customer_deleted(sender, instance, **kwargs):
    publish_live_event(
        kind="customer",
        action="deleted",
        object_id=instance.id,
        message=f"Müşteri '{instance.name}' silindi.",
        brand_id=getattr(instance, 'brand_id', None),
    )


@receiver(m2m_changed, sender=Customer.products.through)
def on_customer_products_changed(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        publish_live_event(
            kind="customer",
            action="updated",
            object_id=instance.id,
            message=f"Müşteri '{instance.name}' ürünleri güncellendi.",
            brand_id=getattr(instance, 'brand_id', None),
        )
