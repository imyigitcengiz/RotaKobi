"""CSV sütun eşleştirme — otomatik tanıma ve canonical satır dönüşümü."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def normalize_header(value: str) -> str:
    s = (value or '').strip().upper()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^A-Z0-9]+', '_', s)
    return s.strip('_')


@dataclass(frozen=True)
class ImportField:
    key: str
    label: str
    required: bool = False
    aliases: tuple[str, ...] = ()


def auto_map_headers(csv_headers: list[str], fields: list[ImportField]) -> dict[str, str]:
    """canonical_key → csv header adı."""
    normalized_csv = {normalize_header(h): h for h in csv_headers if h}
    mapping: dict[str, str] = {}

    for field in fields:
        candidates = [field.key, field.label, *field.aliases]
        for cand in candidates:
            norm = normalize_header(cand)
            if norm in normalized_csv:
                mapping[field.key] = normalized_csv[norm]
                break
        if field.key not in mapping:
            for norm, original in normalized_csv.items():
                if norm and (norm in normalize_header(field.label) or normalize_header(field.label) in norm):
                    mapping[field.key] = original
                    break
    return mapping


def apply_column_mapping(
    rows: list[dict[str, str]],
    mapping: dict[str, str | None],
) -> list[dict[str, str]]:
    """Her satırı canonical alan anahtarlarına dönüştür."""
    out: list[dict[str, str]] = []
    for row in rows:
        mapped: dict[str, str] = {}
        for key, header in mapping.items():
            if header and header in row:
                mapped[key] = (row.get(header) or '').strip()
            else:
                mapped[key] = ''
        out.append(mapped)
    return out


def parse_mapping_payload(raw) -> dict[str, str | None]:
    """JSON veya form dict → canonical_key: csv_header | None."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, str):
        import json
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    else:
        return {}
    out: dict[str, str | None] = {}
    for key, val in data.items():
        if val in (None, '', '__skip__'):
            out[str(key)] = None
        else:
            out[str(key)] = str(val).strip()
    return out
