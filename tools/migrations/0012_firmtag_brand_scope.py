from django.db import migrations, models
import django.db.models.deletion


def backfill_firmtag_brands(apps, schema_editor):
    BusinessBrand = apps.get_model('core_settings', 'BusinessBrand')
    FirmTag = apps.get_model('tools', 'FirmTag')
    brand = (
        BusinessBrand.objects.filter(is_default=True, is_active=True).first()
        or BusinessBrand.objects.filter(is_active=True).order_by('pk').first()
    )
    if not brand:
        return
    FirmTag.objects.filter(brand__isnull=True).update(brand_id=brand.pk)


class Migration(migrations.Migration):
    dependencies = [
        ('core_settings', '0061_tenant_brand_required'),
        ('tools', '0011_tenant_brand_required'),
    ]

    operations = [
        migrations.AddField(
            model_name='firmtag',
            name='brand',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='firm_tags',
                to='core_settings.businessbrand',
                verbose_name='Marka',
            ),
        ),
        migrations.RunPython(backfill_firmtag_brands, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='firmtag',
            name='name',
            field=models.CharField(max_length=60, verbose_name='Etiket'),
        ),
        migrations.AlterField(
            model_name='firmtag',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='firm_tags',
                to='core_settings.businessbrand',
                verbose_name='Marka',
            ),
        ),
        migrations.AddConstraint(
            model_name='firmtag',
            constraint=models.UniqueConstraint(fields=('brand', 'name'), name='tools_firmtag_unique_brand_name'),
        ),
    ]
