from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy

from common.middleware import _is_api_request
from users.impersonation import get_real_user


class SuperuserRequiredMixin(UserPassesTestMixin):
    login_url = reverse_lazy('login')

    def test_func(self):
        user = get_real_user(self.request)
        return user.is_authenticated and user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Bu alan yalnızca süper admin kullanıcıları içindir.')
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
        if user.is_superuser:
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
        messages.error(request, self.permission_denied_message)
        return redirect('home')
