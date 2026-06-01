"""Para birimi — site ayarından sembol ve biçimlendirme."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

CURRENCY_PRESETS: dict[str, dict[str, str]] = {
    'TRY': {'symbol': '₺', 'label': 'Türk Lirası', 'position': 'after'},
    'USD': {'symbol': '$', 'label': 'ABD Doları', 'position': 'before'},
    'EUR': {'symbol': '€', 'label': 'Euro', 'position': 'after'},
    'GBP': {'symbol': '£', 'label': 'İngiliz Sterlini', 'position': 'before'},
    'CHF': {'symbol': 'CHF', 'label': 'İsviçre Frangı', 'position': 'after'},
    'AED': {'symbol': 'AED', 'label': 'BAE Dirhemi', 'position': 'after'},
    'SAR': {'symbol': 'SAR', 'label': 'Suudi Riyali', 'position': 'after'},
}

CURRENCY_CODE_CHOICES = [(code, meta['label']) for code, meta in CURRENCY_PRESETS.items()]

DEFAULT_CURRENCY_CODE = 'TRY'


@dataclass(frozen=True)
class CurrencyInfo:
    code: str
    symbol: str
    label: str
    position: str  # 'before' | 'after'

    @property
    def is_before(self) -> bool:
        return self.position == 'before'


def currency_info(code: str | None) -> CurrencyInfo:
    key = (code or DEFAULT_CURRENCY_CODE).strip().upper()
    meta = CURRENCY_PRESETS.get(key, CURRENCY_PRESETS[DEFAULT_CURRENCY_CODE])
    return CurrencyInfo(
        code=key if key in CURRENCY_PRESETS else DEFAULT_CURRENCY_CODE,
        symbol=meta['symbol'],
        label=meta['label'],
        position=meta.get('position', 'after'),
    )


def currency_from_settings(settings) -> CurrencyInfo:
    if settings is None:
        return currency_info(DEFAULT_CURRENCY_CODE)
    return currency_info(getattr(settings, 'currency_code', None) or DEFAULT_CURRENCY_CODE)


def all_currency_symbols() -> tuple[str, ...]:
    return tuple(meta['symbol'] for meta in CURRENCY_PRESETS.values())


def _format_amount_number(value, *, decimals: int = 2) -> str:
    if value is None or value == '':
        return '-'
    try:
        num = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    quantized = num.quantize(Decimal(10) ** -decimals) if decimals >= 0 else num
    text = f'{quantized:,.{decimals}f}'
    return text.replace(',', 'X').replace('.', ',').replace('X', '.')


def format_money(
    value,
    *,
    settings=None,
    currency: CurrencyInfo | None = None,
    decimals: int = 2,
    include_symbol: bool = True,
) -> str:
    """Örnek: 1.234,56 ₺ veya $1,234.56 (konuma göre)."""
    number = _format_amount_number(value, decimals=decimals)
    if number == '-':
        return number
    if not include_symbol:
        return number
    cur = currency or currency_from_settings(settings)
    if cur.is_before:
        return f'{cur.symbol}{number}'
    return f'{number} {cur.symbol}'


def strip_currency_symbols(text: str) -> str:
    s = (text or '').strip()
    for sym in sorted(all_currency_symbols(), key=len, reverse=True):
        s = s.replace(sym, '')
    return s.strip()
