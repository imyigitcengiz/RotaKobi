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


def is_plausible_public_fqdn(host: str) -> bool:
    """Konteyner ID / docker hostname gibi sahte değerleri ele."""
    host = (host or '').strip()
    if not host:
        return False
    if host in ('localhost', '127.0.0.1', '[::1]'):
        return True
    return '.' in host


def _origin_from_fqdn(fqdn: str) -> str:
    if is_http_only_panel_host(fqdn):
        return f'http://{fqdn}'
    return f'https://{fqdn}'


def _read_fqdn_key(key: str) -> str:
    return _strip_host(os.environ.get(key, ''))


def _detect_fqdn_raw() -> str:
    for key in PANEL_FQDN_ENV_KEYS:
        host = _read_fqdn_key(key)
        if host and is_plausible_public_fqdn(host):
            return host
    for key in (*PANEL_URL_ENV_KEYS, 'APP_URL'):
        host = _strip_host(os.environ.get(key, ''))
        if host and is_plausible_public_fqdn(host):
            return host
    return ''


def normalize_panel_service_env() -> tuple[str, str]:
    """Tüm panel env → (SERVICE_FQDN_APP, SERVICE_URL_APP) canonical çifti."""
    panel = os.environ.get('COOLOPS_PANEL', '').strip().lower()
    if panel in ('plesk', '1panel', 'vps') or os.environ.get('KOBIOPS_PLESK', '').strip() == '1':
        fqdn = _strip_host(
            os.environ.get('KOBIOPS_DOMAIN', '')
            or os.environ.get('PLESK_DOMAIN', '')
            or os.environ.get('DOMAIN', '')
        )
        if not fqdn:
            return '', ''
        url = os.environ.get('KOBIOPS_PUBLIC_URL', '').strip().rstrip('/')
        if not url:
            url = _origin_from_fqdn(fqdn)
        elif '://' not in url:
            url = _origin_from_fqdn(_strip_host(url))
        return fqdn, url

    raw_fqdn = os.environ.get('SERVICE_FQDN_APP', '').strip()
    if ',' in raw_fqdn:
        hosts = []
        for part in raw_fqdn.split(','):
            host = _strip_host(part.strip())
            if host and is_plausible_public_fqdn(host):
                hosts.append(host)
        fqdn = ''
        for host in hosts:
            if not is_http_only_panel_host(host):
                fqdn = host
                break
        if not fqdn and hosts:
            fqdn = hosts[0]
    else:
        fqdn = _read_fqdn_key('SERVICE_FQDN_APP')
    if fqdn and not is_plausible_public_fqdn(fqdn):
        fqdn = ''
    if not fqdn:
        kobi = _strip_host(os.environ.get('KOBIOPS_DOMAIN', ''))
        svc_raw = os.environ.get('SERVICE_FQDN_APP', '').strip()
        if kobi and svc_raw:
            svc = _strip_host(svc_raw)
            if svc != kobi and is_http_only_panel_host(svc):
                fqdn = kobi
        if not fqdn:
            fqdn = _detect_fqdn_raw()

    raw_url = os.environ.get('SERVICE_URL_APP', '').strip()
    if ',' in raw_url:
        parts = [p.strip().rstrip('/') for p in raw_url.split(',') if p.strip()]
        url = parts[0] if parts else ''
        if url and '://' not in url:
            url = _origin_from_fqdn(_strip_host(url))
        host = _strip_host(url)
        if host and is_http_only_panel_host(host):
            url = f'http://{host}'
    else:
        url = raw_url.rstrip('/')
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

    if fqdn and is_http_only_panel_host(fqdn):
        url = f'http://{fqdn}'

    return fqdn, url


def detect_panel_fqdn() -> str:
    fqdn, _ = normalize_panel_service_env()
    return fqdn


def detect_panel_origin() -> str:
    _, url = normalize_panel_service_env()
    return url


def panel_git_updates_enabled() -> bool:
    """Panel içi git güncelleme — yerel git deposunda varsayılan açık; üretimde env ile kapatılabilir."""
    raw = (
        os.environ.get('COOLOPS_PANEL_GIT_UPDATE', '').strip()
        or os.environ.get('KOBIOPS_PANEL_GIT_UPDATE', '').strip()
    ).lower()
    if raw in ('1', 'true', 'yes', 'on'):
        return True
    if raw in ('0', 'false', 'no', 'off'):
        return False
    from pathlib import Path

    from django.conf import settings

    if (Path(settings.BASE_DIR) / '.git').is_dir():
        return True
    return False
