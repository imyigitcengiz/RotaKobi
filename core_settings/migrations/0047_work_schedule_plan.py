from django.db import migrations, models


def seed_default_plan(apps, schema_editor):
    WorkSchedulePlan = apps.get_model('core_settings', 'WorkSchedulePlan')
    if WorkSchedulePlan.objects.exists():
        return
    from core_settings.work_schedule import default_weekly_hours

    WorkSchedulePlan.objects.create(
        name='Standart mesai',
        notes='Pazartesi–Cuma 09:00–18:00, Cumartesi yarım gün.',
        is_default=True,
        is_active=True,
        weekly_hours=default_weekly_hours(),
        sort_order=0,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core_settings', '0046_sitesettings_currency_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkSchedulePlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Plan adı')),
                ('notes', models.TextField(blank=True, default='', verbose_name='Açıklama')),
                ('is_default', models.BooleanField(
                    default=False,
                    help_text='Montaj programı ve mesai kontrollerinde öncelikli plan.',
                    verbose_name='Varsayılan plan',
                )),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktif')),
                ('weekly_hours', models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='Gün başına: çalışma günü mü, başlangıç ve bitiş saati.',
                    verbose_name='Haftalık mesai',
                )),
                ('sort_order', models.PositiveSmallIntegerField(default=0, verbose_name='Sıra')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Mesai planı',
                'verbose_name_plural': 'Mesai planları',
                'ordering': ['-is_default', 'sort_order', 'name'],
            },
        ),
        migrations.RunPython(seed_default_plan, migrations.RunPython.noop),
    ]
