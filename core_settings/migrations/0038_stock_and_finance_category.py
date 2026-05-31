from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sales_leads', '0006_sales_quote'),
        ('services', '0015_servicerecord_scheduled_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core_settings', '0037_cash_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='financerecord',
            name='category',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Yalnızca gider kayıtlarında anlamlıdır.',
                max_length=20,
                verbose_name='Gider kategorisi',
            ),
        ),
        migrations.AddField(
            model_name='productoption',
            name='min_stock_level',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Bu seviyenin altında uyarı gösterilir.',
                verbose_name='Kritik stok seviyesi',
            ),
        ),
        migrations.AddField(
            model_name='productoption',
            name='stock_quantity',
            field=models.IntegerField(default=0, verbose_name='Mevcut stok (adet)'),
        ),
        migrations.AddField(
            model_name='productoption',
            name='track_stock',
            field=models.BooleanField(
                default=False,
                help_text='Açıksa giriş/çıkış hareketleri bu ürün için izlenir.',
                verbose_name='Stok takibi',
            ),
        ),
        migrations.CreateModel(
            name='StockSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auto_deduct_on_sale', models.BooleanField(default=True, verbose_name='Tamamlanan satışta stok düş')),
                ('auto_deduct_on_service', models.BooleanField(default=False, verbose_name='Servis kaydında stok düş (ürün başına 1 adet)')),
                ('block_negative_stock', models.BooleanField(default=True, verbose_name='Stok eksiye düşmesin')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Stok ayarları',
                'verbose_name_plural': 'Stok ayarları',
            },
        ),
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delta', models.IntegerField(verbose_name='Değişim (+/− adet)')),
                ('quantity_after', models.IntegerField(verbose_name='Sonraki stok')),
                ('reason', models.CharField(choices=[('purchase', 'Alış / giriş'), ('sale', 'Satış'), ('sale_cancel', 'Satış iptali'), ('service', 'Servis'), ('count', 'Sayım'), ('manual', 'Manuel')], max_length=20, verbose_name='Neden')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='Not')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_movements', to='core_settings.productoption', verbose_name='Ürün')),
                ('recorded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stock_movements', to=settings.AUTH_USER_MODEL, verbose_name='Kaydeden')),
                ('sales_lead', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stock_movements', to='sales_leads.saleslead', verbose_name='Satış kaydı')),
                ('service_record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stock_movements', to='services.servicerecord', verbose_name='Servis kaydı')),
            ],
            options={
                'verbose_name': 'Stok hareketi',
                'verbose_name_plural': 'Stok hareketleri',
                'ordering': ['-created_at'],
            },
        ),
    ]
