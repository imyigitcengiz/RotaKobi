from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core_settings', '0036_remove_profile_and_agency_modules'),
    ]

    operations = [
        migrations.CreateModel(
            name='CashSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('opening_balance', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=14, verbose_name='Açılış bakiyesi (₺)')),
                ('opening_date', models.DateField(blank=True, null=True, verbose_name='Açılış tarihi')),
                ('include_payroll_in_balance', models.BooleanField(default=True, verbose_name='Maaş/avans ödemelerini kasadan düş')),
                ('include_sales_collections_in_balance', models.BooleanField(default=True, verbose_name='Satış tahsilatlarını (peşinat + ara ödeme) kasaya ekle')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Kasa ayarları',
                'verbose_name_plural': 'Kasa ayarları',
            },
        ),
    ]
