"""Modül kurulum aç/kapa — API ve form POST ortak mantığı."""

from __future__ import annotations

from common.module_catalog import module_by_slug
from common.module_runtime import (
    build_module_hub_context,
    build_module_record,
    get_enabled_module_slugs,
    is_module_installed,
)


def user_can_manage_modules(user) -> bool:
    return bool(
        user.is_authenticated
        and (user.is_superuser or user.has_perm_codename('access.settings'))
    )


def toggle_module_slug(user, slug: str) -> dict:
    from core_settings.models import SiteSettings

    if not user_can_manage_modules(user):
        return {'ok': False, 'error': 'Modül ayarları için yetkiniz yok.'}

    mod = module_by_slug(slug)
    if not mod or mod['slug'].startswith('agency_'):
        return {'ok': False, 'error': 'Geçersiz modül.'}

    settings = SiteSettings.objects.first()
    if not settings:
        settings = SiteSettings.objects.create()

    enabled = list(get_enabled_module_slugs())
    was_installed = slug in enabled

    if was_installed:
        if not mod.get('can_disable', True):
            return {'ok': False, 'error': 'Bu modül kapatılamaz.'}
        disableable = [
            s for s in enabled
            if module_by_slug(s) and module_by_slug(s).get('can_disable', True)
        ]
        if len(disableable) <= 1:
            return {'ok': False, 'error': 'En az bir modül açık kalmalı.'}
        enabled.remove(slug)
        message = f'"{mod["name"]}" kapatıldı.'
        level = 'info'
    else:
        enabled.append(slug)
        message = f'"{mod["name"]}" açıldı.'
        level = 'success'

    settings.enabled_module_slugs = enabled
    settings.save(update_fields=['enabled_module_slugs'])

    record = build_module_record(user, mod)
    installed = is_module_installed(slug)
    hub = build_module_hub_context(user)

    from common.capability_hub import build_capabilities_hub_context

    caps = build_capabilities_hub_context(user)

    return {
        'ok': True,
        'slug': slug,
        'installed': installed,
        'can_open': record['can_open'],
        'open_url': record.get('open_url') or '',
        'can_toggle': record.get('can_toggle', True),
        'name': mod['name'],
        'kind': mod.get('kind'),
        'message': message,
        'level': level,
        'installed_count': hub['module_installed_count'],
        'capabilities_enabled': caps['capabilities_enabled'],
        'capabilities_total': caps['capabilities_total'],
    }
