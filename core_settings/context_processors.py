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

    return {'site_settings': cache_get(request, 'site_settings', _load)}

