"""Ödeme webhook işleyicileri — idempotent, provider adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time

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


def _billing_webhook_secret() -> str:
    return (
        os.environ.get('COOLOPS_BILLING_WEBHOOK_SECRET', '').strip()
        or os.environ.get('KOBIOPS_BILLING_WEBHOOK_SECRET', '').strip()
    )


def _verify_shared_webhook_secret(request) -> bool:
    secret = _billing_webhook_secret()
    if not secret:
        return False
    header = (request.headers.get('X-Coolops-Webhook-Secret') or '').strip()
    if header and hmac.compare_digest(header, secret):
        return True
    auth = (request.headers.get('Authorization') or '').strip()
    if auth.lower().startswith('bearer '):
        token = auth[7:].strip()
        if token and hmac.compare_digest(token, secret):
            return True
    return False


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    if not sig_header or not secret:
        return False
    parts: dict[str, str] = {}
    for item in sig_header.split(','):
        if '=' in item:
            key, value = item.split('=', 1)
            parts[key.strip()] = value.strip()
    timestamp = parts.get('t')
    signature = parts.get('v1')
    if not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > 300:
        return False
    signed = f'{timestamp}.{payload.decode("utf-8")}'
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@csrf_exempt
@require_POST
def iyzico_webhook(request):
    """Iyzico ödeme bildirimi — imzasız istekler reddedilir."""
    if not _verify_shared_webhook_secret(request):
        logger.warning('iyzico webhook rejected: missing or invalid signature')
        return JsonResponse({'ok': False, 'error': 'unauthorized'}, status=403)

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
    """Stripe webhook — Stripe-Signature doğrulanır."""
    sig = request.headers.get('Stripe-Signature', '')
    secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '').strip()
    if not secret:
        return JsonResponse({'ok': False, 'error': 'stripe_not_configured'}, status=501)

    payload = request.body or b''
    if not _verify_stripe_signature(payload, sig, secret):
        logger.warning('stripe webhook rejected: invalid signature')
        return JsonResponse({'ok': False, 'error': 'invalid_signature'}, status=403)

    try:
        event = json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponseBadRequest('invalid json')

    event_type = event.get('type', '')

    if event_type == 'checkout.session.completed':
        # Stripe entegrasyonu tamamlandığında customer metadata → user eşlemesi
        return JsonResponse({'ok': True, 'stub': True})

    return JsonResponse({'ok': True, 'ignored': True})
