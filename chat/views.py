import json

from django.db import DatabaseError
from django.http import JsonResponse
from common.decorators import json_auth_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from chat.models import ChatMembership, ChatMessage, ChatThread
from chat.services import (
    add_user_to_team_thread,
    broadcast_chat_message,
    ensure_membership,
    ensure_team_thread,
    get_or_create_direct_thread,
    mark_thread_read,
    serialize_message,
    serialize_thread_summary,
    serialize_user,
    total_unread_for_user,
)
from django.contrib.auth import get_user_model

User = get_user_model()


def _json_body(request):
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _membership_for(user, thread_id: int, *, brand_id: int | None = None) -> ChatMembership:
    qs = ChatMembership.objects.filter(user=user, thread_id=thread_id)
    if brand_id:
        qs = qs.filter(thread__brand_id=brand_id)
    membership = qs.select_related('thread').first()
    if not membership:
        raise PermissionError('Bu sohbete erişiminiz yok.')
    return membership


@json_auth_required
@require_GET
def chat_summary_api(request):
    from common.brand_scope import get_active_brand

    brand = get_active_brand(request)
    if not brand:
        return JsonResponse({'ok': False, 'error': 'Aktif marka seçin.'}, status=403)
    try:
        ensure_team_thread(brand)
        add_user_to_team_thread(request.user, brand=brand)
    except DatabaseError as exc:
        return JsonResponse({
            'ok': False,
            'error': 'Sohbet tabloları hazır değil. Sunucuda: python manage.py migrate chat',
            'detail': str(exc),
        }, status=503)
    memberships = (
        ChatMembership.objects.filter(user=request.user, thread__brand=brand)
        .select_related('thread')
        .order_by('-thread__updated_at')
    )
    threads = [serialize_thread_summary(m.thread, m, request.user) for m in memberships]
    team = next((t for t in threads if t['kind'] == ChatThread.KIND_TEAM), None)
    direct = [t for t in threads if t['kind'] == ChatThread.KIND_DIRECT]
    return JsonResponse({
        'ok': True,
        'me': serialize_user(request.user),
        'unread_total': total_unread_for_user(request.user, brand_id=brand.pk),
        'team_thread': team,
        'threads': threads,
        'direct_threads': direct,
    })


@json_auth_required
@require_GET
def chat_users_api(request):
    from common.brand_scope import get_active_brand_id
    from core_settings.models import BrandMembership

    brand_id = get_active_brand_id(request)
    if brand_id:
        member_ids = BrandMembership.objects.filter(
            brand_id=brand_id,
            brand__is_active=True,
        ).values_list('user_id', flat=True)
        users = (
            User.objects.filter(is_active=True, pk__in=member_ids)
            .exclude(pk=request.user.pk)
            .order_by('first_name', 'last_name', 'username')
        )
    else:
        users = User.objects.none()
    return JsonResponse({
        'ok': True,
        'users': [serialize_user(u) for u in users],
    })


@json_auth_required
@require_GET
def chat_messages_api(request, thread_id: int):
    from common.brand_scope import get_active_brand_id

    try:
        membership = _membership_for(request.user, thread_id, brand_id=get_active_brand_id(request))
    except PermissionError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=403)

    since_id = request.GET.get('since')
    qs = ChatMessage.objects.filter(thread_id=thread_id).select_related('sender').order_by('created_at')
    if since_id:
        try:
            qs = qs.filter(id__gt=int(since_id))
        except ValueError:
            pass
    else:
        qs = qs.order_by('-created_at')[:80]
        messages = list(reversed(list(qs)))
        mark_thread_read(membership.thread, request.user)
        return JsonResponse({
            'ok': True,
            'thread': serialize_thread_summary(membership.thread, membership, request.user),
            'messages': [serialize_message(m) for m in messages],
        })

    messages = list(qs[:200])
    return JsonResponse({
        'ok': True,
        'messages': [serialize_message(m) for m in messages],
    })


@json_auth_required
@require_POST
def chat_send_api(request, thread_id: int):
    from common.brand_scope import get_active_brand_id

    try:
        membership = _membership_for(request.user, thread_id, brand_id=get_active_brand_id(request))
    except PermissionError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=403)

    body = _json_body(request) or {}
    text = (body.get('body') or '').strip()
    if not text:
        return JsonResponse({'ok': False, 'error': 'Mesaj boş olamaz.'}, status=400)
    if len(text) > 4000:
        return JsonResponse({'ok': False, 'error': 'Mesaj çok uzun.'}, status=400)

    msg = ChatMessage.objects.create(
        thread=membership.thread,
        sender=request.user,
        body=text,
    )
    ChatThread.objects.filter(pk=thread_id).update(updated_at=msg.created_at)
    broadcast_chat_message(msg)
    return JsonResponse({'ok': True, 'message': serialize_message(msg)})


@json_auth_required
@require_POST
def chat_read_api(request, thread_id: int):
    from common.brand_scope import get_active_brand_id

    try:
        membership = _membership_for(request.user, thread_id, brand_id=get_active_brand_id(request))
    except PermissionError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=403)
    mark_thread_read(membership.thread, request.user)
    return JsonResponse({
        'ok': True,
        'unread_total': total_unread_for_user(request.user, brand_id=get_active_brand_id(request)),
    })


@json_auth_required
@require_POST
def chat_direct_api(request):
    from common.brand_scope import get_active_brand, users_share_brand

    brand = get_active_brand(request)
    if not brand:
        return JsonResponse({'ok': False, 'error': 'Aktif marka seçin.'}, status=403)
    body = _json_body(request) or {}
    try:
        other_id = int(body.get('user_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Geçersiz kullanıcı.'}, status=400)

    other = get_object_or_404(User, pk=other_id, is_active=True)
    if other.pk == request.user.pk:
        return JsonResponse({'ok': False, 'error': 'Kendinizle sohbet açılamaz.'}, status=400)
    if not users_share_brand(request.user, other, brand_id=brand.pk):
        return JsonResponse({'ok': False, 'error': 'Bu kullanıcıyla aynı markada değilsiniz.'}, status=403)

    try:
        thread = get_or_create_direct_thread(request.user, other, brand=brand)
    except (ValueError, PermissionError) as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=403)

    membership = ensure_membership(thread, request.user)
    return JsonResponse({
        'ok': True,
        'thread': serialize_thread_summary(thread, membership, request.user),
    })


@json_auth_required
@require_POST
def chat_join_team_api(request):
    """Mevcut kullanıcıyı genel odaya ekler (ilk giriş)."""
    from common.brand_scope import get_active_brand

    brand = get_active_brand(request)
    if not brand:
        return JsonResponse({'ok': False, 'error': 'Aktif marka seçin.'}, status=403)
    add_user_to_team_thread(request.user, brand=brand)
    thread = ensure_team_thread(brand)
    membership = ensure_membership(thread, request.user)
    return JsonResponse({
        'ok': True,
        'thread': serialize_thread_summary(thread, membership, request.user),
    })
