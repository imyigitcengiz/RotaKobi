"""Deploy webhook ve benzeri çıkış istekleri için SSRF koruması."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class WebhookURLError(ValueError):
    pass


def validate_outbound_webhook_url(url: str) -> str:
    """
    Yalnızca https (veya geliştirmede http localhost) hedeflerine izin verir.
    Özel/metadata IP aralıklarını reddeder.
    """
    raw = (url or '').strip()
    if not raw:
        raise WebhookURLError('Webhook URL boş.')

    parsed = urlparse(raw)
    if parsed.scheme not in ('https', 'http'):
        raise WebhookURLError('Webhook yalnızca http veya https olabilir.')
    if parsed.username or parsed.password:
        raise WebhookURLError('Kimlik bilgisi içeren URL kabul edilmez.')

    host = (parsed.hostname or '').strip().lower()
    if not host:
        raise WebhookURLError('Geçersiz webhook host.')

    if parsed.scheme == 'http':
        if host not in ('localhost', '127.0.0.1', '::1'):
            raise WebhookURLError('Üretim webhookları yalnızca https olmalıdır.')

    blocked_names = ('metadata.google.internal', 'metadata.goog')
    if host in blocked_names or host.endswith('.internal'):
        raise WebhookURLError('İç ağ/metadata hostları engellendi.')

    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == 'https' else 80))
    except socket.gaierror as exc:
        raise WebhookURLError(f'Host çözümlenemedi: {host}') from exc

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise WebhookURLError(f'Özel veya yerel IP hedefi engellendi: {ip_str}')

    return raw
