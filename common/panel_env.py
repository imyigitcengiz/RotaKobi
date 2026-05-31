"""Coolify / Dokploy / 1Panel ortam değişkenlerinden Django ayarlarını tamamlar."""

from __future__ import annotations

import os
from urllib.parse import urlparse


def _strip_host(value: str) -> str:
    value = value.strip()
    if not value:
        return ''
    if '://' in value:
        parsed = urlparse(value)
        return (parsed.hostname or '').strip()
    return value.split('/')[0].split(':')[0].strip()


def detect_panel_fqdn() -> str:
    for key in (
        'SERVICE_FQDN_APP',
        'SERVICE_FQDN',
        'COOLIFY_FQDN',
        'DOKPLOY_FQDN',
        'DOMAIN',
        'APP_DOMAIN',
        'HOSTNAME',
    ):
        host = _strip_host(os.environ.get(key, ''))
        if host:
            return host
    for key in ('SERVICE_URL_APP', 'SERVICE_URL', 'DOKPLOY_DEPLOY_URL', 'DOKPLOY_URL', 'APP_URL', 'WEBSITE_URL'):
        host = _strip_host(os.environ.get(key, ''))
        if host:
            return host
    return ''


def detect_panel_origin() -> str:
    for key in ('SERVICE_URL_APP', 'SERVICE_URL', 'DOKPLOY_DEPLOY_URL', 'DOKPLOY_URL', 'APP_URL', 'WEBSITE_URL'):
        raw = os.environ.get(key, '').strip()
        if raw:
            if '://' not in raw:
                fqdn = _strip_host(raw)
                if fqdn.endswith('.sslip.io') or fqdn.endswith('.traefik.me'):
                    return f'http://{fqdn}'
                return f'https://{fqdn}'
            return raw.rstrip('/')
    fqdn = detect_panel_fqdn()
    if fqdn:
        if fqdn.endswith('.sslip.io') or fqdn.endswith('.traefik.me'):
            return f'http://{fqdn}'
        return f'https://{fqdn}'
    return ''


def is_http_only_panel_host(host: str) -> bool:
    return host.endswith('.sslip.io') or host.endswith('.traefik.me')
