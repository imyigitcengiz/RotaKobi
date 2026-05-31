"""Medya dosyası yolu için yetki kontrolü — IDOR azaltma."""

from __future__ import annotations

import re

from common.permissions import can_view_customers, user_has_perm

_PROFILE_PATH = re.compile(r'^profiles/(?P<name>[^/]+)$', re.I)


def user_can_access_media_path(user, relative_path: str) -> bool:
    """
    /media/... sunumu için önek bazlı yetki.
    Süper admin ve tools.media tüm dosyalara erişir.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if user.has_perm_codename('tools.media'):
        return True

    rel = relative_path.lstrip('/').replace('\\', '/')
    lower = rel.lower()

    if lower.startswith('site/'):
        return user.has_perm_codename('access.settings')

    if lower.startswith('profiles/'):
        match = _PROFILE_PATH.match(lower)
        if not match:
            return False
        profile = getattr(user, 'profile', None)
        if profile and profile.avatar:
            avatar_name = profile.avatar.name.split('/')[-1].lower()
            return match.group('name').lower() == avatar_name
        return False

    if lower.startswith('customers/'):
        return can_view_customers(user)

    if lower.startswith('services/'):
        return user.has_perm_codename('access.services')

    return user.has_perm_codename('access.home')
