from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

_local = threading.local()


@contextmanager
def suppress_live_sync():
    """Çok adımlı kayıtlarda (m2m + save) yinelenen canlı olayları engeller."""
    prev = getattr(_local, 'suppress', 0)
    _local.suppress = prev + 1
    try:
        yield
    finally:
        _local.suppress = prev


def _live_sync_group_name(brand_id: int | None) -> str:
    if brand_id:
        return f'live_updates_brand_{brand_id}'
    return 'live_updates_admin'


def publish_live_event(
    kind,
    action='updated',
    object_id=None,
    message=None,
    *,
    user_id=None,
    brand_id=None,
):
    if getattr(_local, 'suppress', 0):
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    payload = {
        'type': 'live_event',
        'kind': kind,
        'action': action,
        'id': object_id,
        'message': message or 'Veriler güncellendi.',
        'ts': datetime.now(timezone.utc).isoformat(),
        'user_id': user_id,
    }
    group_name = _live_sync_group_name(brand_id)
    async_to_sync(channel_layer.group_send)(group_name, payload)
