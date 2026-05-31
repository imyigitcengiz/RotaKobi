"""Kapalı modül / parçacık URL'lerini engelle."""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

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
        if request.user.is_authenticated and not request.user.is_superuser:
            blocked = self._blocked_response(request)
            if blocked is not None:
                return blocked
        return self.get_response(request)

    def _blocked_response(self, request):
        path = request.path

        slug = resolve_path_module_slug(path)
        if slug:
            mod = module_by_slug(slug)
            if mod and mod['status'] in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
                if mod['kind'] == MODULE_KIND_INTEGRATION:
                    if not module_route_allowed(slug):
                        messages.warning(
                            request,
                            f'"{mod["name"]}" entegrasyonu kapalı. Modül Merkezi\'nden açabilirsiniz.',
                        )
                        try:
                            return redirect(reverse('module_hub') + f'?highlight={slug}')
                        except Exception:
                            return redirect('module_hub')
                elif not module_route_allowed(slug):
                    messages.warning(
                        request,
                        f'{mod["name"]} modülü kapalı. Modül Merkezi\'nden açabilirsiniz.',
                    )
                    try:
                        return redirect(reverse('module_hub') + f'?highlight={slug}')
                    except Exception:
                        return redirect('module_hub')

        particle_slug = resolve_path_particle_slug(path)
        if particle_slug:
            p = particle_by_slug(particle_slug)
            if p and not self._particle_route_allowed(particle_slug, path):
                messages.warning(
                    request,
                    f'"{p["name"]}" özelliği kapalı. Modül Merkezi\'nden açabilirsiniz.',
                )
                return redirect(reverse('module_hub'))

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
