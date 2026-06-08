"""Satış CSV içe aktarma."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from common.csv_io import parse_date_tr, parse_decimal
from common.csv_products import parse_product_names_cell, resolve_product_options
from customers.models import Customer
from sales_leads.csv_interim import parse_interim_payments_from_row
from sales_leads.models import SalesLead, SalesLeadInterimPayment


def _cell(row: dict, *keys: str) -> str:
    for key in keys:
        for k, v in row.items():
            if k.strip().upper() == key.upper():
                return (v or '').strip()
    return ''


def _mapped(row: dict, key: str, *legacy: str) -> str:
    val = (row.get(key) or '').strip()
    return val or _cell(row, *legacy)


def import_sales_rows(
    mapped_rows: list[dict],
    *,
    user=None,
    request=None,
    raw_rows: list[dict] | None = None,
) -> dict:
    from common.csv_import_diagnostics import row_preview

    created = 0
    skipped = 0
    interim_payments = 0
    skipped_rows: list[dict] = []
    warnings: list[dict] = []
    raw_rows = raw_rows or mapped_rows

    with transaction.atomic():
        for idx, row in enumerate(mapped_rows):
            line_no = idx + 2
            raw = raw_rows[idx] if idx < len(raw_rows) else row
            name = _mapped(row, 'customer_name', 'AD SOYAD', 'MÜŞTERİ', 'MUSTERI', 'AD')
            if not name:
                skipped += 1
                skipped_rows.append({
                    'row': line_no,
                    'reason': 'Müşteri Adı boş — sütun eşlemesini kontrol edin.',
                    'preview': row_preview(raw),
                })
                continue
            phone = _mapped(row, 'phone', 'TELEFON', 'TEL')
            region = _mapped(row, 'region', 'YER', 'BÖLGE', 'BOLGE')
            project = _mapped(row, 'project', 'PROJE', 'PROJE ADI') or '—'
            sale_date = parse_date_tr(_mapped(row, 'date', 'TARİH', 'TARIH', 'SATIŞ TARİHİ')) or timezone.localdate()
            sale_amount = parse_decimal(_mapped(row, 'total', 'TOPLAM', 'TUTAR'))
            down_payment = parse_decimal(_mapped(row, 'down_payment', 'PEŞİNAT', 'PESINAT'))

            lookup = Customer.objects.filter(name__iexact=name)
            if request is not None:
                from common.brand_scope import filter_customers

                customer = filter_customers(lookup, request).first()
            else:
                customer = lookup.first()
            if customer:
                if phone and customer.phone != phone:
                    customer.phone = phone
                if region and customer.region != region:
                    customer.region = region
                customer.save()
            else:
                if request is not None:
                    from common.brand_scope import assign_brand, get_active_brand
                    from common.brand_team import check_customer_limit_for_request

                    try:
                        blocked = check_customer_limit_for_request(request, brand=get_active_brand(request))
                        if blocked:
                            skipped += 1
                            skipped_rows.append({
                                'row': line_no,
                                'reason': 'müşteri limiti',
                                'preview': row_preview(raw),
                            })
                            continue
                    except ValueError as exc:
                        skipped += 1
                        skipped_rows.append({
                            'row': line_no,
                            'reason': str(exc),
                            'preview': row_preview(raw),
                        })
                        continue
                customer = Customer.objects.create(
                    name=name,
                    phone=phone or None,
                    region=region or None,
                )
                if request is not None:
                    from common.brand_scope import assign_brand

                    assign_brand(customer, request)
                    customer.save(update_fields=['brand_id'])

            lead = SalesLead.objects.create(
                customer=customer,
                sale_date=sale_date,
                project=project,
                sale_amount=sale_amount,
                down_payment=down_payment,
                notes=_mapped(row, 'notes', 'NOT', 'NOTLAR') or '',
                status=SalesLead.STATUS_COMPLETED,
                assigned_to=user if user and user.is_authenticated else None,
            )

            product_names = parse_product_names_cell(_mapped(row, 'products', 'ÜRÜN', 'URUN', 'URUNLER'))
            if product_names:
                options = resolve_product_options(product_names)
                if options:
                    lead.products.set(options)
                    for product in options:
                        customer.products.add(product)
                else:
                    warnings.append({
                        'row': line_no,
                        'message': f'Proje ürünleri bağlanamadı: {", ".join(product_names)}',
                        'preview': name,
                    })

            for order, (amt, pay_date) in enumerate(
                parse_interim_payments_from_row(raw, default_date=sale_date)
            ):
                SalesLeadInterimPayment.objects.create(
                    sales_lead=lead,
                    amount=amt,
                    payment_date=pay_date,
                    sort_order=order,
                )
                interim_payments += 1
            created += 1

    return {
        'created': created,
        'skipped': skipped,
        'skipped_rows': skipped_rows,
        'warnings': warnings,
        'interim_payments': interim_payments,
    }


def import_sales_csv(uploaded_file, *, user=None, request=None, mapping=None) -> dict:
    from common.csv_import_runner import import_from_upload
    return import_from_upload('sales', uploaded_file, user=user, request=request, mapping=mapping)
