"""Cross-tenant (marka) veri izolasyonu testleri."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from common.brand_scope import SESSION_ACTIVE_BRAND, create_brand_for_user
from core_settings.models import PriorityOption, SiteSettings, StatusOption
from customers.models import Customer, CustomerMedia
from sales_leads.models import SalesLead
from services.models import ServiceRecord
from users.models import Permission, Role

User = get_user_model()


class CustomerIsolationTests(TestCase):
    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(site_name='Isolation Test')
        role = Role.objects.create(slug='crm-user', name='CRM', is_system=False)
        for codename in ('access.contact', 'contact.customers_view', 'contact.customers'):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={'name': codename, 'module': 'Test', 'kind': 'action', 'sort_order': 0},
            )
            role.permissions.add(perm)

        self.owner_a = User.objects.create_user(username='owner_a', password='test1234', role=role)
        self.owner_b = User.objects.create_user(username='owner_b', password='test1234', role=role)
        self.brand_a = create_brand_for_user(self.owner_a, 'Marka A')
        self.brand_b = create_brand_for_user(self.owner_b, 'Marka B')

        self.customer_a = Customer.objects.create(name='Müşteri A', brand=self.brand_a)
        self.customer_b = Customer.objects.create(name='Müşteri B', brand=self.brand_b)

    def _login_brand_a(self):
        self.client.force_login(self.owner_a)
        session = self.client.session
        session[SESSION_ACTIVE_BRAND] = self.brand_a.pk
        session.save()

    def test_customer_api_returns_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.get(f'/contact/musteriler/api/{self.customer_b.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_customer_overview_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.get(f'/contact/musteriler/{self.customer_b.pk}/ozet/')
        self.assertEqual(response.status_code, 404)

    def test_customer_quick_edit_api_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.get(f'/contact/musteriler/{self.customer_b.pk}/hizli-duzenle/')
        self.assertEqual(response.status_code, 404)

    def test_update_customer_products_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.post(
            f'/contact/musteriler/api/{self.customer_b.pk}/urunler/',
            data='{"product_ids": []}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_customer_whatsapp_messages_api_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.get(
            f'/contact/musteriler/api/{self.customer_b.pk}/whatsapp-mesajlar/',
        )
        self.assertEqual(response.status_code, 404)


class ServiceIsolationTests(TestCase):
    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(site_name='Service Isolation')
        role = Role.objects.create(slug='svc-user', name='Service User', is_system=False)
        for codename in ('access.services', 'services.manage', 'services.delete'):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={'name': codename, 'module': 'Test', 'kind': 'action', 'sort_order': 0},
            )
            role.permissions.add(perm)

        self.owner_a = User.objects.create_user(username='svc_owner_a', password='test1234', role=role)
        self.owner_b = User.objects.create_user(username='svc_owner_b', password='test1234', role=role)
        self.brand_a = create_brand_for_user(self.owner_a, 'Servis Marka A')
        self.brand_b = create_brand_for_user(self.owner_b, 'Servis Marka B')

        self.customer_a = Customer.objects.create(name='Müşteri A', brand=self.brand_a)
        self.customer_b = Customer.objects.create(name='Müşteri B', brand=self.brand_b)
        self.status = StatusOption.objects.create(name='Aktif', color='#22c55e', sort_order=1)
        self.priority = PriorityOption.objects.create(name='Normal', color='#64748b')
        self.service_a = ServiceRecord.objects.create(
            customer=self.customer_a,
            brand=self.brand_a,
            status=self.status,
            priority=self.priority,
        )
        self.service_b = ServiceRecord.objects.create(
            customer=self.customer_b,
            brand=self.brand_b,
            status=self.status,
            priority=self.priority,
        )

    def _login_brand_a(self):
        self.client.force_login(self.owner_a)
        session = self.client.session
        session[SESSION_ACTIVE_BRAND] = self.brand_a.pk
        session.save()

    def test_service_edit_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.get(f'/services-dashboard/services/{self.service_b.pk}/edit/')
        self.assertEqual(response.status_code, 404)

    def test_service_customer_summary_api_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.get(
            f'/services-dashboard/services/musteri/{self.customer_b.pk}/ozet/'
        )
        self.assertEqual(response.status_code, 404)

    def test_quick_update_404_for_other_brand_service(self):
        self._login_brand_a()
        self.client.get('/services-dashboard/services/')
        csrf = self.client.cookies['csrftoken'].value
        response = self.client.post(
            '/services-dashboard/services/quick-update/',
            data={
                'service_id': str(self.service_b.pk),
                'field': 'priority',
                'value': str(self.priority.pk),
            },
            HTTP_X_CSRFTOKEN=csrf,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 404)


class SalesIsolationTests(TestCase):
    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(site_name='Sales Isolation')
        role = Role.objects.create(slug='sales-user', name='Sales User', is_system=False)
        for codename in ('access.accounting', 'sales.manage', 'sales.export'):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={'name': codename, 'module': 'Test', 'kind': 'action', 'sort_order': 0},
            )
            role.permissions.add(perm)

        self.owner_a = User.objects.create_user(username='sales_owner_a', password='test1234', role=role)
        self.owner_b = User.objects.create_user(username='sales_owner_b', password='test1234', role=role)
        self.brand_a = create_brand_for_user(self.owner_a, 'Satış Marka A')
        self.brand_b = create_brand_for_user(self.owner_b, 'Satış Marka B')

        self.customer_a = Customer.objects.create(name='Satış Müşteri A', brand=self.brand_a)
        self.customer_b = Customer.objects.create(name='Satış Müşteri B', brand=self.brand_b)
        self.lead_a = SalesLead.objects.create(
            customer=self.customer_a,
            sale_date='2026-01-01',
            project='Proje A',
        )
        self.lead_b = SalesLead.objects.create(
            customer=self.customer_b,
            sale_date='2026-01-02',
            project='Proje B',
        )

    def _login_brand_a(self):
        self.client.force_login(self.owner_a)
        session = self.client.session
        session[SESSION_ACTIVE_BRAND] = self.brand_a.pk
        session.save()

    def test_sales_edit_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.get(f'/muhasebe/satis/{self.lead_b.pk}/duzenle/')
        self.assertEqual(response.status_code, 404)

    def test_sales_export_excludes_other_brand(self):
        self._login_brand_a()
        response = self.client.get('/muhasebe/satis/raporlar/export-csv/')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode('utf-8-sig')
        self.assertIn('Proje A', body)
        self.assertNotIn('Proje B', body)


class FinanceIsolationTests(TestCase):
    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(site_name='Finance Isolation')
        from core_settings.models import FinanceRecord

        role = Role.objects.create(slug='fin-user', name='Finance User', is_system=False)
        for codename in ('access.accounting', 'accounting.finance'):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={'name': codename, 'module': 'Test', 'kind': 'action', 'sort_order': 0},
            )
            role.permissions.add(perm)

        self.owner_a = User.objects.create_user(username='fin_owner_a', password='test1234', role=role)
        self.owner_b = User.objects.create_user(username='fin_owner_b', password='test1234', role=role)
        self.brand_a = create_brand_for_user(self.owner_a, 'Finans Marka A')
        self.brand_b = create_brand_for_user(self.owner_b, 'Finans Marka B')

        from django.utils import timezone

        today = timezone.localdate()
        self.record_a = FinanceRecord.objects.create(
            record_type=FinanceRecord.TYPE_INCOME,
            title='Gelir A',
            amount='100.00',
            record_date=today,
            brand=self.brand_a,
        )
        self.record_b = FinanceRecord.objects.create(
            record_type=FinanceRecord.TYPE_INCOME,
            title='Gelir B',
            amount='200.00',
            record_date=today,
            brand=self.brand_b,
        )

    def _login_brand_a(self):
        self.client.force_login(self.owner_a)
        session = self.client.session
        session[SESSION_ACTIVE_BRAND] = self.brand_a.pk
        session.save()

    def test_finance_delete_does_not_remove_other_brand(self):
        self._login_brand_a()
        response = self.client.post(
            '/muhasebe/gelir-gider/',
            data={'delete_finance': '1', 'id': self.record_b.pk},
        )
        self.assertEqual(response.status_code, 302)
        from core_settings.models import FinanceRecord

        self.assertTrue(FinanceRecord.objects.filter(pk=self.record_b.pk).exists())
        self.assertTrue(FinanceRecord.objects.filter(pk=self.record_a.pk).exists())


class MediaIsolationTests(TestCase):
    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(site_name='Media Isolation')
        role = Role.objects.create(slug='media-user', name='Media User', is_system=False)
        for codename in ('access.contact', 'contact.customers_view', 'contact.customers'):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={'name': codename, 'module': 'Test', 'kind': 'action', 'sort_order': 0},
            )
            role.permissions.add(perm)

        self.owner_a = User.objects.create_user(username='media_owner_a', password='test1234', role=role)
        self.owner_b = User.objects.create_user(username='media_owner_b', password='test1234', role=role)
        self.brand_a = create_brand_for_user(self.owner_a, 'Medya Marka A')
        self.brand_b = create_brand_for_user(self.owner_b, 'Medya Marka B')

        self.customer_a = Customer.objects.create(name='Medya Müşteri A', brand=self.brand_a)
        self.customer_b = Customer.objects.create(name='Medya Müşteri B', brand=self.brand_b)
        self.media_b = CustomerMedia.objects.create(
            customer=self.customer_b,
            scope=CustomerMedia.SCOPE_CUSTOMER,
            title='Gizli dosya',
        )

    def _login_brand_a(self):
        self.client.force_login(self.owner_a)
        session = self.client.session
        session[SESSION_ACTIVE_BRAND] = self.brand_a.pk
        session.save()

    def test_customer_media_list_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.get(f'/contact/musteriler/{self.customer_b.pk}/medya/')
        self.assertEqual(response.status_code, 404)

    def test_customer_media_delete_404_for_other_brand(self):
        self._login_brand_a()
        response = self.client.post(f'/contact/musteriler/medya/{self.media_b.pk}/sil/')
        self.assertEqual(response.status_code, 404)
