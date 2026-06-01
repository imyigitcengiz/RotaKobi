"""Mesai saati planları — haftalık çalışma saatleri."""

from __future__ import annotations

import re
TIME_RE = re.compile(r'^([01]?\d|2[0-3]):([0-5]\d)$')

WEEKDAY_DEFS: tuple[dict[str, str], ...] = (
    {'key': 'monday', 'label': 'Pazartesi', 'short': 'Pzt'},
    {'key': 'tuesday', 'label': 'Salı', 'short': 'Sal'},
    {'key': 'wednesday', 'label': 'Çarşamba', 'short': 'Çar'},
    {'key': 'thursday', 'label': 'Perşembe', 'short': 'Per'},
    {'key': 'friday', 'label': 'Cuma', 'short': 'Cum'},
    {'key': 'saturday', 'label': 'Cumartesi', 'short': 'Cmt'},
    {'key': 'sunday', 'label': 'Pazar', 'short': 'Paz'},
)


def default_weekly_hours() -> dict[str, dict]:
    """Varsayılan: Pzt–Cum 09:00–18:00, Cmt 09:00–13:00, Paz kapalı."""
    base = {d['key']: {'work': False, 'start': '', 'end': ''} for d in WEEKDAY_DEFS}
    for key in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday'):
        base[key] = {'work': True, 'start': '09:00', 'end': '18:00'}
    base['saturday'] = {'work': True, 'start': '09:00', 'end': '13:00'}
    return base


def _parse_time(value: str) -> str | None:
    s = (value or '').strip()[:5]
    if not s:
        return None
    if len(s) == 4 and ':' not in s:
        s = s[:2] + ':' + s[2:]
    if TIME_RE.match(s):
        parts = s.split(':')
        return f'{int(parts[0]):02d}:{parts[1]}'
    return None


def normalize_weekly_hours(raw: dict | None) -> dict[str, dict]:
    """Gün anahtarlarına göre çalışma saatlerini doğrula."""
    source = raw if isinstance(raw, dict) else {}
    defaults = default_weekly_hours()
    out: dict[str, dict] = {}
    for day in WEEKDAY_DEFS:
        key = day['key']
        if key in source and isinstance(source[key], dict):
            row = source[key]
        else:
            row = defaults[key]
        work = bool(row.get('work'))
        start = _parse_time(row.get('start', ''))
        end = _parse_time(row.get('end', ''))
        if work:
            if not start or not end:
                work = False
                start = end = None
            elif start >= end:
                work = False
                start = end = None
        else:
            start = end = None
        if not work:
            out[key] = {'work': False, 'start': '', 'end': ''}
        else:
            out[key] = {'work': True, 'start': start, 'end': end}
    return out


def weekly_hours_from_request(post) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for day in WEEKDAY_DEFS:
        key = day['key']
        rows[key] = {
            'work': post.get(f'day_{key}_work') == 'on',
            'start': post.get(f'day_{key}_start', ''),
            'end': post.get(f'day_{key}_end', ''),
        }
    return normalize_weekly_hours(rows)


def plan_display_rows(plan=None) -> list[dict]:
    """Şablon tablosu için satırlar."""
    if plan and plan.weekly_hours:
        hours = normalize_weekly_hours(plan.weekly_hours)
    else:
        hours = default_weekly_hours()
    rows = []
    for day in WEEKDAY_DEFS:
        key = day['key']
        cell = hours.get(key, {'work': False, 'start': '', 'end': ''})
        rows.append({**day, **cell})
    return rows


def format_day_cell(cell: dict) -> str:
    if not cell.get('work'):
        return 'Kapalı'
    start = cell.get('start') or ''
    end = cell.get('end') or ''
    if start and end:
        return f'{start} – {end}'
    return 'Açık'


def format_plan_summary(plan, *, max_days: int = 7) -> str:
    hours = normalize_weekly_hours(plan.weekly_hours if plan else None)
    parts = []
    for day in WEEKDAY_DEFS[:max_days]:
        cell = hours[day['key']]
        if cell['work']:
            parts.append(f"{day['short']} {cell['start']}–{cell['end']}")
    if not parts:
        return 'Tüm günler kapalı'
    return ' · '.join(parts)


def get_default_work_schedule_plan():
    from core_settings.models import WorkSchedulePlan

    return (
        WorkSchedulePlan.objects.filter(is_default=True, is_active=True).first()
        or WorkSchedulePlan.objects.filter(is_active=True).order_by('sort_order', 'name').first()
    )


def set_default_plan(plan) -> None:
    from core_settings.models import WorkSchedulePlan

    WorkSchedulePlan.objects.exclude(pk=plan.pk).update(is_default=False)
    if not plan.is_default:
        plan.is_default = True
        plan.save(update_fields=['is_default', 'updated_at'])


def is_within_work_hours(dt, plan=None) -> bool:
    """Verilen an mesai içinde mi? (plan yoksa varsayılan plan)."""
    from django.utils import timezone

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    local = timezone.localtime(dt)
    if plan is None:
        plan = get_default_work_schedule_plan()
    if not plan:
        return True
    keys = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    key = keys[local.weekday()]
    hours = normalize_weekly_hours(plan.weekly_hours)
    cell = hours.get(key, {})
    if not cell.get('work'):
        return False
    start = cell.get('start') or ''
    end = cell.get('end') or ''
    if not start or not end:
        return True
    t = local.strftime('%H:%M')
    return start <= t <= end
