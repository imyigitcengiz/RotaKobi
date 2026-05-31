"""Kasa bakiyesi — gelir/gider, isteğe bağlı maaş/avans ve satış tahsilatları."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from core_settings.models import CashSettings, FinanceRecord, PersonnelPayment


@dataclass
class CashSnapshot:
    opening_balance: Decimal
    opening_date: date | None
    finance_income: Decimal
    finance_expense: Decimal
    payroll_out: Decimal
    sales_in: Decimal
    current_balance: Decimal
    include_payroll: bool
    include_sales: bool


def get_cash_settings() -> CashSettings:
    obj, _ = CashSettings.objects.get_or_create(pk=1)
    return obj


def _sales_collections_total() -> Decimal:
    from sales_leads.models import SalesLead, SalesLeadInterimPayment

    down = SalesLead.objects.aggregate(t=Sum('down_payment'))['t'] or Decimal('0')
    interim = SalesLeadInterimPayment.objects.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    return down + interim


def build_cash_snapshot() -> CashSnapshot:
    settings = get_cash_settings()
    finance_income = FinanceRecord.objects.filter(
        record_type=FinanceRecord.TYPE_INCOME,
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    finance_expense = FinanceRecord.objects.filter(
        record_type=FinanceRecord.TYPE_EXPENSE,
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    payroll_out = Decimal('0')
    if settings.include_payroll_in_balance:
        payroll_out = PersonnelPayment.objects.aggregate(t=Sum('amount'))['t'] or Decimal('0')

    sales_in = Decimal('0')
    if settings.include_sales_collections_in_balance:
        sales_in = _sales_collections_total()

    current = (
        settings.opening_balance
        + finance_income
        + sales_in
        - finance_expense
        - payroll_out
    )

    return CashSnapshot(
        opening_balance=settings.opening_balance,
        opening_date=settings.opening_date,
        finance_income=finance_income,
        finance_expense=finance_expense,
        payroll_out=payroll_out,
        sales_in=sales_in,
        current_balance=current,
        include_payroll=settings.include_payroll_in_balance,
        include_sales=settings.include_sales_collections_in_balance,
    )


def save_cash_settings(*, opening_balance, opening_date, include_payroll, include_sales):
    settings = get_cash_settings()
    settings.opening_balance = opening_balance
    settings.opening_date = opening_date or None
    settings.include_payroll_in_balance = include_payroll
    settings.include_sales_collections_in_balance = include_sales
    settings.save()
    return settings
