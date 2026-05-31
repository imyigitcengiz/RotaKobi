from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_leads', '0004_dynamic_payments_product_lines'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesleadinterimpayment',
            name='payment_date',
            field=models.DateField(blank=True, null=True, verbose_name='Ödeme tarihi'),
        ),
    ]
