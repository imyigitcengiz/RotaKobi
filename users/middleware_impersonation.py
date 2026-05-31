"""Impersonation: request.user hedef kullanıcı; oturum kimliği süper admin kalır."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from users.impersonation import SESSION_IMPERSONATE_USER_ID

User = get_user_model()


class ImpersonationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw = request.session.get(SESSION_IMPERSONATE_USER_ID)
        if request.user.is_authenticated and raw:
            try:
                target_pk = int(raw)
            except (TypeError, ValueError):
                request.session.pop(SESSION_IMPERSONATE_USER_ID, None)
                return self.get_response(request)

            actor = request.user
            if not actor.is_superuser:
                request.session.pop(SESSION_IMPERSONATE_USER_ID, None)
                return self.get_response(request)

            target = (
                User.objects.filter(pk=target_pk, is_active=True)
                .select_related('role')
                .first()
            )
            if not target or target.is_superuser:
                request.session.pop(SESSION_IMPERSONATE_USER_ID, None)
                return self.get_response(request)

            request.impersonator = actor
            request.user = target

        return self.get_response(request)
