"""Servis yazdırma — WhatsApp konum isteme mesajı şablonu."""

from __future__ import annotations

from core_settings.models import SiteSettings

DEFAULT_WHATSAPP_LOCATION_REQUEST_TEMPLATE = (
    'Merhabalar, {site_name} firmasından {ariza} servis kaydınızla ilgili '
    'sizleri rahatsız ediyorum. Rica etsek tamamlanacak servis kaydınız için '
    'bizlere konum gönderebilir misiniz?'
)


def get_whatsapp_location_request_template() -> str:
    settings = SiteSettings.objects.first()
    raw = getattr(settings, 'whatsapp_location_request_template', None) if settings else None
    if raw and str(raw).strip():
        return str(raw).strip()
    return DEFAULT_WHATSAPP_LOCATION_REQUEST_TEMPLATE


def get_site_display_name() -> str:
    """Site ayarlarındaki firma adı; yoksa varsayılan Kobi Hub."""
    row = SiteSettings.objects.first()
    name = (getattr(row, 'site_name', None) or '').strip() if row else ''
    return name or 'Kobi Hub'


def render_whatsapp_location_request_message(*, ariza: str, site_name: str | None = None) -> str:
    resolved_name = (site_name or '').strip() or get_site_display_name()
    template = get_whatsapp_location_request_template()
    try:
        return template.format(site_name=resolved_name, ariza=ariza)
    except (KeyError, ValueError):
        return DEFAULT_WHATSAPP_LOCATION_REQUEST_TEMPLATE.format(
            site_name=resolved_name,
            ariza=ariza,
        )
