"""Modül aç/kapa API testleri."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from common.module_runtime import is_module_installed
from core_settings.models import SiteSettings


class ModuleToggleApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        role = __import__('users.models', fromlist=['Role']).Role.objects.filter(slug='admin').first()
        self.user = User.objects.create_user(username='_modtog', password='x')
        if role:
            self.user.role = role
            self.user.save()
        SiteSettings.objects.create(site_name='Test')
        self.client.force_login(self.user)

    def test_toggle_off_on_without_page_reload(self):
        slug = 'integration_weather'
        self.assertTrue(is_module_installed(slug))

        off = self.client.post('/panel/moduller/toggle/', {'module_slug': slug})
        self.assertEqual(off.status_code, 200)
        data = off.json()
        self.assertTrue(data['ok'])
        self.assertFalse(data['installed'])
        self.assertFalse(is_module_installed(slug))

        on = self.client.post('/panel/moduller/toggle/', {'module_slug': slug})
        self.assertEqual(on.status_code, 200)
        self.assertTrue(on.json()['installed'])

    def test_installed_state_ignores_particle_fallback(self):
        from common.module_catalog import module_by_slug
        from common.module_runtime import build_module_record, get_enabled_module_slugs, is_module_installed

        slug = 'projects'
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = [s for s in get_enabled_module_slugs() if s != slug]
        settings.save()

        self.assertFalse(is_module_installed(slug))
        record = build_module_record(self.user, module_by_slug(slug))
        self.assertFalse(record['installed'])

        resp = self.client.post('/panel/moduller/toggle/', {'module_slug': slug})
        self.assertTrue(resp.json()['installed'])
        self.assertTrue(is_module_installed(slug))

    def test_toggle_requires_settings_perm(self):
        User = get_user_model()
        role = __import__('users.models', fromlist=['Role']).Role.objects.filter(slug='service').first()
        user = User.objects.create_user(username='_svc', password='x')
        if role:
            user.role = role
            user.save()
        self.client.force_login(user)
        resp = self.client.post('/panel/moduller/toggle/', {'module_slug': 'contact'})
        self.assertEqual(resp.status_code, 403)

    def test_cannot_disable_last_module(self):
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = ['settings']
        settings.save()
        resp = self.client.post('/panel/moduller/toggle/', {'module_slug': 'settings'})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])
