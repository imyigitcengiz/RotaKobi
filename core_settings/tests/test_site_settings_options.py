from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from common.kobi_lean_preset import lean_kobi_slugs
from common.tests.helpers import ensure_brand_for_user, login_with_brand, set_user_modules
from core_settings.models import ServiceTypeOption, StatusOption
from core_settings.work_schedule import validate_weekly_hours_from_request
from users.models import Permission, Role

User = get_user_model()


def _settings_test_client():
    role = Role.objects.create(slug='settings-tester', name='Settings Tester', is_system=False)
    perm, _ = Permission.objects.get_or_create(
        codename='access.settings',
        defaults={'name': 'Settings', 'module': 'Test', 'kind': 'access', 'sort_order': 0},
    )
    role.permissions.add(perm)
    user = User.objects.create_user(
        username='settings_admin',
        password='test-pass-123',
        role=role,
    )
    brand = ensure_brand_for_user(user, 'Settings Test Marka')
    set_user_modules(user, lean_kobi_slugs())
    client = Client()
    login_with_brand(client, user, brand)
    return client


class WorkScheduleValidationTests(TestCase):
    def test_work_day_requires_times(self):
        weekly, errors = validate_weekly_hours_from_request({
            'day_monday_work': 'on',
            'day_monday_start': '',
            'day_monday_end': '',
        })
        self.assertIsNone(weekly)
        self.assertTrue(any('Pazartesi' in e for e in errors))

    def test_end_before_start_rejected(self):
        weekly, errors = validate_weekly_hours_from_request({
            'day_tuesday_work': 'on',
            'day_tuesday_start': '18:00',
            'day_tuesday_end': '09:00',
        })
        self.assertIsNone(weekly)
        self.assertTrue(any('Salı' in e for e in errors))

    def test_valid_week_saved(self):
        weekly, errors = validate_weekly_hours_from_request({
            'day_wednesday_work': 'on',
            'day_wednesday_start': '09:00',
            'day_wednesday_end': '18:00',
        })
        self.assertFalse(errors)
        self.assertTrue(weekly['wednesday']['work'])


class SiteSettingsOptionsTests(TestCase):
    def setUp(self):
        self.client = _settings_test_client()

    def test_duplicate_service_type_shows_clear_error(self):
        ServiceTypeOption.objects.create(name='Montaj')
        url = reverse('settings_service_types')
        response = self.client.post(url, {
            'add_service_type': '1',
            'name': 'Montaj',
        })
        self.assertEqual(response.status_code, 302)
        follow = self.client.get(url)
        self.assertContains(follow, 'zaten kayıtlı')

    def test_update_service_type_name(self):
        obj = ServiceTypeOption.objects.create(name='Eski ad')
        url = reverse('settings_service_types')
        response = self.client.post(url, {
            'update_service_type': '1',
            'id': obj.pk,
            'name': 'Yeni ad',
        })
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.name, 'Yeni ad')

    def test_add_status_requires_color(self):
        url = reverse('settings_statuses')
        response = self.client.post(url, {
            'add_status': '1',
            'name': 'Test durum',
        })
        self.assertEqual(response.status_code, 302)
        follow = self.client.get(url)
        self.assertContains(follow, 'renk', status_code=200)
        self.assertEqual(StatusOption.objects.filter(name='Test durum').count(), 0)

    def test_add_status_with_color(self):
        url = reverse('settings_statuses')
        response = self.client.post(url, {
            'add_status': '1',
            'name': 'Test durum 2',
            'color': '#3b82f6',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StatusOption.objects.filter(name='Test durum 2').count(), 1)
