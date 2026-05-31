"""CSV içe aktarma — eşleştirilmiş satırları ilgili modüle yönlendirir."""

from __future__ import annotations

from common.csv_import_registry import import_type_config
from common.csv_mapping import apply_column_mapping, auto_map_headers, parse_mapping_payload
from common.csv_io import read_uploaded_csv


def prepare_import_rows(
    rows: list[dict[str, str]],
    headers: list[str],
    import_type: str,
    mapping: dict | str | None = None,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    cfg = import_type_config(import_type)
    if not cfg:
        raise ValueError('Geçersiz içe aktarma türü.')
    fields = list(cfg['fields'])
    if not headers and rows:
        headers = list(rows[0].keys())
    parsed = parse_mapping_payload(mapping) if mapping else {}
    auto = auto_map_headers(headers, fields)
    final_mapping: dict[str, str | None] = {}
    for field in fields:
        chosen = parsed.get(field.key) or auto.get(field.key)
        final_mapping[field.key] = chosen
    mapped = apply_column_mapping(rows, final_mapping)
    clean_mapping = {k: v for k, v in final_mapping.items() if v}
    return mapped, clean_mapping


def run_import(
    import_type: str,
    rows: list[dict[str, str]],
    *,
    user=None,
    raw_rows: list[dict[str, str]] | None = None,
    mapping: dict | str | None = None,
    headers: list[str] | None = None,
) -> dict:
    mapped, _ = prepare_import_rows(rows, headers or (list(rows[0].keys()) if rows else []), import_type, mapping)
    if import_type == 'finance':
        from core_settings.csv_exchange import import_finance_rows
        return import_finance_rows(mapped, user=user)
    if import_type == 'payroll':
        from core_settings.csv_exchange import import_payroll_rows
        return import_payroll_rows(mapped, user=user)
    if import_type == 'sales':
        from sales_leads.csv_import import import_sales_rows
        return import_sales_rows(mapped, user=user, raw_rows=raw_rows or rows)
    if import_type == 'customers':
        from customers.csv_import import import_customer_rows
        return import_customer_rows(mapped, user=user)
    if import_type == 'firms':
        from tools.firm_csv_import import import_firm_rows
        return import_firm_rows(mapped, user=user)
    raise ValueError('Geçersiz içe aktarma türü.')


def import_from_upload(
    import_type: str,
    uploaded_file,
    *,
    user=None,
    mapping: dict | str | None = None,
) -> dict:
    rows = read_uploaded_csv(uploaded_file)
    headers = list(rows[0].keys()) if rows else []
    return run_import(
        import_type,
        rows,
        user=user,
        raw_rows=rows,
        mapping=mapping,
        headers=headers,
    )
