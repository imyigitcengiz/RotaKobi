"""İstek bazlı modül kullanıcı bağlamı."""

from __future__ import annotations

from contextvars import ContextVar

_module_ctx: ContextVar = ContextVar('module_ctx', default=None)


def bind_module_user(user, request=None):
    return _module_ctx.set({'user': user, 'request': request})


def reset_module_user(token) -> None:
    _module_ctx.reset(token)


def current_module_context():
    ctx = _module_ctx.get()
    if isinstance(ctx, dict):
        return ctx
    if ctx is not None:
        return {'user': ctx, 'request': None}
    return None


def current_module_user():
    ctx = current_module_context()
    if not ctx:
        return None
    return ctx.get('user')


def current_module_request():
    ctx = current_module_context()
    if not ctx:
        return None
    return ctx.get('request')
