"""Abonelik ödeme portalı."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import View

from core_settings.billing.checkout import start_checkout
from core_settings.billing.subscription import get_active_subscription, refresh_subscription_status
from core_settings.models import Plan


class SubscriptionCheckoutView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def post(self, request):
        refresh_subscription_status(request.user)
        plan_id = request.POST.get('plan_id')
        plan = Plan.objects.filter(pk=plan_id, is_active=True).first()
        if not plan:
            messages.error(request, 'Geçersiz plan seçimi.')
            return redirect('subscription_dashboard')

        if plan.price == 0:
            request.user.plan = plan
            request.user.save(update_fields=['plan'])
            from common.module_plan import clamp_owner_modules_to_plan

            clamp_owner_modules_to_plan(request.user)
            messages.success(request, f'"{plan.name}" planına geçildi.')
            return redirect('subscription_dashboard')

        sub = get_active_subscription(request.user)
        if sub:
            sub.plan = plan
            sub.save(update_fields=['plan', 'updated_at'])

        result = start_checkout(request.user, plan, request)
        if result.external_id and sub:
            sub.external_id = result.external_id
            sub.save(update_fields=['external_id', 'updated_at'])

        messages.info(request, 'Ödeme sayfasına yönlendiriliyorsunuz.')
        return redirect(result.redirect_url)

    def get(self, request):
        sub = get_active_subscription(request.user)
        plan = sub.plan if sub else request.user.active_plan
        if not plan or plan.price == 0:
            messages.info(request, 'Ücretsiz plandasınız; ödeme gerekmez.')
            return redirect('subscription_dashboard')
        result = start_checkout(request.user, plan, request)
        return redirect(result.redirect_url)
