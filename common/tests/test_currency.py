from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from common.currency import currency_info, format_money, strip_currency_symbols
from core_settings.models import SiteSettings


class CurrencyFormatTests(SimpleTestCase):
    def test_try_after_symbol(self):
        text = format_money(Decimal('1234.5'), currency=currency_info('TRY'))
        self.assertTrue(text.endswith('₺'))
        self.assertIn('1.234,50', text)

    def test_usd_before_symbol(self):
        text = format_money(Decimal('100'), currency=currency_info('USD'))
        self.assertTrue(text.startswith('$'))

    def test_strip_symbols(self):
        self.assertEqual(strip_currency_symbols('1.500,50 ₺'), '1.500,50')


class CurrencySettingsTests(TestCase):
    def test_site_settings_currency_symbol(self):
        settings = SiteSettings.objects.create(site_name='T', currency_code='EUR')
        self.assertEqual(settings.currency_symbol, '€')
