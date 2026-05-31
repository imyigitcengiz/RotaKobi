"""İsteğe bağlı Content-Security-Policy — DJANGO_CSP_ENABLED=1."""

from __future__ import annotations

import os

from django.utils.deprecation import MiddlewareMixin

_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' wss: https:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if response.get('Content-Security-Policy'):
            return response
        response['Content-Security-Policy'] = os.environ.get('DJANGO_CSP', _DEFAULT_CSP)
        return response
