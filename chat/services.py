from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from chat.models import ChatMembership, ChatMessage, ChatThread
from common.brand_scope import users_share_brand

User = get_user_model()

TEAM_THREAD_TITLE = 'Genel Sohbet'


def direct_key(user_a_id: int, user_b_id: int) -> str:
    a, b = sorted((user_a_id, user_b_id))
    return f'{a}:{b}'


def ensure_team_thread(brand) -> ChatThread:
    if brand is None:
        raise ValueError('Marka gerekli.')
    thread = ChatThread.objects.filter(kind=ChatThread.KIND_TEAM, brand=brand).order_by('pk').first()
    if not thread:
        thread = ChatThread.objects.create(
            kind=ChatThread.KIND_TEAM,
            brand=brand,
            title=TEAM_THREAD_TITLE,
        )
    elif not thread.title:
        thread.title = TEAM_THREAD_TITLE
        thread.save(update_fields=['title'])
    _ensure_brand_users_in_thread(thread, brand)
    return thread


def _ensure_brand_users_in_thread(thread: ChatThread, brand) -> None:
    from core_settings.models import BrandMembership

    user_ids = set(
        BrandMembership.objects.filter(brand=brand, brand__is_active=True).values_list('user_id', flat=True)
    )
    user_ids &= set(User.objects.filter(is_active=True, pk__in=user_ids).values_list('pk', flat=True))
    existing = set(
        ChatMembership.objects.filter(thread=thread, user_id__in=user_ids).values_list('user_id', flat=True)
    )
    missing = user_ids - existing
    if missing:
        ChatMembership.objects.bulk_create(
            [ChatMembership(thread=thread, user_id=uid) for uid in missing],
            ignore_conflicts=True,
        )


def ensure_membership(thread: ChatThread, user) -> ChatMembership:
    membership, _ = ChatMembership.objects.get_or_create(thread=thread, user=user)
    return membership


def get_or_create_direct_thread(user, other_user, *, brand) -> ChatThread:
    if user.pk == other_user.pk:
        raise ValueError('Kendinizle sohbet açılamaz.')
    if brand is None:
        raise ValueError('Marka gerekli.')
    if not users_share_brand(user, other_user, brand_id=brand.pk):
        raise PermissionError('Bu kullanıcıyla aynı markada değilsiniz.')
    key = direct_key(user.pk, other_user.pk)
    thread = ChatThread.objects.filter(
        kind=ChatThread.KIND_DIRECT,
        direct_key=key,
        brand=brand,
    ).first()
    if thread:
        ensure_membership(thread, user)
        ensure_membership(thread, other_user)
        return thread
    with transaction.atomic():
        thread = ChatThread.objects.create(
            kind=ChatThread.KIND_DIRECT,
            direct_key=key,
            brand=brand,
            title=other_user.display_name,
        )
        ChatMembership.objects.bulk_create([
            ChatMembership(thread=thread, user=user),
            ChatMembership(thread=thread, user=other_user),
        ])
    return thread


def peer_for_thread(thread: ChatThread, viewer) -> User | None:
    if thread.kind != ChatThread.KIND_DIRECT:
        return None
    return (
        User.objects.filter(chat_memberships__thread=thread)
        .exclude(pk=viewer.pk)
        .first()
    )


def serialize_user(user) -> dict:
    return {
        'id': user.id,
        'name': user.display_name,
        'initials': user.initials,
        'username': user.username,
    }


def serialize_message(msg: ChatMessage) -> dict:
    return {
        'id': msg.id,
        'thread_id': msg.thread_id,
        'body': msg.body,
        'created_at': msg.created_at.isoformat(),
        'sender': serialize_user(msg.sender),
    }


def unread_count(membership: ChatMembership) -> int:
    qs = ChatMessage.objects.filter(thread_id=membership.thread_id).exclude(sender_id=membership.user_id)
    if membership.last_read_at:
        qs = qs.filter(created_at__gt=membership.last_read_at)
    return qs.count()


def serialize_thread_summary(thread: ChatThread, membership: ChatMembership, viewer) -> dict:
    last_msg = (
        ChatMessage.objects.filter(thread=thread)
        .select_related('sender')
        .order_by('-created_at')
        .first()
    )
    peer = peer_for_thread(thread, viewer)
    title = thread.title
    if thread.kind == ChatThread.KIND_DIRECT and peer:
        title = peer.display_name
    return {
        'id': thread.id,
        'kind': thread.kind,
        'title': title,
        'unread': unread_count(membership),
        'updated_at': thread.updated_at.isoformat(),
        'last_message': serialize_message(last_msg) if last_msg else None,
        'peer': serialize_user(peer) if peer else None,
    }


def mark_thread_read(thread: ChatThread, user) -> None:
    ChatMembership.objects.filter(thread=thread, user=user).update(last_read_at=timezone.now())


def participant_user_ids(thread: ChatThread) -> list[int]:
    return list(
        ChatMembership.objects.filter(thread=thread).values_list('user_id', flat=True)
    )


def broadcast_chat_message(message: ChatMessage) -> None:
    layer = get_channel_layer()
    if not layer:
        return
    payload = {
        'event': 'chat.message',
        'message': serialize_message(message),
    }
    for uid in participant_user_ids(message.thread):
        async_to_sync(layer.group_send)(
            f'chat_user_{uid}',
            {'type': 'chat.event', 'payload': payload},
        )


def _memberships_for_user(user, *, brand_id: int | None):
    qs = ChatMembership.objects.filter(user=user).select_related('thread')
    if brand_id:
        qs = qs.filter(thread__brand_id=brand_id)
    return qs.order_by('-thread__updated_at')


def total_unread_for_user(user, *, brand_id: int | None = None) -> int:
    total = 0
    for membership in _memberships_for_user(user, brand_id=brand_id):
        total += unread_count(membership)
    return total


def add_user_to_team_thread(user, *, brand) -> None:
    """Yeni kullanıcı kaydında markanın genel odasına ekle."""
    thread = ensure_team_thread(brand)
    ensure_membership(thread, user)
