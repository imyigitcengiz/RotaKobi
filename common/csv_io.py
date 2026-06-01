"""CSV okuma/yazma — Türkçe Excel uyumlu (; ayraç, UTF-8 BOM)."""

from __future__ import annotations

import csv
import io
from typing import Iterable


def csv_response(filename: str, rows: Iterable[list], header: list[str] | None = None):
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';')
    if header:
        writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return response


def _detect_delimiter(text: str) -> str:
    sample = text[:4096]
    semi = sample.count(';')
    comma = sample.count(',')
    return ',' if comma > semi else ';'


def read_csv_text(text: str) -> tuple[list[str], list[dict[str, str]]]:
    delimiter = _detect_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return [], []
    header = [h.strip() for h in rows[0]]
    out: list[dict[str, str]] = []
    for line in rows[1:]:
        if not any(cell.strip() for cell in line):
            continue
        padded = line + [''] * (len(header) - len(line))
        out.append(dict(zip(header, [c.strip() for c in padded[: len(header)]])))
    return header, out


def read_uploaded_csv(uploaded_file) -> list[dict[str, str]]:
    raw = uploaded_file.read()
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    text = raw.decode('utf-8-sig', errors='replace')
    _, rows = read_csv_text(text)
    return rows


def parse_decimal(value: str):
    from decimal import Decimal, InvalidOperation

    if value is None:
        return None
    from common.currency import strip_currency_symbols

    s = strip_currency_symbols(str(value).replace(' ', ''))
    if not s or s in ('-', '—'):
        return None
    s = s.replace('.', '').replace(',', '.') if s.count(',') == 1 and s.count('.') > 1 else s.replace(',', '.')
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_date_tr(value: str):
    from datetime import datetime

    s = (value or '').strip()
    if not s or s in ('-', '—'):
        return None
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
