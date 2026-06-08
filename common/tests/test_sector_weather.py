"""Sektör kataloğu ve hava durumu servisi testleri."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from common.sector_catalog import (
    SECTOR_PRESETS,
    apply_sector_preset,
    module_sector_labels,
    normalize_sector_slug,
    sector_preset_all_slugs,
)
from common.weather_service import WeatherSnapshot, fetch_weather, geocode_city
from core_settings.models import SiteSettings


class SectorCatalogTests(TestCase):
    def test_all_modules_have_sector_mapping(self):
        from common.module_catalog import MODULES

        core = [
            m['slug'] for m in MODULES
            if m.get('default_enabled') and not m['slug'].startswith('agency_')
        ]
        for slug in core:
            if slug == 'settings':
                continue
            labels = module_sector_labels(slug)
            self.assertTrue(labels, msg=f'{slug} için sektör etiketi yok')

    def test_sector_presets_cover_landing_sectors(self):
        self.assertEqual(len(SECTOR_PRESETS), 6)

    def test_normalize_legacy_kobi(self):
        self.assertEqual(normalize_sector_slug('kobi'), 'montaj_saha')

    def test_apply_sector_stk_minimal(self):
        settings = SiteSettings.objects.create(site_name='Test')
        slugs = apply_sector_preset(settings, 'stk_dernek')
        settings.refresh_from_db()
        self.assertEqual(settings.primary_vertical_slug, 'stk_dernek')
        self.assertIn('contact', slugs)
        self.assertIn('outreach', slugs)
        self.assertNotIn('services', slugs)
        self.assertNotIn('accounting', slugs)

    def test_montaj_preset_is_lean_core(self):
        from common.kobi_lean_preset import lean_kobi_slugs

        slugs = sector_preset_all_slugs('montaj_saha')
        self.assertEqual(set(slugs), set(lean_kobi_slugs()))
        for optional in ('p.accounting.payables', 'p.accounting.multi_cash', 'integration_weather', 'outreach'):
            self.assertNotIn(optional, slugs)


class WeatherServiceTests(TestCase):
    @patch('common.weather_service._http_get_json')
    def test_fetch_weather_parses_open_meteo(self, mock_get):
        mock_get.return_value = {
            'current': {
                'temperature_2m': 18.4,
                'relative_humidity_2m': 55,
                'weather_code': 1,
                'wind_speed_10m': 12.0,
            },
        }
        snap = fetch_weather(41.0, 29.0, 'İstanbul')
        self.assertIsNotNone(snap)
        self.assertEqual(snap.temperature_c, 18.4)
        self.assertEqual(snap.condition, 'Az bulutlu')

    @patch('common.weather_service._http_get_json')
    def test_geocode_city(self, mock_get):
        mock_get.return_value = {
            'results': [{'latitude': 41.01, 'longitude': 28.97, 'name': 'İstanbul'}],
        }
        geo = geocode_city('İstanbul')
        self.assertEqual(geo, (41.01, 28.97, 'İstanbul'))


class WeatherApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        settings = SiteSettings.objects.create(site_name='Test')
        slugs = list(sector_preset_all_slugs('montaj_saha'))
        if 'integration_weather' not in slugs:
            slugs.append('integration_weather')
        settings.enabled_module_slugs = slugs
        settings.save()
        role = __import__('users.models', fromlist=['Role']).Role.objects.filter(slug='admin').first()
        self.user = User.objects.create_user(username='weather', password='x')
        if role:
            self.user.role = role
            self.user.save()
        from common.tests.helpers import ensure_brand_for_user, login_with_brand, set_user_modules

        self.brand = ensure_brand_for_user(self.user, 'Weather Marka')
        set_user_modules(self.user, slugs)
        self._weather_client = __import__('django.test', fromlist=['Client']).Client()
        login_with_brand(self._weather_client, self.user, self.brand)

    @patch('tools.weather_views.weather_for_site')
    def test_weather_api_ok(self, mock_weather):
        mock_weather.return_value = WeatherSnapshot(
            city='İstanbul',
            temperature_c=20.0,
            humidity=50,
            wind_kmh=10.0,
            condition='Açık',
            weather_code=0,
            latitude=41.0,
            longitude=29.0,
        )
        resp = self._weather_client.get('/tools/api/hava-durumu/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['weather']['city'], 'İstanbul')

    def test_weather_api_disabled_module(self):
        slugs = [s for s in self.user.enabled_module_slugs if s != 'integration_weather']
        from common.tests.helpers import set_user_modules

        set_user_modules(self.user, slugs)
        resp = self._weather_client.get('/tools/api/hava-durumu/')
        self.assertEqual(resp.status_code, 403)
