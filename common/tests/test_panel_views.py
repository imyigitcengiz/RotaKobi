"""Panel ve modül merkezi smoke testleri."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

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

    def test_home_requires_login(self):
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 302)

    def test_home_ok_for_admin(self):
        self.client.force_login(self.user)
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Modül')

    def test_module_hub_ok(self):
        self.client.force_login(self.user)
        response = self.client.get('/panel/moduller/')
        self.assertEqual(response.status_code, 200)

    def test_capabilities_hub_ok(self):
        self.client.force_login(self.user)
        response = self.client.get('/panel/yetenekler/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entegrasyon')
