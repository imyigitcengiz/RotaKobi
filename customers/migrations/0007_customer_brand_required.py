from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core_settings', '0060_backfill_tenant_brands'),
        ('customers', '0006_business_brands'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='customers',
                to='core_settings.businessbrand',
                verbose_name='Marka / firma',
            ),
        ),
    ]
