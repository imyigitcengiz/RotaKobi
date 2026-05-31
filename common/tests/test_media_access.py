from django.contrib.auth import get_user_model
from django.test import TestCase

from common.media_access import user_can_access_media_path
from users.models import Permission, Role

User = get_user_model()


class MediaAccessTests(TestCase):
    def setUp(self):
        role = Role.objects.create(slug='viewer', name='Viewer', is_system=False)
        perm, _ = Permission.objects.get_or_create(
            codename='contact.customers_view',
            defaults={'name': 'View', 'module': 'Test', 'kind': 'action', 'sort_order': 0},
        )
        role.permissions.add(perm)
        self.user = User.objects.create_user(username='viewer', password='x', role=role)

    def test_customer_media_requires_customer_perm(self):
        self.assertTrue(
            user_can_access_media_path(self.user, 'customers/1/dosyalar/test.jpg'),
        )

    def test_site_media_denied_without_settings(self):
        self.assertFalse(user_can_access_media_path(self.user, 'site/logo.png'))
