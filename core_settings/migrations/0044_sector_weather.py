"""Sektör profili + hava durumu alanları; weather modülü mevcut kurulumlara."""

from django.db import migrations, models

WEATHER_SLUG = 'integration_weather'
LEGACY_TO_SECTOR = {
    'kobi': 'montaj_saha',
    'agency': 'hizmet_danismanlik',
    'retail': 'bayi_servis',
    'healthcare': 'evde_bakim',
    'nonprofit': 'stk_dernek',
}


def migrate_vertical_and_weather(apps, schema_editor):
    SiteSettings = apps.get_model('core_settings', 'SiteSettings')
    settings = SiteSettings.objects.first()
    if not settings:
        return
    slug = settings.primary_vertical_slug or 'kobi'
    if slug in LEGACY_TO_SECTOR:
        settings.primary_vertical_slug = LEGACY_TO_SECTOR[slug]
    elif slug not in (
        'montaj_saha', 'bayi_servis', 'insaat_taahhut',
        'hizmet_danismanlik', 'evde_bakim', 'stk_dernek',
    ):
        settings.primary_vertical_slug = 'montaj_saha'
    slugs = list(settings.enabled_module_slugs or [])
    if WEATHER_SLUG not in slugs:
        slugs.append(WEATHER_SLUG)
        settings.enabled_module_slugs = slugs
    if not settings.weather_city:
        settings.weather_city = 'İstanbul'
    settings.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core_settings', '0043_finance_default_cash_account'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='primary_vertical_slug',
            field=models.CharField(
                default='montaj_saha',
                help_text='Kurumsal sektör tipi — modül paketi bu profile göre önerilir.',
                max_length=32,
                verbose_name='Birincil sektör profili',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='weather_city',
            field=models.CharField(
                blank=True,
                default='İstanbul',
                help_text='Open-Meteo ile otomatik koordinat çözülür; API anahtarı gerekmez.',
                max_length=120,
                verbose_name='Hava durumu şehri',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='weather_latitude',
            field=models.FloatField(blank=True, null=True, verbose_name='Hava enlem'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='weather_longitude',
            field=models.FloatField(blank=True, null=True, verbose_name='Hava boylam'),
        ),
        migrations.RunPython(migrate_vertical_and_weather, migrations.RunPython.noop),
    ]
