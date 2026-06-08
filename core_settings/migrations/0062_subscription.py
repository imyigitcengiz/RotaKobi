from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core_settings', '0061_tenant_brand_required'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('trialing', 'Deneme'),
                        ('active', 'Aktif'),
                        ('past_due', 'Ödeme gecikmiş'),
                        ('canceled', 'İptal'),
                    ],
                    default='trialing',
                    max_length=20,
                    verbose_name='Durum',
                )),
                ('current_period_end', models.DateTimeField(blank=True, null=True, verbose_name='Dönem bitişi')),
                ('external_id', models.CharField(blank=True, default='', max_length=255, verbose_name='Ödeme sağlayıcı kimliği')),
                ('trial_ends_at', models.DateTimeField(blank=True, null=True, verbose_name='Deneme bitişi')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='subscriptions',
                    to='core_settings.plan',
                    verbose_name='Plan',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscriptions',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Abonelik sahibi',
                )),
            ],
            options={
                'verbose_name': 'Abonelik',
                'verbose_name_plural': 'Abonelikler',
                'ordering': ['-updated_at', '-pk'],
            },
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['user', 'status'], name='core_settin_user_id_8f0a2a_idx'),
        ),
    ]
