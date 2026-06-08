from django.contrib.auth import get_user_model
from django.test import TestCase

from common.tests.helpers import default_test_brand
from tools.models import FirmTag, MapsScrapedFirm

User = get_user_model()


class FirmsExportCsvTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='firmexport', password='test12345', is_superuser=True)
        self.brand = default_test_brand()

    def test_firms_export_csv(self):
        tag = FirmTag.objects.create(name='VIP', color='#6366f1', brand=self.brand)
        firm = MapsScrapedFirm.objects.create(
            name='Export Firma',
            phone='05321234567',
            phone_normalized='905321234567',
            address='Test Sokak',
            region='Kadıköy',
            website='https://example.com',
            brand=self.brand,
        )
        firm.tags.add(tag)

        self.client.force_login(self.user)
        resp = self.client.get('/contact/firmalar/export-csv/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')

        body = resp.content.decode('utf-8-sig')
        self.assertIn('Firma adı', body)
        self.assertIn('Export Firma', body)
        self.assertIn('Kadıköy', body)
        self.assertIn('VIP', body)

    def test_firms_export_csv_respects_kind_filter(self):
        MapsScrapedFirm.objects.create(name='Kazınan', firm_kind=MapsScrapedFirm.KIND_SCRAPED, brand=self.brand)
        MapsScrapedFirm.objects.create(name='Bayi', firm_kind=MapsScrapedFirm.KIND_DEALER, brand=self.brand)

        self.client.force_login(self.user)
        resp = self.client.get('/contact/firmalar/export-csv/?kind=dealer')
        body = resp.content.decode('utf-8-sig')
        self.assertIn('Bayi', body)
        self.assertNotIn('Kazınan', body)
