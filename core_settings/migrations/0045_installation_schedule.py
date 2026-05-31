"""Migration — montaj programı modeli ve hafta sonu ayarları."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core_settings', '0044_sector_weather'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='schedule_saturday_default_work',
            field=models.CharField(
                choices=[('installation', 'Montaj'), ('service', 'Servis')],
                default='installation',
                help_text='Cumartesi gününe yeni kayıt eklerken önerilen montaj veya servis.',
                max_length=20,
                verbose_name='Cumartesi varsayılan iş tipi',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='schedule_saturday_working',
            field=models.BooleanField(
                default=True,
                help_text='Kapalıysa cumartesi montaj programında tatil olarak işaretlenir.',
                verbose_name='Cumartesi çalışma günü',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='schedule_sunday_working',
            field=models.BooleanField(
                default=False,
                help_text='Kapalıysa pazar montaj programında tatil olarak işaretlenir.',
                verbose_name='Pazar çalışma günü',
            ),
        ),
        migrations.CreateModel(
            name='InstallationScheduleEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_date', models.DateField(db_index=True, verbose_name='Gün')),
                ('work_type', models.CharField(
                    choices=[('installation', 'Montaj'), ('service', 'Servis')],
                    default='installation',
                    max_length=20,
                    verbose_name='İş tipi',
                )),
                ('notes', models.TextField(blank=True, verbose_name='Montaj notları')),
                ('sort_order', models.PositiveSmallIntegerField(default=0, verbose_name='Sıra')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='installation_schedule_entries',
                    to='customers.customer',
                    verbose_name='Müşteri',
                )),
                ('operational_project', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='schedule_entries',
                    to='core_settings.operationalproject',
                    verbose_name='Proje kartı',
                )),
                ('sales_lead', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='installation_schedule_entries',
                    to='sales_leads.saleslead',
                    verbose_name='Satış kaydı',
                )),
                ('team', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='installation_schedule_entries',
                    to='core_settings.serviceteam',
                    verbose_name='Ekip',
                )),
            ],
            options={
                'verbose_name': 'Montaj programı kaydı',
                'verbose_name_plural': 'Montaj programı kayıtları',
                'ordering': ['scheduled_date', 'sort_order', 'pk'],
            },
        ),
    ]
