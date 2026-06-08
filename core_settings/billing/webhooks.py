"""Ödeme webhook işleyicileri — idempotent, provider adapter."""

from __future__ import annotations

import json
import logging

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _parse_json_body(request) -> dict:
    try:
        raw = request.body.decode('utf-8') if request.body else '{}'
        return json.loads(raw) if raw.strip() else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


@csrf_exempt
@require_POST
def iyzico_webhook(request):
    """Iyzico ödeme bildirimi."""
    payload = _parse_json_body(request)
    token = payload.get('token') or payload.get('paymentId') or request.POST.get('token', '')
    user_id = payload.get('user_id') or payload.get('buyerId')
    status = (payload.get('status') or payload.get('paymentStatus') or '').lower()

    if not user_id and not token:
        return HttpResponseBadRequest('missing reference')

    from users.models import User
    from core_settings.billing.subscription import activate_subscription_payment, get_active_subscription

    user = None
    if user_id:
        user = User.objects.filter(pk=user_id).first()
    if not user and token:
        from core_settings.models import Subscription
        sub = Subscription.objects.filter(external_id=token).select_related('user').first()
        user = sub.user if sub else None

    if not user:
        logger.warning('iyzico webhook: user not found user_id=%s token=%s', user_id, token)
        return JsonResponse({'ok': False, 'error': 'user_not_found'}, status=404)

    if status in ('success', 'succeeded', 'paid', '1'):
        sub = get_active_subscription(user)
        activate_subscription_payment(
            user,
            external_id=token or (sub.external_id if sub else ''),
        )
        return JsonResponse({'ok': True})

    return JsonResponse({'ok': True, 'ignored': True})


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Stripe webhook stub."""
    sig = request.headers.get('Stripe-Signature', '')
    secret = __import__('os').environ.get('STRIPE_WEBHOOK_SECRET', '').strip()
    if not secret:
        return JsonResponse({'ok': False, 'error': 'stripe_not_configured'}, status=501)

    payload = _parse_json_body(request)
    event_type = payload.get('type', '')
    _ = sig

    if event_type == 'checkout.session.completed':
        # Stripe entegrasyonu tamamlandığında customer metadata → user eşlemesi
        return JsonResponse({'ok': True, 'stub': True})

    return JsonResponse({'ok': True, 'ignored': True})
