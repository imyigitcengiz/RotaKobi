"""Tedarikçi borçları — vade ve ödeme kaydı."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from core_settings.models import FinanceRecord, SupplierPayable


def build_payables_context(*, request=None, overdue_days: int = 30) -> dict:
    today = timezone.localdate()
    qs = SupplierPayable.objects.order_by('due_date', '-created_at')
    if request is not None:
        from common.brand_scope import filter_by_brand
        qs = filter_by_brand(qs, request)
    rows = list(qs)
    payable_rows = []
    total_open = Decimal('0')
    overdue_total = Decimal('0')

    for item in rows:
        remaining = item.remaining
        if remaining <= 0:
            continue
        days_over = None
        is_overdue = False
        if item.due_date:
            days_over = (today - item.due_date).days
            is_overdue = days_over > overdue_days
        total_open += remaining
        if is_overdue:
            overdue_total += remaining
        payable_rows.append({
            'payable': item,
            'remaining': remaining,
            'days_over': days_over,
            'is_overdue': is_overdue,
        })

    payable_rows.sort(key=lambda row: (-row['remaining'], row['payable'].due_date or today))

    return {
        'payable_rows': payable_rows,
        'payable_total': total_open,
        'payable_overdue_total': overdue_total,
        'payable_count': len(payable_rows),
        'payable_overdue_count': sum(1 for row in payable_rows if row['is_overdue']),
        'payable_overdue_days': overdue_days,
    }


def create_payable(
    *,
    supplier_name: str,
    amount: Decimal,
    due_date=None,
    invoice_ref: str = '',
    notes: str = '',
    request=None,
    brand=None,
) -> SupplierPayable:
    payable = SupplierPayable(
        supplier_name=supplier_name.strip(),
        amount=amount,
        due_date=due_date,
        invoice_ref=invoice_ref.strip(),
        notes=notes.strip(),
    )
    if request is not None:
        from common.brand_scope import assign_brand
        assign_brand(payable, request)
    elif brand is not None:
        payable.brand = brand
    payable.save()
    return payable


@transaction.atomic
def record_payment(payable: SupplierPayable, amount: Decimal, user, request=None) -> FinanceRecord:
    if amount <= 0:
        raise ValueError('Ödeme tutarı 0\'dan büyük olmalı.')
    remaining = payable.remaining
    if amount > remaining:
        raise ValueError('Ödeme tutarı kalan borçtan fazla olamaz.')
    payable.paid_amount = (payable.paid_amount or Decimal('0')) + amount
    payable.save(update_fields=['paid_amount'])
    title = f'Tedarikçi ödemesi — {payable.supplier_name}'
    if payable.invoice_ref:
        title += f' ({payable.invoice_ref})'
    default_account = _default_cash_account()
    record = FinanceRecord(
        record_type=FinanceRecord.TYPE_EXPENSE,
        category='supplier',
        title=title,
        amount=amount,
        record_date=timezone.localdate(),
        notes=payable.notes or '',
        recorded_by=user,
        cash_account=default_account,
    )
    if request is not None:
        from common.brand_scope import assign_brand

        assign_brand(record, request)
    record.save()
    return record


def _default_cash_account():
    from core_settings.cash_accounts import ensure_default_account
    return ensure_default_account()


def parse_decimal(raw: str) -> Decimal:
    try:
        return Decimal(str(raw).replace(',', '.').strip())
    except (InvalidOperation, ValueError):
        raise ValueError('Geçerli tutar girin.')
