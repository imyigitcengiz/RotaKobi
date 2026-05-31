"""Hava durumu — Open-Meteo (ücretsiz, API anahtarı gerektirmez)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date

from django.core.cache import cache

DEFAULT_CITY = 'İstanbul'
DEFAULT_LAT = 41.0082
DEFAULT_LON = 28.9784
CACHE_TTL = 600  # 10 dk

# WMO weather code → Türkçe kısa etiket
WMO_LABELS: dict[int, str] = {
    0: 'Açık',
    1: 'Az bulutlu',
    2: 'Parçalı bulutlu',
    3: 'Kapalı',
    45: 'Sis',
    48: 'Sis',
    51: 'Çisenti',
    53: 'Çisenti',
    55: 'Çisenti',
    61: 'Yağmur',
    63: 'Yağmur',
    65: 'Şiddetli yağmur',
    71: 'Kar',
    73: 'Kar',
    75: 'Yoğun kar',
    80: 'Sağanak',
    81: 'Sağanak',
    82: 'Şiddetli sağanak',
    95: 'Fırtına',
    96: 'Dolu',
    99: 'Dolu',
}


@dataclass
class WeatherSnapshot:
    city: str
    temperature_c: float | None
    humidity: int | None
    wind_kmh: float | None
    condition: str
    weather_code: int | None
    latitude: float
    longitude: float

    def to_dict(self) -> dict:
        return {
            'city': self.city,
            'temperature_c': self.temperature_c,
            'humidity': self.humidity,
            'wind_kmh': self.wind_kmh,
            'condition': self.condition,
            'weather_code': self.weather_code,
            'latitude': self.latitude,
            'longitude': self.longitude,
        }


def _http_get_json(url: str, timeout: float = 8.0) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'CoolOPS/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return None


def geocode_city(city: str) -> tuple[float, float, str] | None:
    name = (city or '').strip()
    if not name:
        return None
    q = urllib.parse.quote(name)
    url = (
        f'https://geocoding-api.open-meteo.com/v1/search?name={q}'
        f'&count=1&language=tr&format=json'
    )
    data = _http_get_json(url)
    if not data or not data.get('results'):
        return None
    row = data['results'][0]
    return float(row['latitude']), float(row['longitude']), row.get('name') or name


def resolve_coordinates(settings) -> tuple[float, float, str]:
    lat = getattr(settings, 'weather_latitude', None)
    lon = getattr(settings, 'weather_longitude', None)
    city = (getattr(settings, 'weather_city', None) or '').strip() or DEFAULT_CITY

    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon), city
        except (TypeError, ValueError):
            pass

    geo = geocode_city(city)
    if geo:
        return geo[0], geo[1], geo[2]
    return DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY


def fetch_weather(lat: float, lon: float, city: str) -> WeatherSnapshot | None:
    cache_key = f'weather:{lat:.3f}:{lon:.3f}'
    cached = cache.get(cache_key)
    if cached:
        return WeatherSnapshot(**cached)

    url = (
        f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}'
        '&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m'
        '&timezone=Europe%2FIstanbul&forecast_days=1'
    )
    data = _http_get_json(url)
    if not data or 'current' not in data:
        return None

    cur = data['current']
    code = cur.get('weather_code')
    condition = WMO_LABELS.get(int(code), 'Hava') if code is not None else 'Hava'
    snap = WeatherSnapshot(
        city=city,
        temperature_c=cur.get('temperature_2m'),
        humidity=cur.get('relative_humidity_2m'),
        wind_kmh=cur.get('wind_speed_10m'),
        condition=condition,
        weather_code=int(code) if code is not None else None,
        latitude=lat,
        longitude=lon,
    )
    cache.set(cache_key, snap.to_dict(), CACHE_TTL)
    return snap


def weather_for_site(settings) -> WeatherSnapshot | None:
    lat, lon, city = resolve_coordinates(settings)
    return fetch_weather(lat, lon, city)


def refresh_site_coordinates(settings) -> None:
    """Şehir adından koordinat çöz ve kaydet."""
    city = (getattr(settings, 'weather_city', None) or '').strip() or DEFAULT_CITY
    geo = geocode_city(city)
    if not geo:
        return
    settings.weather_latitude = geo[0]
    settings.weather_longitude = geo[1]
    settings.weather_city = geo[2]
    settings.save(update_fields=['weather_latitude', 'weather_longitude', 'weather_city'])


@dataclass
class DailyWeather:
    date_iso: str
    temp_min: float | None
    temp_max: float | None
    condition: str
    weather_code: int | None
    precip_probability: int | None

    def to_dict(self) -> dict:
        return {
            'date': self.date_iso,
            'temp_min': self.temp_min,
            'temp_max': self.temp_max,
            'condition': self.condition,
            'weather_code': self.weather_code,
            'precip_probability': self.precip_probability,
        }


def wmo_label(code: int | None) -> str:
    if code is None:
        return 'Hava'
    return WMO_LABELS.get(int(code), 'Hava')


def fetch_daily_forecast(
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> dict[str, DailyWeather]:
    """Tarih aralığı için günlük hava özeti (Open-Meteo daily)."""
    from datetime import date as date_cls

    if isinstance(start, str):
        start = date_cls.fromisoformat(start)
    if isinstance(end, str):
        end = date_cls.fromisoformat(end)

    cache_key = f'weather_daily:{lat:.3f}:{lon:.3f}:{start}:{end}'
    cached = cache.get(cache_key)
    if cached:
        return {k: DailyWeather(**v) for k, v in cached.items()}

    url = (
        f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}'
        '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max'
        f'&timezone=Europe%2FIstanbul&start_date={start.isoformat()}&end_date={end.isoformat()}'
    )
    data = _http_get_json(url)
    out: dict[str, DailyWeather] = {}
    if not data or 'daily' not in data:
        return out

    daily = data['daily']
    dates = daily.get('time') or []
    codes = daily.get('weather_code') or []
    tmax = daily.get('temperature_2m_max') or []
    tmin = daily.get('temperature_2m_min') or []
    precip = daily.get('precipitation_probability_max') or []

    for i, day_str in enumerate(dates):
        code = codes[i] if i < len(codes) else None
        out[day_str] = DailyWeather(
            date_iso=day_str,
            temp_min=tmin[i] if i < len(tmin) else None,
            temp_max=tmax[i] if i < len(tmax) else None,
            condition=wmo_label(int(code) if code is not None else None),
            weather_code=int(code) if code is not None else None,
            precip_probability=int(precip[i]) if i < len(precip) and precip[i] is not None else None,
        )

    cache.set(cache_key, {k: v.to_dict() for k, v in out.items()}, CACHE_TTL)
    return out


def daily_forecast_for_site(settings, start: date, end: date) -> dict[str, DailyWeather]:
    lat, lon, _city = resolve_coordinates(settings)
    return fetch_daily_forecast(lat, lon, start, end)
