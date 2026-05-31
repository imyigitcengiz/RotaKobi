from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from common.module_runtime import is_module_installed
from common.weather_service import weather_for_site
from core_settings.models import SiteSettings


@login_required
@require_GET
def weather_api(request):
    if not is_module_installed('integration_weather'):
        return JsonResponse({'ok': False, 'error': 'disabled'}, status=403)

    settings = SiteSettings.objects.first()
    if not settings:
        return JsonResponse({'ok': False, 'error': 'no_settings'}, status=404)

    snap = weather_for_site(settings)
    if not snap:
        return JsonResponse({'ok': False, 'error': 'fetch_failed'}, status=502)

    return JsonResponse({'ok': True, 'weather': snap.to_dict()})
