from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy

from common.middleware import _is_api_request, permission_denied_redirect
from users.impersonation import get_real_user, is_impersonating


class SuperuserRequiredMixin(UserPassesTestMixin):
    login_url = reverse_lazy('login')

    def test_func(self):
        user = get_real_user(self.request)
        return user.is_authenticated and user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return permission_denied_redirect(
            self.request,
            'Bu alan yalnızca süper admin kullanıcıları içindir.',
        )


class BrandTeamManagerMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Abonelik / marka sahibi ekip yönetimi."""

    login_url = reverse_lazy('login')

    def test_func(self):
        from common.brand_team import can_manage_brand_team
        from users.impersonation import get_real_user

        return can_manage_brand_team(get_real_user(self.request))

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(
            self.request,
            'Ekip yönetimi yalnızca marka / abonelik sahiplerine açıktır.',
        )
        return redirect('home')


class PermissionRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Tek veya çoklu izin gerektiren class-based view mixin."""

    permission_required = None
    permission_any = False
    permission_denied_message = 'Bu işlem için yetkiniz yok.'

    def get_permission_required(self):
        perms = self.permission_required
        if perms is None:
            return []
        if isinstance(perms, str):
            return [perms]
        return list(perms)

    def test_func(self):
        user = self.request.user
        real_user = get_real_user(self.request)
        if real_user.is_superuser and not is_impersonating(self.request):
            return True
        perms = self.get_permission_required()
        if not perms:
            return True
        if self.permission_any:
            return user.has_any_perm_codename(*perms)
        return all(user.has_perm_codename(p) for p in perms)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        request = self.request
        if _is_api_request(request):
            return JsonResponse({'ok': False, 'error': self.permission_denied_message}, status=403)
        return permission_denied_redirect(request, self.permission_denied_message)
