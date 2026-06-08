"""CSV eşleştirme ve içe aktarma sihirbazı testleri."""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from common.csv_mapping import (
    apply_column_mapping,
    auto_map_headers,
    boost_import_mapping,
    mapping_headers,
    normalize_header,
)
from sales_leads.csv_interim import (
    detect_interim_headers,
    has_interim_columns,
    is_interim_amount_header,
    parse_interim_payments_from_row,
)
from common.csv_import_registry import CUSTOMER_FIELDS, FINANCE_FIELDS
from common.csv_import_diagnostics import resolve_import_mapping
from common.csv_import_runner import prepare_import_rows, run_import
from sales_leads.models import SalesLead
from core_settings.models import FinanceRecord, ProductOption, ServicePersonnel, PersonnelPayment
from customers.models import Customer

User = get_user_model()


class CsvMappingTests(TestCase):
    def test_normalize_header_turkish(self):
        self.assertEqual(normalize_header('Müşteri Adı'), 'MUSTERI_ADI')

    def test_auto_map_finance_headers(self):
        headers = ['Tür', 'Açıklama', 'Tutar', 'Tarih']
        mapping = auto_map_headers(headers, list(FINANCE_FIELDS))
        self.assertEqual(mapping.get('type'), 'Tür')
        self.assertEqual(mapping.get('title'), 'Açıklama')
        self.assertEqual(mapping.get('amount'), 'Tutar')

    def test_boost_mapping_finds_product_column(self):
        headers = ['Ad Soyad', 'Ürünler', 'Tel']
        mapping = boost_import_mapping('customers', headers, {'name': 'Ad Soyad'})
        self.assertEqual(mapping.get('products'), 'Ürünler')

    def test_auto_map_customer_products_column(self):
        headers = ['Müşteri Adı', 'Satın Aldığı Ürünler', 'Telefon']
        mapping = auto_map_headers(headers, list(CUSTOMER_FIELDS))
        self.assertEqual(mapping.get('name'), 'Müşteri Adı')
        self.assertEqual(mapping.get('products'), 'Satın Aldığı Ürünler')
        self.assertEqual(mapping.get('phone'), 'Telefon')

    def test_interim_header_detection(self):
        headers = ['Müşteri Adı', 'Ara ödeme tarihi', 'Ara ödeme', 'Ara ödeme 2']
        self.assertTrue(has_interim_columns(headers))
        self.assertTrue(is_interim_amount_header('Ara ödeme'))
        detected = detect_interim_headers(headers)
        self.assertEqual(len(detected), 3)

    def test_parse_interim_payments_from_row(self):
        from datetime import date

        raw = {
            'Ara ödeme tarihi': '01.03.2025',
            'Ara ödeme': '1500',
            'Ara ödeme tarihi 2': '15.04.2025',
            'Ara ödeme 2': '500',
        }
        payments = parse_interim_payments_from_row(raw, default_date=date(2025, 1, 1))
        self.assertEqual(len(payments), 2)
        self.assertEqual(payments[0][0], 1500)
        self.assertEqual(payments[1][0], 500)

    def test_apply_column_mapping(self):
        rows = [{'Ad': 'Test', 'Tutar': '100'}]
        mapped = apply_column_mapping(rows, {'title': 'Ad', 'amount': 'Tutar'})
        self.assertEqual(mapped[0]['title'], 'Test')
        self.assertEqual(mapped[0]['amount'], '100')

    def test_apply_column_mapping_multiple_headers(self):
        rows = [{'Ad': 'Ali', 'Soyad': 'Yılmaz', 'Ürün1': 'Klima', 'Ürün2': 'Panel'}]
        mapped = apply_column_mapping(
            rows,
            {'name': 'Ad|Soyad', 'products': ['Ürün1', 'Ürün2']},
        )
        self.assertEqual(mapped[0]['name'], 'Ali Yılmaz')
        self.assertEqual(mapped[0]['products'], 'Klima | Panel')
        self.assertEqual(mapping_headers('Ad|Soyad'), ['Ad', 'Soyad'])

    def test_manual_skip_without_auto_mapping(self):
        headers = ['Müşteri Adı', 'Yanlış Ürün Sütunu', 'Telefon']
        user_map = {'name': 'Müşteri Adı', 'products': '', 'phone': 'Telefon'}
        final, sources, _ = resolve_import_mapping(
            headers,
            list(CUSTOMER_FIELDS),
            'customers',
            user_mapping=user_map,
            use_auto_mapping=False,
        )
        self.assertIsNone(final.get('products'))
        self.assertEqual(sources.get('products'), 'skip')
        self.assertEqual(final.get('name'), 'Müşteri Adı')


class CsvImportWizardTests(TestCase):
    def setUp(self):
        from common.brand_scope import create_brand_for_user
        from core_settings.models import SiteSettings
        from users.models import Permission, Role

        from common.module_runtime import get_enabled_module_slugs

        settings = SiteSettings.objects.create(site_name='CSV Wizard')
        enabled = list(get_enabled_module_slugs())
        if 'integration_csv_exchange' not in enabled:
            settings.enabled_module_slugs = enabled + ['integration_csv_exchange']
            settings.save()
        role = Role.objects.create(slug='csv-wizard', name='CSV Wizard', is_system=False)
        for codename in (
            'access.contact',
            'contact.customers',
            'contact.payroll',
            'accounting.finance',
            'sales.manage',
            'access.tools',
        ):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={'name': codename, 'module': 'Test', 'kind': 'action', 'sort_order': 0},
            )
            role.permissions.add(perm)
        self.user = User.objects.create_user(username='csvadmin', password='test12345', role=role)
        self.brand = create_brand_for_user(self.user, 'CSV Marka')
        from common.kobi_lean_preset import lean_kobi_slugs
        from common.tests.helpers import set_user_modules

        slugs = lean_kobi_slugs()
        if 'integration_csv_exchange' not in slugs:
            slugs.append('integration_csv_exchange')
        set_user_modules(self.user, slugs)

    def _login(self):
        from common.brand_scope import SESSION_ACTIVE_BRAND

        self.client.force_login(self.user)
        session = self.client.session
        session[SESSION_ACTIVE_BRAND] = self.brand.pk
        session.save()

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

    def test_resolve_product_options_with_duplicate_names(self):
        ProductOption.objects.create(name='Klima')
        ProductOption.objects.create(name='klima')
        from common.csv_products import resolve_product_options

        options = resolve_product_options(['Klima', 'Panel'])
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].pk, ProductOption.objects.filter(name__iexact='klima').order_by('pk').first().pk)

    def test_customer_import_with_products(self):
        rows = [
            {
                'name': 'Ürünlü Müşteri',
                'phone': '05001112222',
                'products': 'Klima | Panel',
            },
        ]
        mapped, *_ = prepare_import_rows(
            rows, list(rows[0].keys()), 'customers', user=self.user,
        )
        result = run_import('customers', mapped, user=self.user)
        self.assertEqual(result['created'], 1)
        self.assertEqual(result['products_linked'], 1)
        customer = Customer.objects.get(name='Ürünlü Müşteri')
        names = set(customer.products.values_list('name', flat=True))
        self.assertEqual(names, {'Klima', 'Panel'})

    def test_customer_import_creates_sales_when_sale_columns_mapped(self):
        rows = [
            {
                'name': 'Satışlı Müşteri',
                'phone': '05001234567',
                'project': 'Villa projesi',
                'total': '100000',
                'down_payment': '20000',
            },
        ]
        mapping = {
            'name': 'name',
            'phone': 'phone',
            'project': 'project',
            'total': 'total',
            'down_payment': 'down_payment',
        }
        result = run_import(
            'customers',
            rows,
            user=self.user,
            mapping=mapping,
            headers=list(rows[0].keys()),
        )
        self.assertEqual(result['created'], 1)
        self.assertEqual(result.get('sales_created'), 1)
        self.assertTrue(Customer.objects.filter(name='Satışlı Müşteri').exists())
        self.assertEqual(SalesLead.objects.filter(customer__name='Satışlı Müşteri').count(), 1)

    def test_customer_import_creates_and_updates(self):
        Customer.objects.create(name='Ali Veli', phone='05001112233', brand=self.brand)
        rows = [
            {'name': 'Ali Veli', 'phone': '05009998877', 'region': 'İzmir'},
            {'name': 'Yeni Müşteri', 'phone': '05005556677'},
        ]
        mapped, *_ = prepare_import_rows(
            rows, ['name', 'phone', 'region'], 'customers', user=self.user,
        )
        result = run_import('customers', mapped, user=self.user)
        self.assertEqual(result['updated'], 1)
        self.assertEqual(result['created'], 1)
        self.assertEqual(Customer.objects.get(name='Ali Veli').region, 'İzmir')

    def test_wizard_upload_and_import_flow(self):
        self._login()
        csv_text = 'Personel;Tür;Tutar\nAhmet Yılmaz;avans;250\n'
        ServicePersonnel.objects.create(
            name='Ahmet Yılmaz',
            monthly_salary=10000,
            brand=self.brand,
        )
        uploaded = SimpleUploadedFile('payroll.csv', csv_text.encode('utf-8-sig'), content_type='text/csv')

        resp = self.client.post(
            '/tools/csv/yukle/',
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
            f'/tools/csv/yukle/?type=payroll&token={token}',
            {
                'type': 'payroll',
                'step': 'import',
                'token': token,
                'next': '/muhasebe/maas-avans/',
                'map_personnel': 'Personel',
                'map_type': 'Tür',
                'map_amount': 'Tutar',
            },
        )
        self.assertEqual(resp2.status_code, 302)
        self.assertEqual(PersonnelPayment.objects.count(), 1)

    def test_customer_export_csv(self):
        c = Customer.objects.create(
            name='Export Test',
            phone='0500',
            region='Ankara',
            brand=self.brand,
        )
        ProductOption.objects.create(name='Test Ürün')
        c.products.add(ProductOption.objects.get(name='Test Ürün'))
        self._login()
        resp = self.client.get('/contact/musteriler/export-csv/')
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8-sig')
        self.assertIn('Export Test', body)
        self.assertIn('Müşteri Adı', body)
        self.assertIn('Satın Aldığı Ürünler', body)
        self.assertIn('Test Ürün', body)
