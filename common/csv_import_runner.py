"""CSV içe aktarma — eşleştirilmiş satırları ilgili modüle yönlendirir."""

from __future__ import annotations

from common.csv_import_diagnostics import (
    build_mapping_summary,
    empty_result_shell,
    merge_import_result,
)
from common.csv_import_registry import (
    CUSTOMER_SALE_FIELD_KEYS,
    import_type_config,
    import_type_fields,
    user_can_import_sales_with_customers,
)
from common.csv_mapping import apply_column_mapping
from common.csv_io import read_uploaded_csv


def prepare_import_rows(
    rows: list[dict[str, str]],
    headers: list[str],
    import_type: str,
    mapping: dict | str | None = None,
    *,
    use_auto_mapping: bool = True,
    user=None,
) -> tuple[list[dict[str, str]], dict[str, str | None], dict[str, str], dict[str, str]]:
    from common.csv_import_diagnostics import resolve_import_mapping

    if not import_type_config(import_type):
        raise ValueError('Geçersiz içe aktarma türü.')
    fields = list(import_type_fields(import_type, user))
    if not headers and rows:
        headers = list(rows[0].keys())
    final_mapping, sources, auto = resolve_import_mapping(
        headers,
        fields,
        import_type,
        user_mapping=mapping,
        use_auto_mapping=use_auto_mapping,
    )
    mapped = apply_column_mapping(rows, final_mapping)
    return mapped, final_mapping, sources, auto


def _row_has_sale_data(row: dict[str, str]) -> bool:
    for key in ('project', 'date', 'total', 'down_payment', 'notes'):
        if (row.get(key) or '').strip():
            return True
    return False


def _sales_rows_from_customer_import(
    mapped_rows: list[dict[str, str]],
    raw_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    sale_mapped: list[dict[str, str]] = []
    sale_raw: list[dict[str, str]] = []
    for idx, row in enumerate(mapped_rows):
        if not _row_has_sale_data(row):
            continue
        sale_row = dict(row)
        sale_row['customer_name'] = (row.get('name') or row.get('customer_name') or '').strip()
        sale_mapped.append(sale_row)
        sale_raw.append(raw_rows[idx] if idx < len(raw_rows) else row)
    return sale_mapped, sale_raw


def _customer_import_includes_sales(
    final_mapping: dict[str, str | None],
    user,
) -> bool:
    if not user_can_import_sales_with_customers(user):
        return False
    return any(final_mapping.get(k) for k in CUSTOMER_SALE_FIELD_KEYS)


def _interim_headers(import_type: str, raw_rows: list[dict], headers: list[str] | None) -> list[str]:
    if import_type not in ('sales', 'customers') or not raw_rows:
        return []
    from sales_leads.csv_interim import detect_interim_headers

    return [c['header'] for c in detect_interim_headers(headers or list(raw_rows[0].keys()))]


def _attach_report_meta(
    result: dict,
    *,
    import_type: str,
    headers: list[str],
    final_mapping: dict[str, str | None],
    mapping_sources: dict[str, str],
    auto_mapping: dict[str, str],
    use_auto_mapping: bool,
    raw_rows: list[dict] | None,
    user=None,
) -> dict:
    extra = _interim_headers(import_type, raw_rows or [], headers)
    summary = build_mapping_summary(
        import_type,
        headers,
        final_mapping,
        mapping_sources,
        extra_used_headers=extra,
        user=user,
    )
    out = merge_import_result(
        result,
        mapping={k: v for k, v in final_mapping.items() if v},
        mapping_sources=mapping_sources,
        auto_mapping=auto_mapping,
        unmapped_columns=summary['unmapped_columns'],
        mapped_field_lines=summary['mapped_fields'],
        skipped_field_lines=summary['skipped_fields'],
        use_auto_mapping=use_auto_mapping,
        total_rows=result.get('total_rows'),
    )
    return out


def _import_request(user, request=None):
    if request is not None:
        return request
    from django.test import RequestFactory

    from common.brand_scope import SESSION_ACTIVE_BRAND, default_brand_for_user

    req = RequestFactory().get('/')
    req.user = user
    brand = default_brand_for_user(user) if user and getattr(user, 'is_authenticated', True) else None
    req.session = {SESSION_ACTIVE_BRAND: brand.pk} if brand else {}
    return req


def run_import(
    import_type: str,
    rows: list[dict[str, str]],
    *,
    user=None,
    request=None,
    raw_rows: list[dict[str, str]] | None = None,
    mapping: dict | str | None = None,
    headers: list[str] | None = None,
    use_auto_mapping: bool = True,
) -> dict:
    hdrs = headers or (list(rows[0].keys()) if rows else [])
    source_rows = raw_rows or rows
    mapped, final_mapping, sources, auto = prepare_import_rows(
        rows,
        hdrs,
        import_type,
        mapping,
        use_auto_mapping=use_auto_mapping,
        user=user,
    )
    shell = empty_result_shell(import_type)
    shell['total_rows'] = len(rows)
    request = _import_request(user, request)

    if import_type == 'finance':
        from core_settings.csv_exchange import import_finance_rows
        result = import_finance_rows(mapped, user=user, request=request)
    elif import_type == 'payroll':
        from core_settings.csv_exchange import import_payroll_rows
        result = import_payroll_rows(mapped, user=user)
    elif import_type == 'sales':
        from sales_leads.csv_import import import_sales_rows
        result = import_sales_rows(
            mapped, user=user, request=request, raw_rows=source_rows,
        )
    elif import_type == 'customers':
        from customers.csv_import import import_customer_rows
        from sales_leads.csv_import import import_sales_rows

        result = import_customer_rows(mapped, user=user, request=request)
        if _customer_import_includes_sales(final_mapping, user):
            sales_mapped, sales_raw = _sales_rows_from_customer_import(mapped, source_rows)
            if sales_mapped:
                sales_result = import_sales_rows(
                    sales_mapped,
                    user=user,
                    request=request,
                    raw_rows=sales_raw,
                )
                result = merge_import_result(
                    result,
                    sales_created=sales_result.get('created', 0),
                    sales_skipped=sales_result.get('skipped', 0),
                    interim_payments=(
                        (result.get('interim_payments') or 0)
                        + (sales_result.get('interim_payments') or 0)
                    ),
                )
                for key in ('skipped_rows', 'warnings', 'log'):
                    if sales_result.get(key):
                        result[key] = list(result.get(key, [])) + list(sales_result[key])
                result['skipped'] = (result.get('skipped') or 0) + (sales_result.get('skipped') or 0)
    elif import_type == 'firms':
        from tools.firm_csv_import import import_firm_rows
        result = import_firm_rows(mapped, user=user)
    else:
        raise ValueError('Geçersiz içe aktarma türü.')

    return _attach_report_meta(
        merge_import_result(shell, **result),
        import_type=import_type,
        headers=hdrs,
        final_mapping=final_mapping,
        mapping_sources=sources,
        auto_mapping=auto,
        use_auto_mapping=use_auto_mapping,
        raw_rows=source_rows,
        user=user,
    )


def import_from_upload(
    import_type: str,
    uploaded_file,
    *,
    user=None,
    request=None,
    mapping: dict | str | None = None,
    use_auto_mapping: bool = True,
) -> dict:
    rows = read_uploaded_csv(uploaded_file)
    headers = list(rows[0].keys()) if rows else []
    return run_import(
        import_type,
        rows,
        user=user,
        request=request,
        raw_rows=rows,
        mapping=mapping,
        headers=headers,
        use_auto_mapping=use_auto_mapping,
    )
