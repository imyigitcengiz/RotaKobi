"""Modül kapısı — kapalı modül/entegrasyon URL erişimi."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from common.module_runtime import get_enabled_module_slugs, module_route_allowed
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
        self.client = Client()
        self.client.force_login(self.user)

    def _slugs_without(self, *omit):
        return [s for s in get_enabled_module_slugs() if s not in omit]

    def test_closed_integration_blocks_tools_media_url(self):
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = self._slugs_without('integration_media')
        settings.save()
        self.assertFalse(module_route_allowed('integration_media'))
        response = self.client.get('/tools/medya/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/panel/moduller/', response.url)

    def test_closed_whatsapp_blocks_bridge_url(self):
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = self._slugs_without('integration_whatsapp_bridge')
        settings.save()
        response = self.client.get('/tools/whatsapp-baglan/')
        self.assertEqual(response.status_code, 302)

    def test_outreach_closed_hides_whatsapp_even_if_integration_on(self):
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = self._slugs_without('outreach')
        settings.save()
        self.assertFalse(module_route_allowed('integration_whatsapp_bridge'))
        response = self.client.get('/tools/whatsapp-baglan/')
        self.assertEqual(response.status_code, 302)

    def test_sub_app_closed_blocks_payables_route(self):
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = self._slugs_without('supplier_payables')
        settings.save()
        self.assertFalse(module_route_allowed('supplier_payables'))
        response = self.client.get('/muhasebe/borclar/')
        self.assertEqual(response.status_code, 302)

    def test_tools_hub_stays_accessible_when_integrations_closed(self):
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = self._slugs_without(
            'integration_whatsapp_bridge',
            'integration_whatsapp_api',
            'integration_media',
            'integration_weather',
        )
        settings.save()
        response = self.client.get('/tools/')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('/panel/moduller/', response.url)
