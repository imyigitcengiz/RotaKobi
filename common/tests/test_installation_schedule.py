"""Montaj programı takvim testleri."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core_settings.installation_schedule import (
    build_schedule_calendar,
    create_schedule_entry,
    is_day_holiday,
    save_schedule_settings,
)
from core_settings.models import InstallationScheduleEntry, SiteSettings
from customers.models import Customer


class InstallationScheduleTests(TestCase):
    def setUp(self):
        from common.module_particles import vertical_preset_all_slugs

        settings = SiteSettings.objects.create(site_name='Test')
        settings.enabled_module_slugs = list(vertical_preset_all_slugs('kobi'))
        settings.save()
        User = get_user_model()
        role = __import__('users.models', fromlist=['Role']).Role.objects.filter(slug='admin').first()
        self.user = User.objects.create_user(username='_sched', password='test1234')
        if role:
            self.user.role = role
            self.user.save()
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(name='Test Müşteri')

    def test_sunday_holiday_by_default(self):
        settings = SiteSettings.objects.first()
        sunday = date(2026, 6, 7)
        self.assertTrue(is_day_holiday(sunday, settings))
        self.assertFalse(is_day_holiday(date(2026, 6, 6), settings))

    def test_weekend_settings(self):
        settings = SiteSettings.objects.first()
        save_schedule_settings(settings, saturday_working=False, sunday_working=True, saturday_default_work='service')
        settings.refresh_from_db()
        self.assertFalse(settings.schedule_saturday_working)
        self.assertTrue(settings.schedule_sunday_working)
        self.assertEqual(settings.schedule_saturday_default_work, InstallationScheduleEntry.TYPE_SERVICE)

    def test_create_entry_and_calendar(self):
        today = timezone.localdate()
        create_schedule_entry(
            scheduled_date=today,
            customer_id=self.customer.id,
            notes='Asansör montajı',
            work_type=InstallationScheduleEntry.TYPE_INSTALLATION,
        )
        ctx = build_schedule_calendar(year=today.year, month=today.month)
        self.assertIn('visible_weeks', ctx)
        found = False
        for week in ctx['calendar_weeks']:
            for day in week['days']:
                if day['date'] == today and day['entries']:
                    found = True
                    self.assertEqual(day['entries'][0]['customer_name'], 'Test Müşteri')
        self.assertTrue(found)

    def test_projects_page_ok(self):
        response = self.client.get('/muhasebe/projeler/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Montaj programı')

    def test_projects_print_ok(self):
        response = self.client.get('/muhasebe/projeler/yazdir/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Montaj programı')

    def test_post_create_entry(self):
        today = timezone.localdate()
        response = self.client.post('/muhasebe/projeler/?year=2099&month=6&view=month', {
            'action': 'create_entry',
            'scheduled_date': '2099-06-15',
            'customer_id': self.customer.id,
            'work_type': InstallationScheduleEntry.TYPE_INSTALLATION,
            'notes': 'Garanti servisi',
            'calendar_year': '2099',
            'calendar_month': '6',
            'calendar_view': 'month',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('year=2099', response.url)
        self.assertIn('month=6', response.url)
        self.assertEqual(InstallationScheduleEntry.objects.count(), 1)

    def test_module_fallback_when_particle_only(self):
        from common.module_runtime import is_module_enabled

        settings = SiteSettings.objects.first()
        slugs = [s for s in settings.enabled_module_slugs if s != 'projects']
        if 'accounting' not in slugs:
            slugs.append('accounting')
        if 'p.accounting.projects' not in slugs:
            slugs.append('p.accounting.projects')
        settings.enabled_module_slugs = slugs
        settings.save()
        self.assertTrue(is_module_enabled('projects'))

    def test_operation_role_can_access(self):
        User = get_user_model()
        role = __import__('users.models', fromlist=['Role']).Role.objects.filter(slug='operation').first()
        user = User.objects.create_user(username='_ops', password='x')
        if role:
            user.role = role
            user.save()
        self.client.force_login(user)
        response = self.client.get('/muhasebe/projeler/')
        self.assertEqual(response.status_code, 200)
