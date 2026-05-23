from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

from common.permissions import resolve_customer_route_permission
from users.permission_catalog import (
    LOGIN_EXEMPT_PREFIXES,
    ROUTE_PERMISSIONS,
    SUPERUSER_ONLY_PREFIXES,
)


def _path_matches(path, prefix):
    return path == prefix or path.startswith(prefix)


def _is_api_request(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    accept = request.headers.get('Accept', '')
    if 'application/json' in accept and 'text/html' not in accept:
        return True
    path = request.path
    return (
        '/api/' in path
        or path.startswith('/chat/')
        or path.startswith('/tools/whatsapp/')
    )


PUBLIC_EXACT_PATHS = frozenset(('/', ''))


def _resolve_required_permission(path, method='GET'):
    if path in PUBLIC_EXACT_PATHS:
        return None

    customer_perm = resolve_customer_route_permission(path, method)
    if customer_perm is not None:
        return customer_perm

    for prefix, codename in ROUTE_PERMISSIONS:
        if _path_matches(path, prefix):
            return codename
    return 'access.home'


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        path = request.path
        if path in PUBLIC_EXACT_PATHS:
            return self.get_response(request)
        if any(_path_matches(path, prefix) for prefix in LOGIN_EXEMPT_PREFIXES):
            return self.get_response(request)

        login_url = reverse('login')
        if _is_api_request(request):
            return JsonResponse({'ok': False, 'error': 'Giriş gerekli.'}, status=401)

        next_url = request.get_full_path()
        return redirect(f'{login_url}?next={next_url}')


class PermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        path = request.path
        if path in PUBLIC_EXACT_PATHS:
            return self.get_response(request)
        if any(_path_matches(path, prefix) for prefix in LOGIN_EXEMPT_PREFIXES):
            return self.get_response(request)

        user = request.user
        if user.is_superuser:
            return self.get_response(request)

        if _path_matches(path, '/admin/'):
            if not user.is_staff:
                if _is_api_request(request):
                    return JsonResponse({'ok': False, 'error': 'Admin erişimi gerekli.'}, status=403)
                messages.error(request, 'Django admin için yetkiniz yok.')
                return redirect('home')
            return self.get_response(request)

        if any(_path_matches(path, prefix) for prefix in SUPERUSER_ONLY_PREFIXES):
            if _is_api_request(request):
                return JsonResponse({'ok': False, 'error': 'Bu alan yalnızca süper admin içindir.'}, status=403)
            messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
            return redirect('home')

        required = _resolve_required_permission(path, request.method)
        if required:
            if isinstance(required, (list, tuple)):
                allowed = user.has_any_perm_codename(*required)
            else:
                allowed = user.has_perm_codename(required)
            if not allowed:
                if _is_api_request(request):
                    return JsonResponse({'ok': False, 'error': 'Bu işlem için yetkiniz yok.'}, status=403)
                messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
                return redirect('home')

        return self.get_response(request)


class DokploySslipCsrfMiddleware:
    """sslip.io / traefik.me: CSRF için http Origin'i otomatik güvenilir listeye ekler."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().partition(':')[0].lower()
        if host.endswith('.sslip.io') or host.endswith('.traefik.me'):
            origin = f'http://{host}'
            if origin not in settings.CSRF_TRUSTED_ORIGINS:
                settings.CSRF_TRUSTED_ORIGINS.append(origin)
        return self.get_response(request)
