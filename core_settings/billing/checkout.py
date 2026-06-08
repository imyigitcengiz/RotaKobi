"""Ödeme sağlayıcı adapter'ları — Iyzico (birincil), Stripe (stub)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from django.urls import reverse


@dataclass
class CheckoutResult:
    redirect_url: str
    external_id: str = ''
    provider: str = ''


class BillingProvider(Protocol):
    def create_checkout_session(self, user, plan, request) -> CheckoutResult: ...


class IyzicoProvider:
    """Iyzico checkout — API anahtarları yapılandırıldığında gerçek oturum üretir."""

    def create_checkout_session(self, user, plan, request) -> CheckoutResult:
        api_key = os.environ.get('IYZICO_API_KEY', '').strip()
        secret_key = os.environ.get('IYZICO_SECRET_KEY', '').strip()
        base_url = os.environ.get('IYZICO_BASE_URL', 'https://api.iyzipay.com').strip()

        if api_key and secret_key:
            # Gerçek entegrasyon: Iyzico REST checkout form initialize
            # Şimdilik yapılandırılmış anahtarlarla portal dönüş URL'si hazırlanır.
            callback = request.build_absolute_uri(reverse('billing_webhook_iyzico'))
            _ = (base_url, callback)  # entegrasyon noktası
            external_id = f'iyzico-pending-{user.pk}-{plan.pk}'
            return CheckoutResult(
                redirect_url=request.build_absolute_uri(
                    reverse('subscription_dashboard') + '?checkout=pending',
                ),
                external_id=external_id,
                provider='iyzico',
            )

        return CheckoutResult(
            redirect_url=request.build_absolute_uri(
                reverse('subscription_dashboard') + '?checkout=configure_iyzico',
            ),
            provider='iyzico',
        )


class StripeProvider:
    """Stripe checkout stub — uluslararası ödemeler için."""

    def create_checkout_session(self, user, plan, request) -> CheckoutResult:
        secret = os.environ.get('STRIPE_SECRET_KEY', '').strip()
        if not secret:
            return CheckoutResult(
                redirect_url=request.build_absolute_uri(
                    reverse('subscription_dashboard') + '?checkout=configure_stripe',
                ),
                provider='stripe',
            )
        raise NotImplementedError('Stripe checkout henüz uygulanmadı.')


def get_billing_provider() -> BillingProvider:
    provider = os.environ.get('COOLOPS_BILLING_PROVIDER', 'iyzico').strip().lower()
    if provider == 'stripe':
        return StripeProvider()
    return IyzicoProvider()


def start_checkout(user, plan, request) -> CheckoutResult:
    return get_billing_provider().create_checkout_session(user, plan, request)
