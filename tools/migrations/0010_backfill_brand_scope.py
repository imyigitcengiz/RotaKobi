from django.db import migrations


def backfill_brand_scope(apps, schema_editor):
    BusinessBrand = apps.get_model('core_settings', 'BusinessBrand')
    brand = (
        BusinessBrand.objects.filter(is_default=True, is_active=True).first()
        or BusinessBrand.objects.filter(is_active=True).order_by('pk').first()
    )
    if not brand:
        return
    for model_name in ('MapsScrapedFirm', 'OutreachCollection', 'WhatsappConnection'):
        Model = apps.get_model('tools', model_name)
        Model.objects.filter(brand__isnull=True).update(brand_id=brand.pk)
    SupplierPayable = apps.get_model('core_settings', 'SupplierPayable')
    SupplierPayable.objects.filter(brand__isnull=True).update(brand_id=brand.pk)


class Migration(migrations.Migration):
    dependencies = [
        ('tools', '0009_brand_tenant_scope'),
        ('core_settings', '0058_brand_tenant_scope'),
    ]

    operations = [
        migrations.RunPython(backfill_brand_scope, migrations.RunPython.noop),
    ]
