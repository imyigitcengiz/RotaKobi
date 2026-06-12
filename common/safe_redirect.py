"""Güvenli dahili yönlendirme (open redirect koruması)."""

from __future__ import annotations

from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_url(request, raw: str | None, *, fallback: str) -> str:
    """Yalnızca aynı host üzerindeki güvenli URL'lere izin verir."""
    url = (raw or '').strip()
    if not url:
        return fallback
    if url_has_allowed_host_and_scheme(
        url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return url
    return fallback
