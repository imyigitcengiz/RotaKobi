from .models import SiteSettings


def whatsapp_context(request):
    return {}


def site_settings(request):
    from common.request_cache import cache_get

    def _load():
        try:
            return SiteSettings.objects.first()
        except Exception:
            return None

    settings = cache_get(request, 'site_settings', _load)
    from common.currency import currency_from_settings

    cur = currency_from_settings(settings)
    return {
        'site_settings': settings,
        'currency_code': cur.code,
        'currency_symbol': cur.symbol,
        'currency_label': cur.label,
        'currency_position': cur.position,
    }

