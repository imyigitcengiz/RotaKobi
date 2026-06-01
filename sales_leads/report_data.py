"""Satış raporu bağlamı — ekran ve yazdırma paylaşır."""

from __future__ import annotations

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Sum
from django.utils import timezone

from sales_leads.models import SalesLead


def _money(value) -> str:
    from common.currency import format_money

    return format_money(value, decimals=2)


def _completed_leads():
    return SalesLead.objects.filter(status=SalesLead.STATUS_COMPLETED)


def _lead_queryset():
    return (
        SalesLead.objects.select_related('customer', 'assigned_to')
        .prefetch_related(
            'products',
            'interim_payments',
            'product_lines__product',
            'product_lines__color',
            'customer__products',
            'customer__service_records',
        )
    )


def _status_label(status: str) -> str:
    return {
        SalesLead.STATUS_COMPLETED: 'Tamamlandı',
        SalesLead.STATUS_PENDING: 'Beklemede',
        SalesLead.STATUS_CANCELLED: 'İptal',
    }.get(status, status)


def _lead_product_line_rows(lead) -> list[dict]:
    rows = []
    for line in lead.product_lines.all():
        rows.append({
            'name': line.product.name,
            'quantity': line.quantity,
            'color': line.color.name if line.color_id else '',
            'note': (line.note or '').strip(),
            'headline': f'{line.product.name} × {line.quantity}',
            'detail': ' · '.join(
                part for part in (
                    line.color.name if line.color_id else '',
                    line.note or '',
                ) if part
            ),
        })
    if rows:
        return rows
    for product in lead.products.all():
        rows.append({
            'name': product.name,
            'quantity': 1,
            'color': '',
            'note': '',
            'headline': product.name,
            'detail': '',
        })
    return rows


def _lead_products_primary(lead) -> str:
    rows = _lead_product_line_rows(lead)
    if rows:
        return ', '.join(row['headline'] for row in rows)
    if lead.project:
        return lead.project
    return '—'


def _build_product_summary(report_leads) -> list[dict]:
    summary: dict[str, dict] = {}
    for lead in report_leads:
        seen_in_sale: set[str] = set()
        for row in _lead_product_line_rows(lead):
            name = row['name']
            bucket = summary.setdefault(name, {'name': name, 'quantity': 0, 'sales': 0})
            bucket['quantity'] += row['quantity']
            if name not in seen_in_sale:
                bucket['sales'] += 1
                seen_in_sale.add(name)
    return sorted(summary.values(), key=lambda item: (-item['quantity'], item['name']))


def _attach_lead_report_fields(lead, *, col_count: int) -> None:
    payments = list(lead.interim_payments.all())
    lead.report_interim_cells = []
    for i in range(col_count):
        if i < len(payments):
            payment = payments[i]
            lead.report_interim_cells.append({
                'amount': payment.amount,
                'payment_date': payment.payment_date,
                'display': (
                    f'{payment.payment_date.strftime("%d.%m.%Y")} · {_money(payment.amount)}'
                    if payment.payment_date
                    else _money(payment.amount)
                ),
            })
        else:
            lead.report_interim_cells.append(None)
    lead.status_label = _status_label(lead.status)
    lead.report_product_lines = _lead_product_line_rows(lead)
    lead.report_products_primary = _lead_products_primary(lead)
    lead.report_project_ref = (lead.project or '').strip()


def build_sales_report_context(request=None) -> dict:
    status_filter = ''
    if request is not None:
        status_filter = request.GET.get('status', '').strip()

    completed = _completed_leads()
    today = timezone.localdate()

    monthly = []
    month_cursor = today.replace(day=1)
    for i in range(5, -1, -1):
        month = month_cursor - relativedelta(months=i)
        next_month = month + relativedelta(months=1)
        qs = completed.filter(sale_date__gte=month, sale_date__lt=next_month)
        monthly.append({
            'label': month.strftime('%m.%Y'),
            'count': qs.count(),
            'amount': qs.aggregate(total=Sum('sale_amount'))['total'] or Decimal('0'),
        })

    region_stats = (
        completed.exclude(customer__region__isnull=True)
        .exclude(customer__region='')
        .values('customer__region')
        .annotate(total=Count('id'), amount=Sum('sale_amount'))
        .order_by('-total')[:10]
    )
    status_breakdown = (
        SalesLead.objects.values('status')
        .annotate(total=Count('id'), amount=Sum('sale_amount'))
        .order_by('-total')
    )
    for row in status_breakdown:
        row['label'] = _status_label(row['status'])

    leads_qs = _lead_queryset().order_by('-sale_date', '-created_at')
    if status_filter:
        leads_qs = leads_qs.filter(status=status_filter)
    report_leads = list(leads_qs)

    max_interim = max((lead.interim_payments.count() for lead in report_leads), default=0)
    col_count = max(max_interim, 1)
    for lead in report_leads:
        _attach_lead_report_fields(lead, col_count=col_count)

    totals = {
        'count': len(report_leads),
        'sale_amount': sum((lead.sale_amount or Decimal('0')) for lead in report_leads),
        'down_payment': sum((lead.down_payment or Decimal('0')) for lead in report_leads),
        'interim': sum(lead.interim_payments_total for lead in report_leads),
        'remaining': sum(lead.remaining_balance for lead in report_leads),
    }

    return {
        'monthly_stats': monthly,
        'region_stats': region_stats,
        'status_breakdown': status_breakdown,
        'report_leads': report_leads,
        'report_totals': totals,
        'max_interim_count': max_interim,
        'interim_column_count': col_count,
        'interim_column_indices': list(range(col_count)),
        'report_generated_at': timezone.localtime(),
        'report_status_filter': status_filter,
        'report_status_choices': SalesLead.STATUS_CHOICES,
        'product_summary': _build_product_summary(report_leads),
    }
