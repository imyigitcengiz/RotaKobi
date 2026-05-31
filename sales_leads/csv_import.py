"""Satış CSV içe aktarma."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from common.csv_io import parse_date_tr, parse_decimal, read_uploaded_csv
from customers.models import Customer
from sales_leads.models import SalesLead, SalesLeadInterimPayment


def _cell(row: dict, *keys: str) -> str:
    for key in keys:
        for k, v in row.items():
            if k.strip().upper() == key.upper():
                return (v or '').strip()
    return ''


def import_sales_csv(uploaded_file, *, user=None) -> dict:
    rows = read_uploaded_csv(uploaded_file)
    created = 0
    skipped = 0
    errors: list[str] = []

    with transaction.atomic():
        for idx, row in enumerate(rows, start=2):
            name = _cell(row, 'AD SOYAD', 'MÜŞTERİ', 'MUSTERI', 'AD')
            if not name:
                skipped += 1
                continue
            phone = _cell(row, 'TELEFON', 'TEL')
            region = _cell(row, 'YER', 'BÖLGE', 'BOLGE')
            project = _cell(row, 'PROJE', 'PROJE ADI') or '—'
            sale_date = parse_date_tr(_cell(row, 'TARİH', 'TARIH', 'SATIŞ TARİHİ')) or timezone.localdate()
            sale_amount = parse_decimal(_cell(row, 'TOPLAM', 'TUTAR'))
            down_payment = parse_decimal(_cell(row, 'PEŞİNAT', 'PESINAT'))

            customer, _ = Customer.objects.get_or_create(
                name=name,
                defaults={'phone': phone, 'region': region},
            )
            if phone and customer.phone != phone:
                customer.phone = phone
            if region and customer.region != region:
                customer.region = region
            customer.save()

            lead = SalesLead.objects.create(
                customer=customer,
                sale_date=sale_date,
                project=project,
                sale_amount=sale_amount,
                down_payment=down_payment,
                notes=_cell(row, 'NOT', 'NOTLAR') or '',
                status=SalesLead.STATUS_COMPLETED,
                assigned_to=user if user and user.is_authenticated else None,
            )

            interim_cols = sorted(
                [k for k in row if k.upper().startswith('ARA ÖDEME') or k.upper().startswith('ARA ODEME')],
                key=lambda x: x,
            )
            date_cols = [k for k in interim_cols if 'TARİH' in k.upper() or 'TARIH' in k.upper()]
            amount_cols = [k for k in interim_cols if k not in date_cols]
            if not amount_cols:
                amount_cols = ['ARA ÖDEME']
            order = 0
            for col in amount_cols:
                amt = parse_decimal(row.get(col, ''))
                if not (amt and amt > 0):
                    continue
                date_key = col.replace('ARA ÖDEME', 'ARA ÖDEME TARİH').replace('ARA ODEME', 'ARA ODEME TARIH')
                pay_date = parse_date_tr(_cell(row, date_key, f'{col} TARİH', f'{col} TARIH')) or sale_date
                SalesLeadInterimPayment.objects.create(
                    sales_lead=lead,
                    amount=amt,
                    payment_date=pay_date,
                    sort_order=order,
                )
                order += 1
            created += 1

    return {'created': created, 'skipped': skipped, 'errors': errors}
