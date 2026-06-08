from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core_settings', '0060_backfill_tenant_brands'),
    ]

    operations = [
        migrations.AlterField(
            model_name='financerecord',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='finance_records',
                to='core_settings.businessbrand',
                verbose_name='Marka / firma',
            ),
        ),
        migrations.AlterField(
            model_name='servicepersonnel',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='personnel',
                to='core_settings.businessbrand',
                verbose_name='Marka / firma',
            ),
        ),
        migrations.AlterField(
            model_name='solutionpartner',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='solution_partners',
                to='core_settings.businessbrand',
                verbose_name='Marka / firma',
            ),
        ),
        migrations.AlterField(
            model_name='supplierpayable',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='supplier_payables',
                to='core_settings.businessbrand',
                verbose_name='Marka',
            ),
        ),
    ]
