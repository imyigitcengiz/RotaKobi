from django.db import migrations, models
from django.utils import timezone


def mark_existing_setups_complete(apps, schema_editor):
    SiteSettings = apps.get_model('core_settings', 'SiteSettings')
    now = timezone.now()
    SiteSettings.objects.filter(profile_setup_completed_at__isnull=True).update(
        profile_setup_completed_at=now,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core_settings', '0030_sitesettings_module_catalog'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='profile_setup_completed_at',
            field=models.DateTimeField(
                blank=True,
                help_text='İlk kurulum sihirbazı tamamlandığında doldurulur.',
                null=True,
                verbose_name='Profil kurulumu tamamlandı',
            ),
        ),
        migrations.RunPython(mark_existing_setups_complete, migrations.RunPython.noop),
    ]
