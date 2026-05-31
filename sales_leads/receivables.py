"""Alacak takibi — satış kalan bakiyeleri."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from sales_leads.models import SalesLead


def build_receivables_context(*, overdue_days: int = 30) -> dict:
    today = timezone.localdate()
    leads = list(
        SalesLead.objects.exclude(status=SalesLead.STATUS_CANCELLED)
        .select_related('customer')
        .prefetch_related('interim_payments', 'product_lines__product')
        .order_by('-sale_date', '-created_at')
    )
    receivable_rows = []
    total_receivable = Decimal('0')
    overdue_receivable = Decimal('0')

    for lead in leads:
        remaining = lead.remaining_balance
        if remaining <= 0:
            continue
        days_since = (today - lead.sale_date).days if lead.sale_date else 0
        is_overdue = days_since >= overdue_days
        total_receivable += remaining
        if is_overdue:
            overdue_receivable += remaining

        product_labels = [
            f'{line.product.name} × {line.quantity}'
            for line in lead.product_lines.all()
        ] or [lead.project_display]

        receivable_rows.append({
            'lead': lead,
            'remaining': remaining,
            'days_since': days_since,
            'is_overdue': is_overdue,
            'product_labels': product_labels,
            'products_primary': ', '.join(product_labels[:3]),
            'whatsapp_text': _receivable_whatsapp_text(lead, remaining),
        })

    receivable_rows.sort(key=lambda row: (-row['remaining'], -row['days_since']))

    by_customer: dict[int, dict] = {}
    for row in receivable_rows:
        cid = row['lead'].customer_id
        bucket = by_customer.setdefault(cid, {
            'customer': row['lead'].customer,
            'total': Decimal('0'),
            'count': 0,
        })
        bucket['total'] += row['remaining']
        bucket['count'] += 1
    customer_totals = sorted(by_customer.values(), key=lambda item: -item['total'])

    return {
        'receivable_rows': receivable_rows,
        'receivable_total': total_receivable,
        'receivable_overdue_total': overdue_receivable,
        'receivable_count': len(receivable_rows),
        'receivable_overdue_count': sum(1 for r in receivable_rows if r['is_overdue']),
        'receivable_customer_totals': customer_totals,
        'receivable_overdue_days': overdue_days,
    }


def _receivable_whatsapp_text(lead, remaining: Decimal) -> str:
    products = ', '.join(
        f'{line.product.name}×{line.quantity}' for line in lead.product_lines.all()
    ) or lead.project_display
    return (
        f'Merhaba {lead.customer.name}, '
        f'{products} için kalan ödeme tutarı {remaining:.2f} ₺. '
        f'Ödeme planınız hakkında bilgi alabilir miyiz?'
    )
