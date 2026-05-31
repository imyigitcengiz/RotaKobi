"""Süper admin — hedef kullanıcı rolüyle paneli inceleme (impersonation)."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()
# Hedef kullanıcı pk — oturum süper admin olarak kalır (login() ile değiştirilmez)
SESSION_IMPERSONATE_USER_ID = '_impersonate_user_id'
# Geriye dönük uyumluluk (eski oturum anahtarı)
SESSION_IMPERSONATOR_KEY = '_impersonator_user_id'


class ImpersonationError(Exception):
    pass


def get_real_user(request):
    """Oturumdaki gerçek kullanıcı; impersonation sırasında süper admin."""
    actor = getattr(request, 'impersonator', None)
    if actor is not None and actor.is_authenticated:
        return actor
    return request.user


def is_impersonating(request) -> bool:
    return bool(request.session.get(SESSION_IMPERSONATE_USER_ID))


def get_impersonator(request):
    """Impersonation aktifken süper admin; değilse None."""
    if not is_impersonating(request):
        return None
    return get_real_user(request)


def can_impersonate(actor, target, *, already_impersonating: bool = False) -> tuple[bool, str]:
    if not actor or not actor.is_authenticated:
        return False, 'Giriş gerekli.'
    if not actor.is_superuser:
        return False, 'Yalnızca süper admin kullanıcı geçişi yapabilir.'
    if already_impersonating:
        return False, 'Önce mevcut kullanıcı görünümünden çıkın.'
    if target.pk == actor.pk:
        return False, 'Kendi hesabınızla geçiş yapılamaz.'
    if target.is_superuser:
        return False, 'Başka bir süper admin hesabına geçiş yapılamaz.'
    if not target.is_active:
        return False, 'Pasif kullanıcı ile geçiş yapılamaz.'
    return True, ''


def start_impersonation(request, target) -> None:
    actor = get_real_user(request)
    ok, reason = can_impersonate(
        actor,
        target,
        already_impersonating=is_impersonating(request),
    )
    if not ok:
        raise ImpersonationError(reason)

    request.session.pop(SESSION_IMPERSONATOR_KEY, None)
    request.session[SESSION_IMPERSONATE_USER_ID] = target.pk
    request.session.modified = True
    logger.info(
        'impersonation_start actor_id=%s target_id=%s target_username=%s',
        actor.pk,
        target.pk,
        target.username,
    )


def stop_impersonation(request):
    """Impersonation oturumunu sonlandırır. Dönüş: (actor, previous_target) veya (None, None)."""
    if not is_impersonating(request):
        return None, None

    target = request.user
    actor = get_real_user(request)
    request.session.pop(SESSION_IMPERSONATE_USER_ID, None)
    request.session.pop(SESSION_IMPERSONATOR_KEY, None)
    request.session.modified = True
    logger.info(
        'impersonation_stop actor_id=%s previous_target_id=%s',
        getattr(actor, 'pk', None),
        getattr(target, 'pk', None),
    )
    return actor, target
