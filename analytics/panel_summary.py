"""Ana panel (/panel) modül özetleri — Yardım Masası ve İletişim Merkezi."""

from __future__ import annotations

import calendar
from datetime import date, datetime, time

from django.db.models import Q
from django.utils import timezone

from analytics.service_report import build_service_dashboard_report
from common.brand_scope import filter_by_brand, filter_outreach_messages, get_active_brand_id

from tools.models import OutreachCollection, OutreachCollectionMember, WhatsappOutboundMessage


def _month_bounds(period: date) -> tuple[date, date]:
    last = calendar.monthrange(period.year, period.month)[1]
    return period.replace(day=1), date(period.year, period.month, last)


def _month_label(period: date) -> str:
    months = (
        'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
        'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
    )
    return f'{months[period.month - 1]} {period.year}'


def build_services_panel_context(request) -> dict:
    """Yardım Masası panel bölümü — servis durum özeti."""
    today = timezone.localdate()
    period = today.replace(day=1)
    report = build_service_dashboard_report(request)
    counts = report['service_counts']

    return {
        'services_panel_period_label': _month_label(period),
        'services_show_panel': True,
        'services_active': counts['active'],
        'services_pending': counts['pending'],
        'services_open': counts['open'],
        'services_closed': counts['closed'],
        'services_month_new': report['month_new'],
        'services_month_delta': report['month_delta'],
        'services_completion_rate': report['completion_rate'],
        'services_total': report['total_services'],
    }


def _outreach_member_count(request) -> int:
    bid = get_active_brand_id(request)
    qs = OutreachCollectionMember.objects.all()
    if bid:
        qs = qs.filter(collection__brand_id=bid)
    else:
        qs = qs.none()
    return qs.count()


def build_outreach_panel_context(request) -> dict:
    """İletişim Merkezi panel bölümü — kampanya ve mesaj özeti."""
    today = timezone.localdate()
    period = today.replace(day=1)
    month_start, month_end = _month_bounds(period)
    month_start_dt = timezone.make_aware(datetime.combine(month_start, time.min))
    month_end_dt = timezone.make_aware(datetime.combine(month_end, time.max))

    month_qs = filter_outreach_messages(
        WhatsappOutboundMessage.objects.filter(
            Q(sent_at__gte=month_start_dt, sent_at__lte=month_end_dt)
            | Q(sent_at__isnull=True, created_at__gte=month_start_dt, created_at__lte=month_end_dt),
        ),
        request,
    )
    sent_month = month_qs.filter(status=WhatsappOutboundMessage.STATUS_SENT).count()
    pending_month = month_qs.filter(
        status__in=(WhatsappOutboundMessage.STATUS_PENDING, WhatsappOutboundMessage.STATUS_SENDING),
    ).count()
    failed_month = month_qs.filter(status=WhatsappOutboundMessage.STATUS_FAILED).count()
    campaign_messages = month_qs.filter(send_type=WhatsappOutboundMessage.SEND_CAMPAIGN).count()

    return {
        'outreach_panel_period_label': _month_label(period),
        'outreach_show_panel': True,
        'outreach_campaigns': filter_by_brand(OutreachCollection.objects.all(), request).count(),
        'outreach_members': _outreach_member_count(request),
        'outreach_sent_month': sent_month,
        'outreach_pending_month': pending_month,
        'outreach_failed_month': failed_month,
        'outreach_campaign_messages_month': campaign_messages,
    }
