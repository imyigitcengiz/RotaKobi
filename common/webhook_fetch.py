"""SSRF korumalı outbound webhook istekleri."""

from __future__ import annotations

import urllib.error
import urllib.request


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url,
            code,
            'redirect blocked',
            headers,
            fp,
        )


def post_webhook(url: str, *, data: bytes = b'', timeout: int = 30) -> int:
    """Redirect takip etmeden POST gönderir; HTTP status kodu döner."""
    req = urllib.request.Request(url, data=data, method='POST')
    opener = urllib.request.build_opener(_NoRedirectHandler)
    with opener.open(req, timeout=timeout) as resp:
        return int(resp.getcode())
