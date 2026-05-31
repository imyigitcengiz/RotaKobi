"""Modül aç/kapa — AJAX uç noktası."""

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from common.decorators import json_auth_required
from common.module_toggle import toggle_module_slug


@require_POST
@json_auth_required
def module_toggle_api(request):
    slug = (request.POST.get('module_slug') or '').strip()
    if not slug:
        return JsonResponse({'ok': False, 'error': 'Modül belirtilmedi.'}, status=400)
    result = toggle_module_slug(request.user, slug)
    status = 200 if result.get('ok') else 400
    if result.get('error') and not result.get('ok') and 'yetkiniz' in result.get('error', ''):
        status = 403
    return JsonResponse(result, status=status)
