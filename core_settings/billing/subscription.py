"""Abonelik yaşam döngüsü — trial, past_due, aktif plan çözümlemesi."""

from __future__ import annotations

import os
from datetime import timedelta

from django.utils import timezone


def trial_days() -> int:
    raw = os.environ.get('COOLOPS_SUBSCRIPTION_TRIAL_DAYS', '14').strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 14


def create_subscription_for_register(user, plan) -> 'Subscription':
    """Kayıt sonrası abonelik kaydı — ücretsiz plan hemen aktif, ücretli plan trial."""
    from core_settings.models import Subscription

    now = timezone.now()
    days = trial_days()
    trial_end = now + timedelta(days=days) if days else None

    if plan.price == 0:
        status = Subscription.STATUS_ACTIVE
        trial_end = None
    else:
        status = Subscription.STATUS_TRIALING

    return Subscription.objects.create(
        user=user,
        plan=plan,
        status=status,
        trial_ends_at=trial_end,
        current_period_end=trial_end,
    )


def get_active_subscription(user):
    if not user or not getattr(user, 'pk', None):
        return None
    from core_settings.models import Subscription

    return (
        Subscription.objects.filter(
            user=user,
            status__in=(
                Subscription.STATUS_TRIALING,
                Subscription.STATUS_ACTIVE,
                Subscription.STATUS_PAST_DUE,
            ),
        )
        .select_related('plan')
        .order_by('-updated_at', '-pk')
        .first()
    )


def refresh_subscription_status(user) -> None:
    """Trial bitmiş ücretli abonelikleri past_due yap."""
    if not user or not getattr(user, 'pk', None):
        return
    from core_settings.models import Subscription

    now = timezone.now()
    qs = Subscription.objects.filter(user=user, status=Subscription.STATUS_TRIALING)
    for sub in qs.select_related('plan'):
        if not sub.trial_ends_at or sub.trial_ends_at > now:
            continue
        if sub.plan.price > 0:
            sub.status = Subscription.STATUS_PAST_DUE
            sub.save(update_fields=['status', 'updated_at'])


def subscription_blocks_writes(user) -> bool:
    """past_due abonelikte yazma işlemleri engellenir."""
    if not user or user.is_superuser:
        return False
    refresh_subscription_status(user)
    sub = get_active_subscription(user)
    from core_settings.models import Subscription

    return bool(sub and sub.status == Subscription.STATUS_PAST_DUE)


def activate_subscription_payment(user, *, external_id: str = '', period_end=None) -> None:
    """Webhook veya manuel onay sonrası aboneliği aktifleştir."""
    from core_settings.models import Subscription

    sub = get_active_subscription(user)
    if not sub:
        sub = (
            Subscription.objects.filter(user=user)
            .select_related('plan')
            .order_by('-pk')
            .first()
        )
    if not sub:
        return

    sub.status = Subscription.STATUS_ACTIVE
    if external_id:
        sub.external_id = external_id
    if period_end:
        sub.current_period_end = period_end
    sub.trial_ends_at = None
    sub.save(update_fields=['status', 'external_id', 'current_period_end', 'trial_ends_at', 'updated_at'])

    user.plan = sub.plan
    user.save(update_fields=['plan'])

    from common.module_plan import clamp_owner_modules_to_plan

    clamp_owner_modules_to_plan(user)
