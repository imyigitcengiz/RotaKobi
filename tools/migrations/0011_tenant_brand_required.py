from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core_settings', '0060_backfill_tenant_brands'),
        ('tools', '0010_backfill_brand_scope'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='mapsscrapedfirm',
            name='tools_mapsfirm_unique_place_id',
        ),
        migrations.RemoveConstraint(
            model_name='mapsscrapedfirm',
            name='tools_mapsfirm_unique_phone',
        ),
        migrations.AlterField(
            model_name='mapsscrapedfirm',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='scraped_firms',
                to='core_settings.businessbrand',
                verbose_name='Marka',
            ),
        ),
        migrations.AlterField(
            model_name='outreachcollection',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='outreach_collections',
                to='core_settings.businessbrand',
                verbose_name='Marka',
            ),
        ),
        migrations.AddConstraint(
            model_name='mapsscrapedfirm',
            constraint=models.UniqueConstraint(
                condition=models.Q(('place_id', ''), _negated=True),
                fields=('brand', 'place_id'),
                name='tools_mapsfirm_unique_brand_place_id',
            ),
        ),
        migrations.AddConstraint(
            model_name='mapsscrapedfirm',
            constraint=models.UniqueConstraint(
                condition=models.Q(('phone_normalized', ''), _negated=True),
                fields=('brand', 'phone_normalized'),
                name='tools_mapsfirm_unique_brand_phone',
            ),
        ),
    ]
