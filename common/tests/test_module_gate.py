"""Modül kapısı — kapalı modül/entegrasyon URL erişimi."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from common.kobi_lean_preset import lean_kobi_slugs
from common.module_context import bind_module_user, reset_module_user
from common.module_runtime import get_enabled_module_slugs, module_route_allowed
from common.tests.helpers import (
    ensure_brand_for_user,
    lean_modules_without,
    login_with_brand,
    set_user_modules,
)
from core_settings.models import SiteSettings
from users.models import Role

User = get_user_model()


class ModuleGateTests(TestCase):
    def setUp(self):
        role = Role.objects.filter(slug='service').first()
        self.user = User.objects.create_user(username='_gate', password='x')
        if role:
            self.user.role = role
            self.user.save()
        SiteSettings.objects.create(site_name='Gate Test')
        self.brand = ensure_brand_for_user(self.user, 'Gate Marka')
        set_user_modules(self.user, lean_kobi_slugs())
        self.client = Client()
        login_with_brand(self.client, self.user, self.brand)

    def _set_modules(self, slugs):
        set_user_modules(self.user, slugs)

    def _assert_module_blocked(self, slug: str):
        token = bind_module_user(self.user)
        try:
            self.assertFalse(module_route_allowed(slug))
        finally:
            reset_module_user(token)

    def _slugs_without(self, *omit):
        return lean_modules_without(*omit)

    def test_closed_integration_blocks_tools_media_url(self):
        self._set_modules(self._slugs_without('integration_media'))
        self._assert_module_blocked('integration_media')
        response = self.client.get('/tools/medya/')
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Modül Merkezi', status_code=403)

    def test_closed_whatsapp_blocks_bridge_url(self):
        self._set_modules(self._slugs_without('integration_whatsapp_bridge'))
        response = self.client.get('/tools/whatsapp-baglan/')
        self.assertEqual(response.status_code, 403)

    def test_outreach_closed_hides_whatsapp_api_even_if_integration_on(self):
        slugs = list(get_enabled_module_slugs()) + ['integration_whatsapp_api']
        slugs = [s for s in slugs if s != 'outreach']
        self._set_modules(slugs)
        self._assert_module_blocked('integration_whatsapp_api')
        response = self.client.get('/tools/whatsapp-api/')
        self.assertEqual(response.status_code, 403)

    def test_outreach_closed_hides_bulk_messaging_even_if_integration_on(self):
        slugs = list(get_enabled_module_slugs()) + ['integration_bulk_messaging']
        slugs = [s for s in slugs if s != 'outreach']
        self._set_modules(slugs)
        self._assert_module_blocked('integration_bulk_messaging')
        response = self.client.get('/iletisim/kampanyalar/')
        self.assertEqual(response.status_code, 403)

    def test_bulk_messaging_closed_blocks_campaign_url(self):
        slugs = [s for s in get_enabled_module_slugs() if s != 'integration_bulk_messaging']
        if 'outreach' not in slugs:
            slugs.append('outreach')
        self._set_modules(slugs)
        self._assert_module_blocked('integration_bulk_messaging')
        response = self.client.get('/iletisim/kampanyalar/')
        self.assertEqual(response.status_code, 403)

    def test_whatsapp_bridge_works_without_outreach(self):
        role = Role.objects.filter(slug='admin').first()
        if role:
            self.user.role = role
            self.user.save()
        self._set_modules(lean_kobi_slugs())
        token = bind_module_user(self.user)
        try:
            self.assertTrue(module_route_allowed('integration_whatsapp_bridge'))
        finally:
            reset_module_user(token)
        response = self.client.get('/tools/whatsapp-baglan/')
        self.assertEqual(response.status_code, 200)

    def test_payables_particle_closed_blocks_route(self):
        slugs = [s for s in lean_kobi_slugs() if s != 'p.accounting.payables']
        if 'accounting' not in slugs:
            slugs.append('accounting')
        self._set_modules(slugs)
        response = self.client.get('/muhasebe/borclar/')
        self.assertEqual(response.status_code, 403)

    def test_firma_kazi_blocked_when_data_harvest_closed(self):
        self._set_modules(self._slugs_without('integration_data_harvest'))
        response = self.client.get('/contact/firma-kazi/')
        self.assertEqual(response.status_code, 403)

    def test_contact_sidebar_hides_closed_integration(self):
        self._set_modules(self._slugs_without('integration_media'))
        response = self.client.get('/contact/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Medya Kütüphanesi')

    def test_tools_hub_stays_accessible_when_integrations_closed(self):
        self._set_modules(self._slugs_without(
            'integration_whatsapp_bridge',
            'integration_whatsapp_api',
            'integration_media',
            'integration_weather',
        ))
        response = self.client.get('/tools/')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('/panel/moduller/', response.url)
