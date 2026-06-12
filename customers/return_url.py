"""Güvenli `next` yönlendirmesi (servis formu ↔ müşteri düzenleme)."""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from common.safe_redirect import safe_redirect_url

_SERVICE_CREATE_PATH = '/services-dashboard/services/new/'


def get_safe_return_url(request) -> str | None:
    raw = (request.GET.get('next') or request.POST.get('next') or '').strip()
    if not raw:
        return None
    safe = safe_redirect_url(request, raw, fallback='')
    return safe or None


def ensure_customer_on_service_create_return(url: str | None, customer_id: int) -> str | None:
    """Servis oluşturma dönüş URL'sine müşteri parametresi ekler."""
    if not url or not customer_id:
        return url
    parsed = urlparse(url)
    if parsed.path.rstrip('/') != _SERVICE_CREATE_PATH.rstrip('/'):
        return url
    params = parse_qs(parsed.query, keep_blank_values=True)
    if 'customer' in params and params['customer']:
        return url
    params['customer'] = [str(customer_id)]
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
