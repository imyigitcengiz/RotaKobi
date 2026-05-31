"""Müşteri rehberi CSV içe aktarma."""

from __future__ import annotations

from django.db import transaction

from common.csv_io import parse_date_tr
from customers.models import Customer


def import_customer_rows(rows: list[dict], *, user=None) -> dict:
    created = 0
    updated = 0
    skipped = 0

    with transaction.atomic():
        for row in rows:
            name = (row.get('name') or '').strip()
            if not name:
                skipped += 1
                continue
            phone = (row.get('phone') or '').strip()
            region = (row.get('region') or '').strip()
            address = (row.get('address') or '').strip()
            contract_date = parse_date_tr(row.get('contract_date') or '')

            customer = Customer.objects.filter(name__iexact=name).first()
            if customer:
                if phone:
                    customer.phone = phone
                if region:
                    customer.region = region
                if address:
                    customer.address = address
                if contract_date:
                    customer.contract_date = contract_date
                customer.save()
                updated += 1
            else:
                Customer.objects.create(
                    name=name,
                    phone=phone or None,
                    region=region or None,
                    address=address or None,
                    contract_date=contract_date,
                )
                created += 1

    return {'created': created, 'updated': updated, 'skipped': skipped}
