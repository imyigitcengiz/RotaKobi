from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View

from common.brand_scope import set_active_brand
from common.safe_redirect import safe_redirect_url


class BrandSwitchView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def post(self, request):
        raw = request.POST.get('brand_id')
        fallback = str(reverse_lazy('home'))
        next_url = safe_redirect_url(request, request.POST.get('next'), fallback=fallback)
        try:
            brand_id = int(raw)
        except (TypeError, ValueError):
            messages.error(request, 'Geçersiz marka seçimi.')
            return redirect(next_url)
        if set_active_brand(request, brand_id):
            messages.success(request, 'Aktif marka güncellendi.')
        else:
            messages.error(request, 'Bu markaya erişiminiz yok.')
        return redirect(next_url)
