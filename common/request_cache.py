"""İstek başına önbellek — context processor tekrarlarını azaltır."""

from __future__ import annotations


def cache_get(request, key: str, factory):
    if request is None:
        return factory()
    store = getattr(request, '_gy_request_cache', None)
    if store is None:
        store = {}
        request._gy_request_cache = store
    if key not in store:
        store[key] = factory()
    return store[key]
