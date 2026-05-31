"""CSV eşleştirme ve içe aktarma sihirbazı testleri."""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from common.csv_mapping import auto_map_headers, apply_column_mapping, normalize_header
from common.csv_import_registry import FINANCE_FIELDS
from common.csv_import_runner import prepare_import_rows, run_import
from core_settings.models import FinanceRecord, ServicePersonnel, PersonnelPayment
from customers.models import Customer

User = get_user_model()


class CsvMappingTests(TestCase):
    def test_normalize_header_turkish(self):
        self.assertEqual(normalize_header('Müşteri Adı'), 'MUSTERI_ADI')

    def test_auto_map_finance_headers(self):
        headers = ['TÜR', 'AÇIKLAMA', 'TUTAR', 'TARİH']
        mapping = auto_map_headers(headers, list(FINANCE_FIELDS))
        self.assertEqual(mapping.get('type'), 'TÜR')
        self.assertEqual(mapping.get('title'), 'AÇIKLAMA')
        self.assertEqual(mapping.get('amount'), 'TUTAR')

    def test_apply_column_mapping(self):
        rows = [{'Ad': 'Test', 'Tutar': '100'}]
        mapped = apply_column_mapping(rows, {'title': 'Ad', 'amount': 'Tutar'})
        self.assertEqual(mapped[0]['title'], 'Test')
        self.assertEqual(mapped[0]['amount'], '100')


class CsvImportWizardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='csvadmin', password='test12345', is_superuser=True)

    def test_finance_import_with_custom_mapping(self):
        rows = [{'desc': 'Kira', 'tip': 'gider', 'price': '500'}]
        result = run_import(
            'finance',
            rows,
            user=self.user,
            mapping={'title': 'desc', 'type': 'tip', 'amount': 'price'},
            headers=['desc', 'tip', 'price'],
        )
        self.assertEqual(result['created'], 1)
        self.assertTrue(FinanceRecord.objects.filter(title='Kira').exists())

    def test_customer_import_creates_and_updates(self):
        Customer.objects.create(name='Ali Veli', phone='05001112233')
        rows = [
            {'name': 'Ali Veli', 'phone': '05009998877', 'region': 'İzmir'},
            {'name': 'Yeni Müşteri', 'phone': '05005556677'},
        ]
        mapped, _ = prepare_import_rows(rows, ['name', 'phone', 'region'], 'customers')
        result = run_import('customers', mapped, user=self.user)
        self.assertEqual(result['updated'], 1)
        self.assertEqual(result['created'], 1)
        self.assertEqual(Customer.objects.get(name='Ali Veli').region, 'İzmir')

    def test_wizard_upload_and_import_flow(self):
        self.client.force_login(self.user)
        csv_text = 'PERSONEL;TÜR;TUTAR\nAhmet Yılmaz;avans;250\n'
        ServicePersonnel.objects.create(name='Ahmet Yılmaz', monthly_salary=10000)
        uploaded = SimpleUploadedFile('payroll.csv', csv_text.encode('utf-8-sig'), content_type='text/csv')

        resp = self.client.post(
            '/muhasebe/veri-alisverisi/csv/',
            {
                'type': 'payroll',
                'step': 'upload',
                'next': '/muhasebe/maas-avans/',
                'file': uploaded,
            },
            format='multipart',
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn('token=', resp['Location'])

        token = resp['Location'].split('token=')[1].split('&')[0]
        resp2 = self.client.post(
            f'/muhasebe/veri-alisverisi/csv/?type=payroll&token={token}',
            {
                'type': 'payroll',
                'step': 'import',
                'token': token,
                'next': '/muhasebe/maas-avans/',
                'map_personnel': 'PERSONEL',
                'map_type': 'TÜR',
                'map_amount': 'TUTAR',
            },
        )
        self.assertEqual(resp2.status_code, 302)
        self.assertEqual(PersonnelPayment.objects.count(), 1)

    def test_customer_export_csv(self):
        Customer.objects.create(name='Export Test', phone='0500', region='Ankara')
        self.client.force_login(self.user)
        resp = self.client.get('/contact/musteriler/export-csv/')
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8-sig')
        self.assertIn('Export Test', body)
