from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core_settings.backup import factory_reset_database
from core_settings.models import SiteSettings, StatusOption
from common.tests.helpers import default_test_brand
from customers.models import Customer
from users.models import Permission, Role

User = get_user_model()


def _superuser_client(password='test-pass-123'):
    role = Role.objects.create(slug='admin-test', name='Admin Test', is_system=False)
    perm, _ = Permission.objects.get_or_create(
        codename='access.settings',
        defaults={'name': 'Settings', 'module': 'Test', 'kind': 'access', 'sort_order': 0},
    )
    role.permissions.add(perm)
    user = User.objects.create_superuser(
        username='super_reset',
        password=password,
        email='super@test.local',
        role=role,
    )
    client = Client()
    client.force_login(user)
    return client, user


@override_settings(DEBUG=True)
class FactoryResetDatabaseTests(TestCase):
    def test_factory_reset_recreates_admin_and_defaults(self):
        Customer.objects.create(name='Silinecek müşteri', brand=default_test_brand())
        ok, _msg = factory_reset_database(backup_before=False)
        self.assertTrue(ok)
        self.assertEqual(Customer.objects.count(), 0)
        admin = User.objects.get(username='admin')
        self.assertTrue(admin.is_superuser)
        self.assertTrue(check_password('admin', admin.password))
        self.assertGreaterEqual(StatusOption.objects.count(), 1)
        self.assertTrue(SiteSettings.objects.filter(site_name='Kobi Hub').exists())

    def test_factory_reset_requires_superuser_on_page(self):
        role = Role.objects.create(slug='plain', name='Plain', is_system=False)
        perm, _ = Permission.objects.get_or_create(
            codename='access.settings',
            defaults={'name': 'Settings', 'module': 'Test', 'kind': 'access', 'sort_order': 0},
        )
        role.permissions.add(perm)
        user = User.objects.create_user(
            username='plain_user',
            password='test-pass-123',
            role=role,
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse('admin_system_backup'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

    def test_factory_reset_post_validates_confirmation(self):
        client, user = _superuser_client(password='secret123')
        url = reverse('admin_system_backup')
        response = client.post(url, {
            'factory_reset_database': '1',
            'acknowledge_data_loss': 'on',
            'confirm_phrase': 'YANLIS',
            'password': 'secret123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.filter(username='super_reset').count(), 1)

    @patch('core_settings.system_backup_handlers.import_sqlite_file', return_value=(True, 'SQLite yüklendi.'))
    def test_import_sqlite_success_logs_out(self, _mock_import):
        client, _user = _superuser_client(password='secret123')
        url = reverse('admin_system_backup')
        uploaded = SimpleUploadedFile('test.sqlite3', b'SQLite format 3\x00' + b'\x00' * 200)
        response = client.post(url, {'import_sqlite': '1', 'sqlite_file': uploaded})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))

    def test_factory_reset_post_success_logs_out(self):
        client, user = _superuser_client(password='secret123')
        Customer.objects.create(name='Kayıt', brand=default_test_brand())
        url = reverse('admin_system_backup')
        response = client.post(url, {
            'factory_reset_database': '1',
            'acknowledge_data_loss': 'on',
            'confirm_phrase': 'SIFIRLA',
            'password': 'secret123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))
        self.assertFalse(User.objects.filter(username='super_reset').exists())
        admin = User.objects.get(username='admin')
        self.assertTrue(check_password('admin', admin.password))
