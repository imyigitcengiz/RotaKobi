from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from users.impersonation import SESSION_IMPERSONATE_USER_ID, is_impersonating
from users.models import Permission, Role

User = get_user_model()


class ImpersonationTests(TestCase):
    def setUp(self):
        self.client = Client()
        Role.objects.create(slug='sa', name='SA', is_system=True)
        self.admin = User.objects.create_superuser(
            username='superadmin',
            password='test-pass-12345',
            email='sa@test.local',
        )
        self.limited_role = Role.objects.create(slug='viewer', name='Viewer', is_system=False)
        perm, _ = Permission.objects.get_or_create(
            codename='access.home',
            defaults={'name': 'Home', 'module': 'Test', 'kind': 'access', 'sort_order': 0},
        )
        self.limited_role.permissions.add(perm)
        self.target = User.objects.create_user(
            username='viewer1',
            password='test-pass-12345',
            role=self.limited_role,
        )

    def test_superuser_can_impersonate_and_stop(self):
        self.client.login(username='superadmin', password='test-pass-12345')
        res = self.client.post(reverse('admin_impersonate_start', args=[self.target.pk]))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(int(self.client.session[SESSION_IMPERSONATE_USER_ID]), self.target.pk)
        self.assertEqual(str(self.client.session.get('_auth_user_id')), str(self.admin.pk))

        res_home = self.client.get(reverse('home'))
        self.assertEqual(res_home.status_code, 200)
        self.assertContains(res_home, 'Kullanıcı görünümü')

        res_stop = self.client.post(reverse('impersonate_stop'))
        self.assertEqual(res_stop.status_code, 302)
        self.assertNotIn(SESSION_IMPERSONATE_USER_ID, self.client.session)

    def test_impersonated_user_has_target_permissions_not_superuser(self):
        self.client.login(username='superadmin', password='test-pass-12345')
        self.client.post(reverse('admin_impersonate_start', args=[self.target.pk]))
        res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res.status_code, 302)
        self.assertNotEqual(res.url, reverse('login'))

    def test_cannot_impersonate_superuser(self):
        other = User.objects.create_superuser(username='other', password='test-pass-12345')
        self.client.login(username='superadmin', password='test-pass-12345')
        res = self.client.post(reverse('admin_impersonate_start', args=[other.pk]))
        self.assertEqual(res.status_code, 302)
        self.assertNotIn(SESSION_IMPERSONATE_USER_ID, self.client.session)

    def test_non_superuser_blocked(self):
        self.client.login(username='viewer1', password='test-pass-12345')
        res = self.client.post(reverse('admin_impersonate_start', args=[self.admin.pk]))
        self.assertEqual(res.status_code, 302)
        self.assertNotIn(SESSION_IMPERSONATE_USER_ID, self.client.session)
