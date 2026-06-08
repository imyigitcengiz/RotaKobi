"""Marka / bayi kiracı çözümlemesi — alt alan adı veya yol öneki."""

from __future__ import annotations

import os
import re

from django.conf import settings
from django.db.models import Q
from django.http import HttpRequest

from common.panel_env import detect_panel_fqdn

_RESERVED_PATH_SEGMENTS = frozenset({
    'panel', 'giris', 'cikis', 'kayit', 'profil', 'admin', 'static', 'media',
    'healthz', 'api', 'contact', 'muhasebe', 'tools', 'chat', 'ayarlar',
    'crm', 'iletisim', 'services-dashboard', 'sales-lead', 'bilgi-bankasi',
    'ortak', 'yonetim',
})


def normalize_tenant_key(value: str) -> str:
    from django.utils.text import slugify

    return slugify((value or '').strip()) or ''


def effective_tenant_key(*, host_slug: str = '', slug: str = '') -> str:
    return (normalize_tenant_key(host_slug) or normalize_tenant_key(slug)).lower()


def find_tenant_key_conflict(key: str, *, brand=None, panel_kind=None, parent_brand=None):
    """Aynı kiracı anahtarına sahip başka aktif marka var mı?"""
    from core_settings.models import BusinessBrand

    key = normalize_tenant_key(key).lower()
    if not key:
        return None

    panel_kind = panel_kind or getattr(brand, 'panel_kind', BusinessBrand.PANEL_HQ)
    parent_brand = parent_brand or getattr(brand, 'parent_brand', None)

    if panel_kind == BusinessBrand.PANEL_DEALER and parent_brand:
        qs = BusinessBrand.objects.filter(
            panel_kind=BusinessBrand.PANEL_DEALER,
            parent_brand=parent_brand,
            is_active=True,
        )
    else:
        qs = BusinessBrand.objects.filter(
            panel_kind=BusinessBrand.PANEL_HQ,
            is_active=True,
        )
    if brand and brand.pk:
        qs = qs.exclude(pk=brand.pk)

    for other in qs.only('id', 'name', 'slug', 'host_slug'):
        if other.tenant_key.lower() == key:
            return other
    return None


def allocate_host_slug(
    name: str,
    *,
    panel_kind=None,
    parent_brand=None,
) -> str:
    """Marka adından benzersiz kiracı anahtarı üretir (kayıt / otomatik atama)."""
    from core_settings.models import BusinessBrand

    base = normalize_tenant_key(name) or 'marka'
    candidate = base
    n = 1
    while True:
        try:
            return validate_brand_tenant_key(
                candidate,
                panel_kind=panel_kind or BusinessBrand.PANEL_HQ,
                parent_brand=parent_brand,
                allow_empty=False,
            )
        except ValueError:
            n += 1
            candidate = f'{base}-{n}'


def validate_brand_tenant_key(
    key: str,
    *,
    brand=None,
    panel_kind=None,
    parent_brand=None,
    allow_empty: bool = True,
) -> str:
    """Form doğrulaması — normalize edilmiş kiracı anahtarı veya ValueError."""
    normalized = normalize_tenant_key(key)
    if not normalized:
        if allow_empty:
            return ''
        raise ValueError('Kalıcı URL kodu gerekli.')

    if normalized in _RESERVED_PATH_SEGMENTS:
        raise ValueError(f'"{normalized}" sistem tarafından ayrılmış; başka bir kod seçin.')

    conflict = find_tenant_key_conflict(
        normalized,
        brand=brand,
        panel_kind=panel_kind,
        parent_brand=parent_brand,
    )
    if conflict:
        raise ValueError(f'"{normalized}" adresi "{conflict.name}" markası tarafından kullanılıyor.')
    return normalized


def get_tenant_base_domain() -> str:
    explicit = os.environ.get('COOLOPS_TENANT_BASE_DOMAIN', '').strip().lower()
    if explicit:
        return explicit
    fqdn = (detect_panel_fqdn() or '').strip().lower()
    if fqdn and '.' in fqdn:
        parts = fqdn.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
    if settings.DEBUG:
        return 'localhost'
    return fqdn or 'localhost'


def _is_bare_platform_host(host: str) -> bool:
    host = (host or '').split(':')[0].lower()
    base = get_tenant_base_domain()
    return host in ('localhost', '127.0.0.1', '::1', '[::1]', base)


def _find_hq_by_key(key: str):
    from core_settings.models import BusinessBrand

    key = (key or '').strip().lower()
    if not key:
        return None
    return BusinessBrand.objects.filter(
        panel_kind=BusinessBrand.PANEL_HQ,
        is_active=True,
    ).filter(Q(host_slug=key) | Q(slug=key)).first()


def _find_dealer(*, dealer_key: str, parent):
    from core_settings.models import BusinessBrand

    dealer_key = (dealer_key or '').strip().lower()
    if not dealer_key or not parent:
        return None
    return BusinessBrand.objects.filter(
        panel_kind=BusinessBrand.PANEL_DEALER,
        parent_brand=parent,
        is_active=True,
    ).filter(Q(host_slug=dealer_key) | Q(slug=dealer_key)).first()


def resolve_tenant_from_host(host: str):
    host = (host or '').split(':')[0].lower()
    base = get_tenant_base_domain()
    if _is_bare_platform_host(host):
        return None

    suffix = f'.{base}'
    if not host.endswith(suffix):
        return None

    sub = host[: -len(suffix)]
    if not sub:
        return None

    parts = sub.split('.')
    if len(parts) == 1:
        return _find_hq_by_key(parts[0])
    if len(parts) == 2:
        parent = _find_hq_by_key(parts[1])
        if not parent:
            return None
        return _find_dealer(dealer_key=parts[0], parent=parent)
    return None


def resolve_tenant_from_path(path: str):
    segments = [s for s in (path or '').strip('/').split('/') if s]
    if not segments or segments[0] in _RESERVED_PATH_SEGMENTS:
        return None, ''

    hq = _find_hq_by_key(segments[0])
    if not hq:
        return None, ''

    if len(segments) == 1:
        return hq, f'/{segments[0]}'

    if segments[1] in _RESERVED_PATH_SEGMENTS:
        return hq, f'/{segments[0]}'

    dealer = _find_dealer(dealer_key=segments[1], parent=hq)
    if dealer and dealer.tenant_routing == dealer.TENANT_PATH:
        return dealer, f'/{segments[0]}/{segments[1]}'
    return hq, f'/{segments[0]}'


def resolve_request_tenant(request: HttpRequest):
    host = request.get_host()
    tenant = resolve_tenant_from_host(host)
    path_prefix = ''

    if tenant is None:
        tenant, path_prefix = resolve_tenant_from_path(request.path)

    return tenant, path_prefix


def strip_tenant_path(request: HttpRequest, path_prefix: str) -> None:
    if not path_prefix:
        return
    path = request.path
    if path == path_prefix:
        new_path = '/'
    elif path.startswith(path_prefix + '/'):
        new_path = path[len(path_prefix):] or '/'
    else:
        return
    request.path_info = new_path
    request.META['PATH_INFO'] = new_path


def build_brand_public_url(brand, request: HttpRequest | None = None) -> str:
    from core_settings.models import BusinessBrand

    if not brand:
        return '/'

    scheme = 'https'
    port_suffix = ''
    if request is not None:
        scheme = 'https' if request.is_secure() else 'http'
        port = request.get_port()
        if port and str(port) not in ('80', '443'):
            port_suffix = f':{port}'

    base_domain = get_tenant_base_domain()
    use_path = (
        settings.DEBUG
        and base_domain in ('localhost', '127.0.0.1')
    ) or brand.tenant_routing == BusinessBrand.TENANT_PATH

    if brand.panel_kind == BusinessBrand.PANEL_DEALER and brand.parent_brand_id:
        parent = brand.parent_brand
        if use_path:
            parent_url = build_brand_public_url(parent, request).rstrip('/')
            return f'{parent_url}/{brand.tenant_key}/'
        parent_key = parent.tenant_key
        dealer_key = brand.tenant_key
        host = f'{dealer_key}.{parent_key}.{base_domain}{port_suffix}'
        return f'{scheme}://{host}/'

    key = brand.tenant_key
    if use_path:
        host = f'127.0.0.1{port_suffix}' if request is None else request.get_host()
        return f'{scheme}://{host}/{key}/'
    host = f'{key}.{base_domain}{port_suffix}'
    return f'{scheme}://{host}/'


def tenant_login_url(request: HttpRequest) -> str:
    tenant = getattr(request, 'tenant_brand', None)
    if tenant:
        return build_brand_public_url(tenant, request).rstrip('/') + '/giris/'
    return '/giris/'
