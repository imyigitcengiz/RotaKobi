"""Coolify / Dokploy / Plesk / 1Panel — ortak domain otomatik algılama."""

from __future__ import annotations

import os
from urllib.parse import urlparse

# Öncelik sırası — deploy/panel-domain.sh ile aynı
PANEL_FQDN_ENV_KEYS = (
    'SERVICE_FQDN_APP',
    'SERVICE_FQDN',
    'KOBIOPS_DOMAIN',
    'PLESK_DOMAIN',
    'DOKPLOY_FQDN',
    'DOMAIN',
    'APP_DOMAIN',
    'HOSTNAME',
    'COOLIFY_FQDN',
)

PANEL_URL_ENV_KEYS = (
    'SERVICE_URL_APP',
    'SERVICE_URL',
    'KOBIOPS_PUBLIC_URL',
    'DOKPLOY_DEPLOY_URL',
    'DOKPLOY_URL',
    'WEBSITE_URL',
)


def _strip_host(value: str) -> str:
    value = value.strip()
    if not value:
        return ''
    if '://' in value:
        parsed = urlparse(value)
        return (parsed.hostname or '').strip()
    return value.split('/')[0].split(':')[0].strip()


def is_http_only_panel_host(host: str) -> bool:
    return host.endswith('.sslip.io') or host.endswith('.traefik.me')


def _origin_from_fqdn(fqdn: str) -> str:
    if is_http_only_panel_host(fqdn):
        return f'http://{fqdn}'
    return f'https://{fqdn}'


def _read_fqdn_key(key: str) -> str:
    return _strip_host(os.environ.get(key, ''))


def _detect_fqdn_raw() -> str:
    for key in PANEL_FQDN_ENV_KEYS:
        host = _read_fqdn_key(key)
        if host:
            return host
    for key in (*PANEL_URL_ENV_KEYS, 'APP_URL'):
        host = _strip_host(os.environ.get(key, ''))
        if host:
            return host
    return ''


def normalize_panel_service_env() -> tuple[str, str]:
    """Tüm panel env → (SERVICE_FQDN_APP, SERVICE_URL_APP) canonical çifti."""
    fqdn = _read_fqdn_key('SERVICE_FQDN_APP')
    if not fqdn:
        fqdn = _detect_fqdn_raw()

    url = os.environ.get('SERVICE_URL_APP', '').strip().rstrip('/')
    if not url:
        for key in PANEL_URL_ENV_KEYS:
            raw = os.environ.get(key, '').strip()
            if raw:
                url = raw.rstrip('/')
                if '://' not in url:
                    url = _origin_from_fqdn(_strip_host(url))
                break
    if not url and fqdn:
        url = _origin_from_fqdn(fqdn)
    if not fqdn and url:
        fqdn = _strip_host(url)
    if not fqdn and not os.environ.get('SERVICE_FQDN_APP', '').strip():
        legacy = os.environ.get('APP_URL', '').strip()
        if legacy:
            fqdn = _strip_host(legacy)
            if not url:
                url = legacy.rstrip('/') if '://' in legacy else _origin_from_fqdn(fqdn)

    if url and '://' not in url:
        url = _origin_from_fqdn(_strip_host(url))

    return fqdn, url


def detect_panel_fqdn() -> str:
    fqdn, _ = normalize_panel_service_env()
    return fqdn


def detect_panel_origin() -> str:
    _, url = normalize_panel_service_env()
    return url
