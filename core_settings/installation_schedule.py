"""Montaj programı — günlük takvim, ekip, hava durumu ve hafta sonu kuralları."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from django.utils import timezone

from common.weather_service import (
    customer_weather_query,
    daily_forecast_for_site,
    resolve_customer_coordinates,
)
from core_settings.models import InstallationScheduleEntry, SiteSettings

TR_MONTHS = (
    '', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
    'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
)
TR_WEEKDAYS = ('Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz')


def _site_settings() -> SiteSettings | None:
    return SiteSettings.objects.first()


def _default_work_schedule_label() -> str:
    from core_settings.work_schedule import get_default_work_schedule_plan

    plan = get_default_work_schedule_plan()
    if not plan:
        return 'Tanımlı değil'
    return f'{plan.name} ({plan.summary()})'


def default_work_type_for_date(d: date, settings: SiteSettings) -> str:
    if d.weekday() == 5:
        return settings.schedule_saturday_default_work or InstallationScheduleEntry.TYPE_INSTALLATION
    return InstallationScheduleEntry.TYPE_INSTALLATION


def is_day_holiday(d: date, settings: SiteSettings) -> bool:
    wd = d.weekday()
    if wd == 5 and not settings.schedule_saturday_working:
        return True
    if wd == 6 and not settings.schedule_sunday_working:
        return True
    return False


def _weeks_in_month(year: int, month: int) -> list[list[date]]:
    return calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)


def _month_bounds(weeks: list[list[date]]) -> tuple[date, date]:
    flat = [d for week in weeks for d in week]
    return flat[0], flat[-1]


def _entries_for_range(start: date, end: date) -> dict[str, list]:
    rows = (
        InstallationScheduleEntry.objects.filter(
            scheduled_date__gte=start,
            scheduled_date__lte=end,
        )
        .select_related('customer', 'team', 'sales_lead', 'operational_project')
        .order_by('scheduled_date', 'sort_order', 'pk')
    )
    grouped: dict[str, list] = {}
    for entry in rows:
        key = entry.scheduled_date.isoformat()
        grouped.setdefault(key, []).append(entry)
    return grouped


def _serialize_entry(entry: InstallationScheduleEntry, *, entry_weather=None) -> dict:
    weather_dict = entry_weather.to_dict() if entry_weather else None
    loc_label = customer_weather_query(entry.customer) or ''
    return {
        'id': entry.id,
        'customer_name': entry.customer.name,
        'customer_phone': entry.customer.phone or '',
        'customer_address': entry.customer.address or '',
        'customer_region': entry.customer.region or '',
        'weather_location': loc_label,
        'weather': weather_dict,
        'team_name': entry.team.name if entry.team else '',
        'work_type': entry.work_type,
        'work_type_label': entry.get_work_type_display(),
        'notes': entry.notes or '',
        'sales_lead_label': (
            f'{entry.sales_lead.customer.name} — {entry.sales_lead.sale_date:%d.%m.%Y}'
            if entry.sales_lead_id and entry.sales_lead
            else ''
        ),
    }


def build_day_cell(
    d: date,
    *,
    year: int,
    month: int,
    settings: SiteSettings,
    entries_by_date: dict[str, list],
    weather_by_date: dict,
    entry_weather_map: dict,
    today: date,
) -> dict:
    iso = d.isoformat()
    weather = weather_by_date.get(iso)
    weather_dict = weather.to_dict() if weather else None
    raw_entries = entries_by_date.get(iso, [])
    entries = [
        _serialize_entry(e, entry_weather=entry_weather_map.get((e.pk, iso)))
        for e in raw_entries
    ]
    holiday = is_day_holiday(d, settings)
    return {
        'date': d,
        'date_iso': iso,
        'day': d.day,
        'weekday': d.weekday(),
        'weekday_label': TR_WEEKDAYS[d.weekday()],
        'in_month': d.month == month,
        'is_today': d == today,
        'is_holiday': holiday,
        'is_weekend': d.weekday() >= 5,
        'weather': weather_dict,
        'entries': entries,
        'entry_count': len(entries),
        'default_work_type': default_work_type_for_date(d, settings),
    }


def build_schedule_calendar(
    *,
    year: int | None = None,
    month: int | None = None,
    view: str = 'month',
    week_index: int | None = None,
) -> dict:
    today = timezone.localdate()
    year = year or today.year
    month = month or today.month
    settings = _site_settings()
    if not settings:
        settings = SiteSettings(site_name='CoolOPS')

    weeks_raw = _weeks_in_month(year, month)
    range_start, range_end = _month_bounds(weeks_raw)
    entries_by_date = _entries_for_range(range_start, range_end)
    weather_by_date = daily_forecast_for_site(settings, range_start, range_end)

    entry_weather_map: dict[tuple[int, str], object] = {}
    coord_cache: dict[str, tuple[float, float]] = {}
    for day_entries in entries_by_date.values():
        for entry in day_entries:
            key = (entry.pk, entry.scheduled_date.isoformat())
            if key in entry_weather_map:
                continue
            loc_key = customer_weather_query(entry.customer) or '__site_default__'
            if loc_key not in coord_cache:
                lat, lon, _ = resolve_customer_coordinates(entry.customer, settings)
                coord_cache[loc_key] = (lat, lon)
            lat, lon = coord_cache[loc_key]
            from common.weather_service import fetch_daily_forecast

            day_iso = entry.scheduled_date.isoformat()
            forecasts = fetch_daily_forecast(lat, lon, entry.scheduled_date, entry.scheduled_date)
            entry_weather_map[key] = forecasts.get(day_iso)

    weeks = []
    current_week_idx = None
    for wi, week_dates in enumerate(weeks_raw):
        if today in week_dates:
            current_week_idx = wi
        days = [
            build_day_cell(
                d,
                year=year,
                month=month,
                settings=settings,
                entries_by_date=entries_by_date,
                weather_by_date=weather_by_date,
                entry_weather_map=entry_weather_map,
                today=today,
            )
            for d in week_dates
        ]
        weeks.append({'index': wi, 'days': days, 'is_current_week': today in week_dates})

    if week_index is None:
        week_index = current_week_idx if current_week_idx is not None else 0

    visible_weeks = weeks
    if view == 'week' and 0 <= week_index < len(weeks):
        visible_weeks = [weeks[week_index]]

    prev_month = date(year, month, 1) - timedelta(days=1)
    next_month = date(year, month, 28) + timedelta(days=4)
    next_month = date(next_month.year, next_month.month, 1)

    return {
        'calendar_year': year,
        'calendar_month': month,
        'calendar_month_label': f'{TR_MONTHS[month]} {year}',
        'calendar_weeks': weeks,
        'visible_weeks': visible_weeks,
        'calendar_view': view,
        'calendar_week_index': week_index,
        'current_week_index': current_week_idx,
        'weekday_headers': TR_WEEKDAYS,
        'prev_year': prev_month.year,
        'prev_month': prev_month.month,
        'next_year': next_month.year,
        'next_month': next_month.month,
        'today_iso': today.isoformat(),
        'schedule_settings': {
            'saturday_working': settings.schedule_saturday_working,
            'sunday_working': settings.schedule_sunday_working,
            'saturday_default_work': settings.schedule_saturday_default_work,
            'saturday_default_work_label': settings.get_schedule_saturday_default_work_display(),
            'weather_city': (settings.weather_city or '').strip() or 'Ayarlanmadı',
            'weather_city_value': (settings.weather_city or '').strip(),
            'weather_city_configured': bool((settings.weather_city or '').strip()),
            'work_schedule_plan': _default_work_schedule_label(),
        },
        'work_type_choices': InstallationScheduleEntry.TYPE_CHOICES,
    }


def create_schedule_entry(
    *,
    scheduled_date: date,
    customer_id: int,
    team_id=None,
    sales_lead_id=None,
    operational_project_id=None,
    work_type: str = '',
    notes: str = '',
) -> InstallationScheduleEntry:
    settings = _site_settings()
    if not work_type and settings:
        work_type = default_work_type_for_date(scheduled_date, settings)
    if not work_type:
        work_type = InstallationScheduleEntry.TYPE_INSTALLATION

    return InstallationScheduleEntry.objects.create(
        scheduled_date=scheduled_date,
        customer_id=customer_id,
        team_id=team_id or None,
        sales_lead_id=sales_lead_id or None,
        operational_project_id=operational_project_id or None,
        work_type=work_type,
        notes=(notes or '').strip(),
    )


def update_schedule_entry(entry: InstallationScheduleEntry, **fields) -> InstallationScheduleEntry:
    allowed = {
        'scheduled_date', 'customer_id', 'team_id', 'sales_lead_id',
        'operational_project_id', 'work_type', 'notes', 'sort_order',
    }
    update_fields = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key.endswith('_id') and value == '':
            value = None
        setattr(entry, key, value)
        update_fields.append(key)
    if update_fields:
        entry.save(update_fields=update_fields + ['updated_at'])
    return entry


def schedule_redirect_url(request) -> str:
    """POST sonrası aynı ay/hafta görünümüne dön."""
    from urllib.parse import urlencode

    today = timezone.localdate()

    def _int(name: str, default: int) -> int:
        raw = request.POST.get(name) or request.GET.get(name)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    year = _int('calendar_year', today.year)
    month = _int('calendar_month', today.month)
    view = request.POST.get('calendar_view') or request.GET.get('view', 'month')
    if view not in ('month', 'week'):
        view = 'month'

    params: dict[str, str | int] = {'year': year, 'month': month, 'view': view}
    week = request.POST.get('calendar_week') or request.GET.get('week')
    if view == 'week' and week is not None and str(week).isdigit():
        params['week'] = week

    day = (request.POST.get('scheduled_date') or request.GET.get('day') or '').strip()
    if day:
        params['day'] = day

    from django.urls import reverse
    return f"{reverse('accounting_projects')}?{urlencode(params)}"


def schedule_form_context(request) -> dict:
    """Şablondaki gizli takvim alanları."""
    today = timezone.localdate()

    def _int(name: str, default: int) -> int:
        raw = request.GET.get(name)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    return {
        'form_calendar_year': _int('year', today.year),
        'form_calendar_month': _int('month', today.month),
        'form_calendar_view': request.GET.get('view', 'month'),
        'form_calendar_week': request.GET.get('week', ''),
    }


def save_schedule_settings(
    settings: SiteSettings,
    *,
    saturday_working: bool,
    sunday_working: bool,
    saturday_default_work: str,
    weather_city: str | None = None,
) -> None:
    settings.schedule_saturday_working = saturday_working
    settings.schedule_sunday_working = sunday_working
    if saturday_default_work in (
        InstallationScheduleEntry.TYPE_INSTALLATION,
        InstallationScheduleEntry.TYPE_SERVICE,
    ):
        settings.schedule_saturday_default_work = saturday_default_work
    update_fields = [
        'schedule_saturday_working',
        'schedule_sunday_working',
        'schedule_saturday_default_work',
    ]
    if weather_city is not None:
        settings.weather_city = weather_city.strip()
        update_fields.append('weather_city')
    settings.save(update_fields=update_fields)
    if weather_city is not None:
        from common.weather_service import refresh_site_coordinates

        refresh_site_coordinates(settings)
