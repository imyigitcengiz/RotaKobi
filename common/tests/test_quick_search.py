from django.contrib.auth import get_user_model
from django.test import TestCase

from common.quick_search import QUICK_SEARCH_ITEMS, build_quick_search_results, search_entities
from common.tests.helpers import default_test_brand
from customers.models import Customer
from tools.models import MapsScrapedFirm
from users.models import Role, UserNotification
from users.notifications import notify_user, refresh_system_notifications


class QuickSearchTests(TestCase):
    def test_all_items_have_string_url_name(self):
        for item in QUICK_SEARCH_ITEMS:
            self.assertIsInstance(item.url_name, (str, type(None)))
            if item.url_name is not None:
                self.assertIsInstance(item.url_name, str)
            self.assertIsInstance(item.perms_any, tuple)
            for perm in item.perms_any:
                self.assertIsInstance(perm, str)

    def test_search_returns_valid_urls_for_superuser(self):
        user = get_user_model().objects.create_superuser('qs_admin', 'qs@test.local', 'pass')
        results = build_quick_search_results(user, 'maaş', limit=5)
        self.assertTrue(results)
        for row in results:
            self.assertTrue(row['url'].startswith('/'))
            self.assertIsInstance(row['url'], str)

    def test_rbac_user_gets_filtered_results(self):
        role = Role.objects.create(slug='qs_sales', name='QS Satış')
        role.permissions.set([])
        user = get_user_model().objects.create_user('qs_sales', password='pass', role=role)
        all_results = build_quick_search_results(user, '', limit=50)
        self.assertEqual(all_results, [])

    def test_search_entities_by_customer_phone(self):
        user = get_user_model().objects.create_superuser('qs_phone', 'qs-phone@test.local', 'pass')
        brand = default_test_brand()
        Customer.objects.create(name='Ali Veli', phone='0532 111 22 33', brand=brand)
        results = search_entities(user, '5321112233', limit=10)
        titles = [row['title'] for row in results]
        self.assertIn('Ali Veli', titles)

    def test_search_entities_by_firm_phone(self):
        user = get_user_model().objects.create_superuser('qs_firm_phone', 'qs-firm@test.local', 'pass')
        brand = default_test_brand()
        MapsScrapedFirm.objects.create(
            name='Demo Firma AŞ',
            phone='0 (212) 555 66 77',
            phone_normalized='902125556677',
            brand=brand,
        )
        results = search_entities(user, '2125556677', limit=10)
        titles = [row['title'] for row in results]
        self.assertIn('Demo Firma AŞ', titles)
        firm_row = next(row for row in results if row['title'] == 'Demo Firma AŞ')
        self.assertIn('212', firm_row['subtitle'])
        self.assertIn('q=2125556677', firm_row['url'])


class NotificationTests(TestCase):
    def test_dedupe_does_not_duplicate_after_mark_read(self):
        user = get_user_model().objects.create_user('notif_user', password='pass')
        first = notify_user(user, title='Test', dedupe_key='test-key')
        self.assertIsNotNone(first)
        first.is_read = True
        first.save(update_fields=['is_read'])
        second = notify_user(user, title='Test güncellendi', dedupe_key='test-key')
        self.assertEqual(UserNotification.objects.filter(user=user, dedupe_key='test-key').count(), 1)
        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.title, 'Test güncellendi')

    def test_refresh_throttled(self):
        user = get_user_model().objects.create_superuser('notif_admin', 'n@test.local', 'pass')
        refresh_system_notifications(user)
        count_after_first = UserNotification.objects.filter(user=user).count()
        refresh_system_notifications(user)
        count_after_second = UserNotification.objects.filter(user=user).count()
        self.assertEqual(count_after_first, count_after_second)
