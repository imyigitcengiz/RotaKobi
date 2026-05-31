from django.db import models
from customers.models import Customer
from django.conf import settings
from core_settings.models import ServiceTypeOption, ProductOption, StatusOption, PriorityOption, SolutionPartner, ServicePersonnel
from django.utils import timezone

class ServiceRecord(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='service_records')
    solution_partner = models.ForeignKey(
        SolutionPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_records',
        verbose_name='Çözüm ortağı',
    )
    status = models.ForeignKey(StatusOption, on_delete=models.PROTECT, verbose_name="Durum")
    priority = models.ForeignKey(PriorityOption, on_delete=models.PROTECT, verbose_name="Öncelik")
    
    products = models.ManyToManyField(ProductOption, blank=True, verbose_name="Ürünler")
    service_types = models.ManyToManyField(ServiceTypeOption, blank=True, verbose_name="Servis Tipleri")
    
    notes = models.TextField(verbose_name="Servis Notları", blank=True, null=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_services', verbose_name="Atanan Kişi / Ekip")
    service_personnel = models.ForeignKey(
        ServicePersonnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services',
        verbose_name='Servis personeli',
    )
    
    WARRANTY_STATUS_CHOICES = [
        ('active', 'Garanti Devam Ediyor'),
        ('expired', 'Garanti Bitti'),
    ]
    warranty_status = models.CharField(max_length=20, choices=WARRANTY_STATUS_CHOICES, default='active', verbose_name="Garanti Durumu")

    list_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Normal fiyat',
    )
    discounted_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='İndirimli fiyat',
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Planlanan randevu',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_warranty_active(self):
        if self.warranty_status == 'expired' or 'ücretli' in self.status.name.lower():
            return False
        return True

    @staticmethod
    def status_name_is_paid(status_name: str) -> bool:
        return 'ücretli' in (status_name or '').lower()

    def requires_pricing_fields(self) -> bool:
        if self.warranty_status == 'expired':
            return True
        if self.status_id and self.status_name_is_paid(self.status.name):
            return True
        return False

    def __str__(self):
        return f"{self.customer.name} ({self.status.name})"

def service_image_path(instance, filename):
    return f'services/{instance.service.customer.name}/{filename}'

class ServiceImage(models.Model):
    service = models.ForeignKey(ServiceRecord, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=service_image_path)
    created_at = models.DateTimeField(auto_now_add=True)

class ServiceHistory(models.Model):
    service = models.ForeignKey(ServiceRecord, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.TextField()
    snapshot = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ServiceVersion(models.Model):
    service = models.ForeignKey(ServiceRecord, on_delete=models.CASCADE, related_name='versions')
    version_no = models.PositiveIntegerField(verbose_name="Versiyon No")
    snapshot = models.JSONField(verbose_name="Servis Snapshot")
    summary = models.CharField(max_length=255, blank=True, default='', verbose_name="Özet")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_no']
        unique_together = ('service', 'version_no')

    def __str__(self):
        return f"Servis #{self.service_id} v{self.version_no}"
