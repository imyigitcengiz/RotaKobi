from django.db import migrations, models

import common.currency


class Migration(migrations.Migration):

    dependencies = [
        ('core_settings', '0045_installation_schedule'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='currency_code',
            field=models.CharField(
                choices=common.currency.CURRENCY_CODE_CHOICES,
                default=common.currency.DEFAULT_CURRENCY_CODE,
                help_text='Tüm tutar alanları ve raporlarda kullanılır.',
                max_length=3,
                verbose_name='Para birimi',
            ),
        ),
    ]
