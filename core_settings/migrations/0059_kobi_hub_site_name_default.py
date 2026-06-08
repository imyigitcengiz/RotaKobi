from django.db import migrations, models


def rename_coolops_to_kobi_hub(apps, schema_editor):
    SiteSettings = apps.get_model('core_settings', 'SiteSettings')
    SiteSettings.objects.filter(site_name='CoolOPS').update(site_name='Kobi Hub')


class Migration(migrations.Migration):
    dependencies = [
        ('core_settings', '0058_brand_tenant_scope'),
    ]

    operations = [
        migrations.RunPython(rename_coolops_to_kobi_hub, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='sitesettings',
            name='site_name',
            field=models.CharField(default='Kobi Hub', max_length=255),
        ),
    ]
