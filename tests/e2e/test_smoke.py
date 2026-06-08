"""Canlı sunucu üzerinde temel kullanıcı akışları."""

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase
from django.urls import reverse

from common.brand_scope import create_brand_for_user
from common.kobi_lean_preset import lean_kobi_slugs
from common.tests.helpers import ensure_test_plan, set_user_modules
from core_settings.models import SiteSettings

User = get_user_model()


class SmokeFlowTests(LiveServerTestCase):
    def setUp(self):
        SiteSettings.objects.get_or_create(defaults={'site_name': 'Smoke Test'})
        role = __import__('users.models', fromlist=['Role']).Role.objects.filter(slug='admin').first()
        self.password = 'smoke-pass-123'
        self.user = User.objects.create_user(username='smoke_user', password=self.password)
        if role:
            self.user.role = role
            self.user.save()
        self.brand = create_brand_for_user(self.user, 'Smoke HQ')
        set_user_modules(self.user, lean_kobi_slugs())

    def test_login_panel_logout(self):
        from django.test import Client

        client = Client()
        login_url = reverse('login')
        response = client.post(login_url, {
            'username': 'smoke_user',
            'password': self.password,
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        panel = client.get('/panel/')
        self.assertEqual(panel.status_code, 200)

        logout = client.get(reverse('logout'), follow=True)
        self.assertEqual(logout.status_code, 200)

    def test_customer_create_flow(self):
        from django.test import Client

        client = Client()
        client.login(username='smoke_user', password=self.password)
        session = client.session
        session['active_brand_id'] = self.brand.pk
        session.save()

        response = client.post('/contact/musteriler/yeni/', {
            'name': 'Smoke Müşteri',
            'phone': '5551112233',
        }, follow=True)
        self.assertIn(response.status_code, (200, 302))
