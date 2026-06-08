"""Modül aç/kapa API testleri — plan tavanı ve abonelik sahibi."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from common.brand_scope import create_brand_for_user
from common.module_context import bind_module_user, reset_module_user
from common.module_plan import default_plan_module_seed, plan_included_modules
from common.module_runtime import is_module_installed, is_particle_enabled
from core_settings.models import BrandMembership, Plan, SiteSettings

User = get_user_model()


def _bind(user):
    return bind_module_user(user)


class ModuleToggleApiTests(TestCase):
    def setUp(self):
        role = __import__('users.models', fromlist=['Role']).Role.objects.filter(slug='admin').first()
        self.plan = Plan.objects.create(
            name='Toggle Plan',
            price=0,
            max_hq_brands=1,
            max_dealer_panels=0,
            max_users_per_brand=5,
            max_customers_per_brand=100,
            included_module_slugs=default_plan_module_seed() + ['integration_weather'],
            is_active=True,
        )
        self.user = User.objects.create_user(username='_modtog', password='x', plan=self.plan)
        if role:
            self.user.role = role
            self.user.save()
        SiteSettings.objects.create(site_name='Test')
        self.brand = create_brand_for_user(self.user, 'Toggle Marka')
        self.client.force_login(self.user)

    def _assert_installed(self, slug, expected):
        token = _bind(self.user)
        try:
            self.assertEqual(is_module_installed(slug), expected)
        finally:
            reset_module_user(token)

    def test_toggle_off_on_without_page_reload(self):
        slug = 'integration_weather'
        self._assert_installed(slug, True)

        off = self.client.post('/panel/abonelik/modul-toggle/', {'module_slug': slug})
        self.assertEqual(off.status_code, 200)
        data = off.json()
        self.assertTrue(data['ok'])
        self.assertFalse(data['installed'])
        self.user.refresh_from_db()
        self._assert_installed(slug, False)

        on = self.client.post('/panel/abonelik/modul-toggle/', {'module_slug': slug})
        self.assertEqual(on.status_code, 200)
        self.assertTrue(on.json()['installed'])

    def test_toggle_rejects_module_outside_plan(self):
        slug = 'agency_portal'
        resp = self.client.post('/panel/abonelik/modul-toggle/', {'module_slug': slug})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])

    def test_disable_montaj_particle_persists(self):
        particle = 'p.accounting.projects'
        if 'accounting' not in plan_included_modules(self.plan):
            self.plan.included_module_slugs = list(self.plan.included_module_slugs) + ['accounting']
            self.plan.save()
        token = _bind(self.user)
        try:
            self.assertTrue(is_particle_enabled(particle))
        finally:
            reset_module_user(token)

        off = self.client.post('/panel/abonelik/modul-toggle/', {'particle_slug': particle})
        self.assertTrue(off.json()['ok'])
        self.user.refresh_from_db()
        self.assertNotIn(particle, self.user.enabled_module_slugs or [])
        token = _bind(self.user)
        try:
            self.assertFalse(is_particle_enabled(particle))
        finally:
            reset_module_user(token)

    def test_toggle_requires_settings_perm(self):
        role = __import__('users.models', fromlist=['Role']).Role.objects.filter(slug='service').first()
        user = User.objects.create_user(username='_svc', password='x', plan=self.plan)
        if role:
            user.role = role
            user.save()
        BrandMembership.objects.create(
            brand=self.brand,
            user=user,
            role=BrandMembership.ROLE_MEMBER,
        )
        self.client.force_login(user)
        resp = self.client.post('/panel/abonelik/modul-toggle/', {'module_slug': 'contact'})
        self.assertIn(resp.status_code, (403, 400))
        self.assertFalse(resp.json()['ok'])

    def test_toggle_particle_off_on(self):
        slug = 'p.contact.customers'
        token = _bind(self.user)
        try:
            self.assertTrue(is_particle_enabled(slug))
        finally:
            reset_module_user(token)

        off = self.client.post('/panel/abonelik/modul-toggle/', {'particle_slug': slug})
        self.assertEqual(off.status_code, 200)
        self.assertTrue(off.json()['ok'])
        self.assertFalse(off.json()['enabled'])

        on = self.client.post('/panel/abonelik/modul-toggle/', {'particle_slug': slug})
        self.assertEqual(on.status_code, 200)
        self.assertTrue(on.json()['enabled'])

    def test_particle_requires_parent_module(self):
        modules = [s for s in plan_included_modules(self.plan) if s != 'contact']
        self.user.enabled_module_slugs = modules
        self.user.save()
        resp = self.client.post('/panel/abonelik/modul-toggle/', {'particle_slug': 'p.contact.customers'})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])

    def test_cannot_disable_last_module(self):
        only = [s for s in plan_included_modules(self.plan) if s == 'settings']
        if not only:
            only = ['settings']
            self.plan.included_module_slugs = only
            self.plan.save()
        self.user.enabled_module_slugs = only
        self.user.save()
        resp = self.client.post('/panel/abonelik/modul-toggle/', {'module_slug': 'settings'})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])
