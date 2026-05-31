from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0014_servicerecord_pricing'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicerecord',
            name='scheduled_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Planlanan randevu'),
        ),
    ]
