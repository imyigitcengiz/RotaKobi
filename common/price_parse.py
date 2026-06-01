"""Türkçe para girişi (1.234,56) → Decimal."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from common.currency import strip_currency_symbols


def parse_tr_decimal(value) -> Decimal | None:
    if value is None or value == '':
        return None
    if isinstance(value, Decimal):
        return value
    s = strip_currency_symbols(str(value).replace(' ', ''))
    if not s:
        return None
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError('Geçersiz tutar. Örnek: 1500 veya 1500,50') from exc
