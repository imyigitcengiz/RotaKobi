"""Kapalı modül / parçacık URL'lerini engelle."""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from common.module_context import bind_module_user, reset_module_user

from common.middleware import _is_api_request, _path_matches
from common.module_catalog import (
    MODULE_KIND_INTEGRATION,
    MODULE_STATUS_ACTIVE,
    MODULE_STATUS_BETA,
    module_by_slug,
)
from common.module_particles import particle_by_slug
from common.module_runtime import (
    is_module_installed,
    is_particle_enabled,
    module_route_allowed,
    resolve_path_module_slug,
    resolve_path_particle_slug,
)


class ModuleInstallMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = bind_module_user(
            request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            request=request,
        )
        try:
            if request.user.is_authenticated and not request.user.is_superuser:
                past_due = self._subscription_write_blocked(request)
                if past_due is not None:
                    return past_due
                blocked = self._blocked_response(request)
                if blocked is not None:
                    return blocked
            return self.get_response(request)
        finally:
            reset_module_user(token)

    @staticmethod
    def _api_forbidden(message: str, *, error: str = 'module_disabled', status: int = 403):
        return JsonResponse({'ok': False, 'error': error, 'detail': message}, status=status)

    _SUBSCRIPTION_WRITE_EXEMPT = (
        '/panel/abonelik/',
        '/cikis/',
        '/profil/',
        '/static/',
        '/media/',
        '/api/billing/',
        '/aktiflestir/',
        '/giris/',
        '/healthz/',
    )

    def _subscription_write_blocked(self, request):
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return None
        path = request.path
        if any(_path_matches(path, prefix) for prefix in self._SUBSCRIPTION_WRITE_EXEMPT):
            return None
        from core_settings.billing.subscription import subscription_blocks_writes

        if not subscription_blocks_writes(request.user):
            return None
        msg = (
            'Deneme süreniz sona erdi ve ödeme alınamadı. '
            'Salt okunur moddasınız — Abonelik sayfasından ödeme yapın.'
        )
        if _is_api_request(request):
            return self._api_forbidden(msg, error='subscription_past_due', status=403)
        return render(request, 'errors/module_disabled.html', {'message': msg}, status=403)

    def _blocked_response(self, request):
        path = request.path

        slug = resolve_path_module_slug(path)
        if slug:
            mod = module_by_slug(slug)
            if mod and mod['status'] in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
                if mod['kind'] == MODULE_KIND_INTEGRATION:
                    if not module_route_allowed(slug):
                        msg = f'"{mod["name"]}" entegrasyonu kapalı. Abonelik sayfasından açabilirsiniz.'
                        if _is_api_request(request):
                            return self._api_forbidden(msg)
                        return render(request, 'errors/module_disabled.html', {'message': msg}, status=403)
                elif not module_route_allowed(slug):
                    msg = f'{mod["name"]} modülü kapalı. Abonelik sayfasından açabilirsiniz.'
                    if _is_api_request(request):
                        return self._api_forbidden(msg)
                    return render(request, 'errors/module_disabled.html', {'message': msg}, status=403)

        particle_slug = resolve_path_particle_slug(path)
        if particle_slug:
            p = particle_by_slug(particle_slug)
            if p and not self._particle_route_allowed(particle_slug, path):
                msg = f'"{p["name"]}" özelliği kapalı. Abonelik sayfasından açabilirsiniz.'
                if _is_api_request(request):
                    return self._api_forbidden(msg)
                return render(request, 'errors/module_disabled.html', {'message': msg}, status=403)

        return None

    @staticmethod
    def _particle_route_allowed(particle_slug: str, path: str = '') -> bool:
        p = particle_by_slug(particle_slug)
        if not p or not is_particle_enabled(particle_slug):
            return False
        parent = p.get('parent_module')
        if parent and not is_module_installed(parent):
            return False
        integration_slug = resolve_path_module_slug(path)
        if integration_slug:
            mod = module_by_slug(integration_slug)
            if mod and mod['kind'] == MODULE_KIND_INTEGRATION:
                return module_route_allowed(integration_slug)
        return True
