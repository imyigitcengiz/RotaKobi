"""Müşteri rehberi CSV içe aktarma — customers.Customer alanları."""

from __future__ import annotations

import logging

from django.db import transaction

from common.csv_io import parse_date_tr
from common.csv_import_diagnostics import row_preview
from common.csv_products import parse_product_names_cell, resolve_product_options
from customers.models import Customer

logger = logging.getLogger(__name__)


def import_customer_rows(rows: list[dict], *, user=None, request=None) -> dict:
    created = 0
    updated = 0
    skipped = 0
    products_linked = 0
    skipped_rows: list[dict] = []
    warnings: list[dict] = []
    log: list[dict] = []

    with transaction.atomic():
        for line_no, row in enumerate(rows, start=2):
            name = (row.get('name') or '').strip()
            if not name:
                skipped += 1
                skipped_rows.append({
                    'row': line_no,
                    'reason': 'Müşteri Adı boş — «Müşteri Adı» sütununu kontrol edin veya satırı düzeltin.',
                    'preview': row_preview(row),
                })
                continue
            phone = (row.get('phone') or '').strip() or None
            region = (row.get('region') or '').strip() or None
            address = (row.get('address') or '').strip() or None
            location_link = (row.get('location_link') or '').strip() or None
            contract_date = parse_date_tr(row.get('contract_date') or '')
            product_names = parse_product_names_cell(row.get('products') or '')

            lookup = Customer.objects.filter(name__iexact=name)
            if request is not None:
                from common.brand_scope import filter_customers

                customer = filter_customers(lookup, request).first()
            else:
                customer = lookup.first()
            action = 'updated' if customer else 'created'
            if customer:
                if phone:
                    customer.phone = phone
                if region:
                    customer.region = region
                if address:
                    customer.address = address
                if location_link:
                    customer.location_link = location_link
                if contract_date:
                    customer.contract_date = contract_date
                customer.save()
                updated += 1
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
                                'preview': row_preview(row),
                            })
                            continue
                    except ValueError as exc:
                        skipped += 1
                        skipped_rows.append({
                            'row': line_no,
                            'reason': str(exc),
                            'preview': row_preview(row),
                        })
                        continue
                customer = Customer(
                    name=name,
                    phone=phone,
                    region=region,
                    address=address,
                    location_link=location_link,
                    contract_date=contract_date,
                )
                if request is not None:
                    from common.brand_scope import assign_brand

                    assign_brand(customer, request)
                elif user:
                    from common.brand_scope import default_brand_for_user

                    brand = default_brand_for_user(user)
                    if brand:
                        customer.brand_id = brand.pk
                customer.save()
                created += 1

            if product_names:
                options = resolve_product_options(product_names)
                if options:
                    customer.products.set(options)
                    products_linked += 1
                    unresolved = [p for p in product_names if p.lower() not in {o.name.lower() for o in options}]
                    if unresolved:
                        warnings.append({
                            'row': line_no,
                            'message': f'Ürün kısmen bağlandı; tanınmayan: {", ".join(unresolved)}',
                            'preview': name,
                        })
                else:
                    warnings.append({
                        'row': line_no,
                        'message': f'Ürünler bağlanamadı: {", ".join(product_names)}',
                        'preview': name,
                    })
            elif row.get('products'):
                warnings.append({
                    'row': line_no,
                    'message': 'Ürün hücresi dolu ama ayrıştırılamadı — «Satın Aldığı Ürünler» eşlemesini kontrol edin.',
                    'preview': row_preview(row),
                })

            log.append({'row': line_no, 'action': action, 'name': name})

    if skipped_rows:
        logger.info('CSV müşteri içe aktarma: %s satır atlandı', len(skipped_rows))
    return {
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'products_linked': products_linked,
        'skipped_rows': skipped_rows,
        'warnings': warnings,
        'log': log[:50],
    }
