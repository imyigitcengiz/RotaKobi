from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core_settings', '0060_backfill_tenant_brands'),
        ('services', '0018_servicerecord_warranty_note'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicerecord',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='service_records',
                to='core_settings.businessbrand',
                verbose_name='Marka / firma',
            ),
        ),
    ]
