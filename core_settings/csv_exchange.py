"""Gelir/gider ve maaş/avans CSV alışverişi."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from common.csv_io import parse_date_tr, parse_decimal, read_uploaded_csv
from core_settings.models import FinanceRecord, PersonnelPayment, ServicePersonnel
from core_settings.payroll import parse_period


def _cell(row: dict, *keys: str) -> str:
    for key in keys:
        for k, v in row.items():
            if k.strip().upper() == key.upper():
                return (v or '').strip()
    return ''


def import_finance_csv(uploaded_file, *, user=None) -> dict:
    rows = read_uploaded_csv(uploaded_file)
    created = 0
    with transaction.atomic():
        for row in rows:
            raw_type = _cell(row, 'TÜR', 'TUR', 'TYPE').lower()
            if raw_type in ('gelir', 'income', 'g'):
                record_type = FinanceRecord.TYPE_INCOME
            elif raw_type in ('gider', 'expense', 'e'):
                record_type = FinanceRecord.TYPE_EXPENSE
            else:
                continue
            title = _cell(row, 'AÇIKLAMA', 'ACIKLAMA', 'BAŞLIK', 'BASLIK')
            amount = parse_decimal(_cell(row, 'TUTAR', 'MİKTAR', 'MIKTAR'))
            record_date = parse_date_tr(_cell(row, 'TARİH', 'TARIH')) or timezone.localdate()
            if not title or not amount or amount <= 0:
                continue
            FinanceRecord.objects.create(
                record_type=record_type,
                title=title,
                amount=amount,
                record_date=record_date,
                notes=_cell(row, 'NOT', 'NOTLAR'),
                recorded_by=user if user and user.is_authenticated else None,
            )
            created += 1
    return {'created': created}


def import_payroll_csv(uploaded_file, *, user=None) -> dict:
    rows = read_uploaded_csv(uploaded_file)
    created = 0
    skipped = 0
    personnel_by_name = {
        p.name.strip().lower(): p
        for p in ServicePersonnel.objects.filter(is_active=True)
    }
    with transaction.atomic():
        for row in rows:
            pname = _cell(row, 'PERSONEL', 'AD SOYAD', 'AD')
            personnel = personnel_by_name.get(pname.lower())
            if not personnel:
                skipped += 1
                continue
            period_raw = _cell(row, 'DÖNEM', 'DONEM', 'PERIOD')
            try:
                period = parse_period(period_raw) if period_raw else timezone.localdate().replace(day=1)
            except ValueError:
                skipped += 1
                continue
            raw_type = _cell(row, 'TÜR', 'TUR', 'TYPE').lower()
            amount = parse_decimal(_cell(row, 'TUTAR', 'MİKTAR'))
            if not amount or amount <= 0:
                skipped += 1
                continue
            payment_date = parse_date_tr(_cell(row, 'TARİH', 'TARIH', 'ÖDEME TARİHİ')) or timezone.localdate()
            notes = _cell(row, 'NOT', 'NOTLAR')

            if raw_type in ('avans', 'advance', 'a'):
                ptype = PersonnelPayment.TYPE_ADVANCE
            elif raw_type in ('maaş', 'maas', 'salary', 'm'):
                ptype = PersonnelPayment.TYPE_SALARY
            else:
                skipped += 1
                continue

            PersonnelPayment.objects.create(
                personnel=personnel,
                payment_type=ptype,
                period=period,
                amount=amount,
                payment_date=payment_date,
                notes=notes,
                recorded_by=user if user and user.is_authenticated else None,
            )
            created += 1
    return {'created': created, 'skipped': skipped}


def export_payroll_payments_rows(period_from, period_to, personnel_qs=None):
    from core_settings.payroll import iter_period_months, period_label

    if personnel_qs is None:
        personnel_qs = ServicePersonnel.objects.filter(is_active=True).order_by('name')
    rows = []
    for month in iter_period_months(period_from, period_to):
        payments = PersonnelPayment.objects.filter(
            period=month,
            personnel__in=personnel_qs,
        ).select_related('personnel').order_by('payment_date', 'id')
        for pay in payments:
            rows.append([
                month.strftime('%Y-%m'),
                pay.personnel.name,
                'avans' if pay.payment_type == PersonnelPayment.TYPE_ADVANCE else 'maaş',
                pay.amount,
                pay.payment_date.strftime('%d.%m.%Y'),
                pay.notes or '',
            ])
    return rows, period_label(period_from), period_label(period_to)
