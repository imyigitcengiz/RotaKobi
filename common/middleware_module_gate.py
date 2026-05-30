"""Kapalı modül / parçacık URL'lerini engelle."""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from common.module_catalog import MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA, module_by_slug
from common.module_particles import particle_by_slug
from common.module_runtime import (
    is_module_enabled,
    is_particle_enabled,
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

        particle_slug = resolve_path_particle_slug(path)
        if particle_slug:
            p = particle_by_slug(particle_slug)
            if p and not is_particle_enabled(particle_slug):
                messages.warning(
                    request,
                    f'"{p["name"]}" özelliği kapalı. Modül Merkezi\'nden açabilirsiniz.',
                )
                return redirect(reverse('module_hub') + '?section=particles')

        slug = resolve_path_module_slug(path)
        if not slug:
            return None
        mod = module_by_slug(slug)
        if not mod or mod['status'] not in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
            return None
        if is_module_enabled(slug):
            return None
        messages.warning(
            request,
            f'{mod["name"]} modülü kurulu değil. Modül Merkezi\'nden açabilirsiniz.',
        )
        try:
            return redirect(reverse('module_hub') + f'?highlight={slug}')
        except Exception:
            return redirect('module_hub')
