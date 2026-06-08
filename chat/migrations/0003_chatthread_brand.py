"""Marka başına genel sohbet odası; mevcut global odayı markalara böl."""

from django.db import migrations, models
import django.db.models.deletion


def split_team_threads_by_brand(apps, schema_editor):
    ChatThread = apps.get_model('chat', 'ChatThread')
    ChatMembership = apps.get_model('chat', 'ChatMembership')
    BusinessBrand = apps.get_model('core_settings', 'BusinessBrand')
    BrandMembership = apps.get_model('core_settings', 'BrandMembership')

    legacy_team = ChatThread.objects.filter(kind='team', brand__isnull=True).order_by('pk').first()
    legacy_member_ids = set()
    if legacy_team:
        legacy_member_ids = set(
            ChatMembership.objects.filter(thread=legacy_team).values_list('user_id', flat=True)
        )

    for brand in BusinessBrand.objects.filter(is_active=True).order_by('pk'):
        team = ChatThread.objects.filter(kind='team', brand_id=brand.pk).first()
        if not team:
            team = ChatThread.objects.create(
                kind='team',
                brand_id=brand.pk,
                title='Genel Sohbet',
            )
        member_ids = set(
            BrandMembership.objects.filter(brand_id=brand.pk).values_list('user_id', flat=True)
        )
        if legacy_team and legacy_member_ids:
            member_ids &= legacy_member_ids
        existing = set(
            ChatMembership.objects.filter(thread=team, user_id__in=member_ids).values_list('user_id', flat=True)
        )
        missing = member_ids - existing
        if missing:
            ChatMembership.objects.bulk_create(
                [ChatMembership(thread=team, user_id=uid) for uid in missing],
                ignore_conflicts=True,
            )

    if legacy_team:
        ChatMembership.objects.filter(thread=legacy_team).delete()
        legacy_team.delete()

    User = apps.get_model('users', 'User')
    for thread in ChatThread.objects.filter(kind='direct', brand__isnull=True):
        user_ids = list(
            ChatMembership.objects.filter(thread=thread).values_list('user_id', flat=True)
        )
        if len(user_ids) != 2:
            continue
        shared = (
            BrandMembership.objects.filter(user_id=user_ids[0], brand__is_active=True)
            .filter(brand_id__in=BrandMembership.objects.filter(user_id=user_ids[1]).values('brand_id'))
            .order_by('brand_id')
            .values_list('brand_id', flat=True)
            .first()
        )
        if shared:
            thread.brand_id = shared
            thread.save(update_fields=['brand_id'])


class Migration(migrations.Migration):
    dependencies = [
        ('core_settings', '0061_tenant_brand_required'),
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatthread',
            name='brand',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='chat_threads',
                to='core_settings.businessbrand',
                verbose_name='Marka',
            ),
        ),
        migrations.RunPython(split_team_threads_by_brand, migrations.RunPython.noop),
    ]
