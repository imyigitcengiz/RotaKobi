"""Null brand_id kayıtlarını varsayılan markaya bağla (NOT NULL öncesi)."""

from django.db import migrations


def _default_brand(apps):
    BusinessBrand = apps.get_model('core_settings', 'BusinessBrand')
    return (
        BusinessBrand.objects.filter(is_default=True, is_active=True).first()
        or BusinessBrand.objects.filter(is_active=True).order_by('pk').first()
    )


def backfill_all_brands(apps, schema_editor):
    brand = _default_brand(apps)
    if not brand:
        return
    bid = brand.pk

    Customer = apps.get_model('customers', 'Customer')
    Customer.objects.filter(brand__isnull=True).update(brand_id=bid)

    ServiceRecord = apps.get_model('services', 'ServiceRecord')
    for row in ServiceRecord.objects.filter(brand__isnull=True).iterator():
        customer_brand = None
        if row.customer_id:
            customer_brand = (
                Customer.objects.filter(pk=row.customer_id)
                .values_list('brand_id', flat=True)
                .first()
            )
        ServiceRecord.objects.filter(pk=row.pk).update(brand_id=customer_brand or bid)

    for app_label, model_name in (
        ('core_settings', 'ServicePersonnel'),
        ('core_settings', 'FinanceRecord'),
        ('core_settings', 'SolutionPartner'),
        ('core_settings', 'SupplierPayable'),
        ('tools', 'MapsScrapedFirm'),
        ('tools', 'OutreachCollection'),
    ):
        Model = apps.get_model(app_label, model_name)
        Model.objects.filter(brand__isnull=True).update(brand_id=bid)


class Migration(migrations.Migration):
    dependencies = [
        ('core_settings', '0059_kobi_hub_site_name_default'),
        ('customers', '0006_business_brands'),
        ('services', '0016_business_brands'),
        ('tools', '0010_backfill_brand_scope'),
    ]

    operations = [
        migrations.RunPython(backfill_all_brands, migrations.RunPython.noop),
    ]
