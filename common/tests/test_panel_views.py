"""Panel ve modül merkezi smoke testleri."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from common.module_runtime import build_panel_integrations, build_panel_modules, get_enabled_module_slugs
from core_settings.models import SiteSettings
from users.models import Role

User = get_user_model()


class PanelViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        role = Role.objects.filter(slug='admin').first()
        self.user = User.objects.create_user(username='_panel_test', password='test1234')
        if role:
            self.user.role = role
            self.user.save()
        SiteSettings.objects.create(site_name='Panel Test')

    def test_home_requires_login(self):
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 302)

    def test_home_ok_for_admin(self):
        self.client.force_login(self.user)
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Modül')

    def test_home_hides_closed_integrations(self):
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = [
            s for s in get_enabled_module_slugs()
            if s != 'integration_data_harvest'
        ]
        settings.save()
        self.client.force_login(self.user)
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Firma &amp; Lead Kazıma')
        self.assertNotContains(response, 'Firma bul')

    def test_home_hides_sub_app_modules(self):
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = [
            s for s in get_enabled_module_slugs()
            if s not in ('supplier_payables', 'projects', 'multi_cash', 'project_costing')
        ]
        settings.save()
        self.client.force_login(self.user)
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Tedarikçi borçları')
        self.assertNotContains(response, 'Montaj programı')

    def test_panel_integrations_require_parent_module(self):
        settings = SiteSettings.objects.first()
        settings.enabled_module_slugs = [
            s for s in get_enabled_module_slugs()
            if s != 'outreach'
        ]
        settings.save()
        integrations = build_panel_integrations(self.user)
        outreach_slugs = {
            i['slug'] for i in integrations
            if i.get('panel_section') == 'outreach'
        }
        self.assertEqual(outreach_slugs, set())

    def test_panel_modules_only_primary_hubs(self):
        modules = build_panel_modules(self.user)
        slugs = {m['slug'] for m in modules}
        self.assertTrue(slugs.issubset({'contact', 'services', 'accounting', 'outreach'}))

    def test_module_hub_ok(self):
        self.client.force_login(self.user)
        response = self.client.get('/panel/moduller/')
        self.assertEqual(response.status_code, 200)

    def test_capabilities_hub_ok(self):
        self.client.force_login(self.user)
        response = self.client.get('/panel/yetenekler/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entegrasyon')

    def test_introducer_knowledge_base_public(self):
        response = self.client.get('/bilgi-bankasi/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bilgi bankası')
        self.assertContains(response, 'Tam demo')

    def test_introducer_knowledge_base_journey_query(self):
        response = self.client.get('/bilgi-bankasi/?yol=hizmet-hizli')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hızlı demo')

    def test_contact_hub_ok(self):
        self.client.force_login(self.user)
        response = self.client.get('/contact/')
        self.assertEqual(response.status_code, 200)

    def test_whatsapp_baglan_ok(self):
        self.client.force_login(self.user)
        response = self.client.get('/tools/whatsapp-baglan/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WhatsApp Köprüsü')
