from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def clear_legacy_product_movements(apps, schema_editor):
    StockMovement = apps.get_model('core_settings', 'StockMovement')
    StockMovement.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core_settings', '0038_stock_and_finance_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='Material',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Malzeme adı')),
                ('unit', models.CharField(choices=[('piece', 'Adet'), ('m', 'Metre'), ('kg', 'Kg'), ('l', 'Litre')], default='piece', max_length=10, verbose_name='Birim')),
                ('stock_quantity', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='Mevcut stok')),
                ('min_stock_level', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='Kritik seviye')),
                ('sku', models.CharField(blank=True, max_length=64, verbose_name='Stok kodu')),
                ('notes', models.CharField(blank=True, max_length=255, verbose_name='Not')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktif')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Malzeme',
                'verbose_name_plural': 'Malzemeler',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ProductRecipeLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=2, default=Decimal('1'), max_digits=10, verbose_name='Miktar (1 ürün başına)')),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='recipe_lines', to='core_settings.material', verbose_name='Malzeme')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_lines', to='core_settings.productoption', verbose_name='Satış ürünü')),
            ],
            options={
                'verbose_name': 'Reçete satırı',
                'verbose_name_plural': 'Reçete satırları',
                'ordering': ['material__name'],
            },
        ),
        migrations.AddConstraint(
            model_name='productrecipeline',
            constraint=models.UniqueConstraint(fields=('product', 'material'), name='uniq_product_recipe_material'),
        ),
        migrations.RunPython(clear_legacy_product_movements, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='stockmovement',
            name='product',
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='material',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='stock_movements',
                to='core_settings.material',
                verbose_name='Malzeme',
            ),
        ),
        migrations.AlterField(
            model_name='stockmovement',
            name='delta',
            field=models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Değişim (+/−)'),
        ),
        migrations.AlterField(
            model_name='stockmovement',
            name='quantity_after',
            field=models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Sonraki stok'),
        ),
        migrations.RemoveField(
            model_name='productoption',
            name='min_stock_level',
        ),
        migrations.RemoveField(
            model_name='productoption',
            name='stock_quantity',
        ),
        migrations.RemoveField(
            model_name='productoption',
            name='track_stock',
        ),
    ]
