"""Firma rehberi CSV içe aktarma."""

from __future__ import annotations

from django.db import transaction

from tools.firm_directory import create_manual_firm


def import_firm_rows(rows: list[dict], *, user=None) -> dict:
    created = 0
    skipped = 0

    with transaction.atomic():
        for row in rows:
            name = (row.get('name') or '').strip()
            if not name or name == '-':
                skipped += 1
                continue
            phone = (row.get('phone') or '').strip()
            if phone == '-':
                phone = ''
            region = (row.get('region') or '').strip()
            address = (row.get('address') or '').strip()
            website = (row.get('website') or '').strip()
            notes_parts = []
            if address:
                notes_parts.append(address)
            if website and website != '-':
                notes_parts.append(f'Web: {website}')
            extra = (row.get('notes') or '').strip()
            if extra:
                notes_parts.append(extra)
            notes = ' | '.join(notes_parts)[:255]

            create_manual_firm(
                name=name,
                phone=phone,
                region=region,
                notes=notes,
            )
            created += 1

    return {'created': created, 'skipped': skipped}
