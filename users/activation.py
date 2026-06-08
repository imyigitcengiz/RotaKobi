"""Hesap aktivasyon e-postası ve token doğrulama."""

from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.template.loader import render_to_string
from django.urls import reverse

_SIGNER = TimestampSigner(salt='kobiops.account-activation')
_MAX_AGE = 60 * 60 * 24 * 3  # 3 gün


def make_activation_token(user) -> str:
    return _SIGNER.sign(str(user.pk))


def user_from_activation_token(token: str):
    from users.models import User

    try:
        user_id = _SIGNER.unsign(token, max_age=_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    try:
        return User.objects.get(pk=int(user_id))
    except (User.DoesNotExist, ValueError, TypeError):
        return None


def send_activation_email(request, user) -> None:
    token = make_activation_token(user)
    path = reverse('activate_account', kwargs={'token': token})
    activate_url = request.build_absolute_uri(path)

    context = {
        'user': user,
        'activate_url': activate_url,
        'site_name': getattr(settings, 'KOBIOPS_SITE_NAME', 'KobiOPS'),
    }
    subject = render_to_string('users/activation_subject.txt', context).strip()
    body = render_to_string('users/activation_email.txt', context)

    recipient = (user.email or '').strip()
    if not recipient:
        return

    send_mail(
        subject=subject or 'Hesabınızı aktifleştirin',
        message=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[recipient],
        fail_silently=False,
    )
