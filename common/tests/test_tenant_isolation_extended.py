"""Genişletilmiş cross-tenant izolasyon testleri — outreach, personel, chat, analytics."""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from analytics.panel_summary import build_outreach_panel_context
from common.brand_scope import SESSION_ACTIVE_BRAND, create_brand_for_user
from common.kobi_lean_preset import lean_kobi_slugs
from common.tests.helpers import ensure_test_plan, login_with_brand, set_user_modules
from core_settings.models import ServicePersonnel, SiteSettings
from tools.models import FirmTag, MapsScrapedFirm, OutreachCollection, OutreachCollectionMember

User = get_user_model()


def _role_with_perms(slug, name, codenames):
    from users.models import Permission, Role

    role = Role.objects.create(slug=slug, name=name, is_system=False)
    for codename in codenames:
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={'name': codename, 'module': 'Test', 'kind': 'action', 'sort_order': 0},
        )
        role.permissions.add(perm)
    return role


class TenantIsolationBase(TestCase):
    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(site_name='Extended Isolation')
        ensure_test_plan(lean_kobi_slugs())


class OutreachIsolationTests(TenantIsolationBase):
    def setUp(self):
        super().setUp()
        role = _role_with_perms('outreach-a', 'Outreach', ('access.outreach', 'contact.firms', 'access.contact'))
        self.owner_a = User.objects.create_user(username='out_a', password='test1234', role=role)
        self.owner_b = User.objects.create_user(username='out_b', password='test1234', role=role)
        slugs = lean_kobi_slugs()
        set_user_modules(self.owner_a, slugs)
        set_user_modules(self.owner_b, slugs)
        self.brand_a = create_brand_for_user(self.owner_a, 'Outreach A')
        self.brand_b = create_brand_for_user(self.owner_b, 'Outreach B')
        self.col_a = OutreachCollection.objects.create(name='Kampanya A', brand=self.brand_a)
        self.col_b = OutreachCollection.objects.create(name='Kampanya B', brand=self.brand_b)
        self.firm_a = MapsScrapedFirm.objects.create(
            name='Firma A', phone_normalized='905111111111', brand=self.brand_a,
        )
        self.firm_b = MapsScrapedFirm.objects.create(
            name='Firma B', phone_normalized='905222222222', brand=self.brand_b,
        )

    def _login(self, user, brand):
        login_with_brand(self.client, user, brand)

    def test_collections_api_scoped_to_brand(self):
        from common.brand_scope import filter_by_brand
        from django.test import RequestFactory

        req = RequestFactory().get('/iletisim/api/kampanyalar/')
        req.user = self.owner_a
        req.session = self.client.session
        req.session[SESSION_ACTIVE_BRAND] = self.brand_a.pk
        scoped = filter_by_brand(OutreachCollection.objects.all(), req)
        ids = set(scoped.values_list('pk', flat=True))
        self.assertIn(self.col_a.pk, ids)
        self.assertNotIn(self.col_b.pk, ids)

    def test_collection_detail_404_other_brand(self):
        self._login(self.owner_a, self.brand_a)
        resp = self.client.get(f'/iletisim/api/kampanyalar/{self.col_b.pk}/')
        self.assertIn(resp.status_code, (403, 404))

    def test_collection_delete_404_other_brand(self):
        self._login(self.owner_a, self.brand_a)
        resp = self.client.delete(f'/iletisim/api/kampanyalar/{self.col_b.pk}/')
        self.assertIn(resp.status_code, (403, 404))

    def test_firm_memory_list_excludes_other_brand(self):
        self._login(self.owner_a, self.brand_a)
        data = self.client.get('/contact/firmalar/hafiza/').json()
        names = {row['name'] for row in data['results']}
        self.assertIn('Firma A', names)
        self.assertNotIn('Firma B', names)

    def test_firm_bulk_delete_cannot_touch_other_brand(self):
        self._login(self.owner_a, self.brand_a)
        resp = self.client.post(
            '/contact/firmalar/hafiza/temizle/',
            data=json.dumps({'mode': 'selected', 'firm_ids': [self.firm_b.pk]}),
            content_type='application/json',
        )
        self.assertTrue(MapsScrapedFirm.objects.filter(pk=self.firm_b.pk).exists())

    def test_firm_csv_export_scoped(self):
        self._login(self.owner_a, self.brand_a)
        resp = self.client.get('/contact/firmalar/export-csv/')
        body = resp.content.decode('utf-8-sig')
        self.assertIn('Firma A', body)
        self.assertNotIn('Firma B', body)

    def test_outreach_panel_counts_brand_scoped(self):
        OutreachCollectionMember.objects.create(
            collection=self.col_a,
            name='Üye A',
            phone_normalized='905111111111',
            phone_display='05311111111',
        )
        OutreachCollectionMember.objects.create(
            collection=self.col_b,
            name='Üye B',
            phone_normalized='905222222222',
            phone_display='05322222222',
        )
        member_count_a = OutreachCollectionMember.objects.filter(collection__brand=self.brand_a).count()
        member_count_b = OutreachCollectionMember.objects.filter(collection__brand=self.brand_b).count()
        self.assertEqual(member_count_a, 1)
        self.assertEqual(member_count_b, 1)

        from django.test import RequestFactory

        req = RequestFactory().get('/panel/')
        req.user = self.owner_a
        session = self.client.session
        session[SESSION_ACTIVE_BRAND] = self.brand_a.pk
        session.save()
        req.session = session
        ctx = build_outreach_panel_context(req)
        self.assertEqual(ctx['outreach_campaigns'], 1)
        self.assertEqual(ctx['outreach_members'], 1)


class PersonnelIsolationTests(TenantIsolationBase):
    def setUp(self):
        super().setUp()
        role = _role_with_perms(
            'pers-a',
            'Personnel',
            ('access.accounting', 'contact.payroll', 'accounting.payroll'),
        )
        self.owner_a = User.objects.create_user(username='pers_a', password='test1234', role=role)
        self.owner_b = User.objects.create_user(username='pers_b', password='test1234', role=role)
        from common.kobi_lean_preset import full_finance_extension_slugs

        slugs = full_finance_extension_slugs()
        set_user_modules(self.owner_a, slugs)
        set_user_modules(self.owner_b, slugs)
        self.brand_a = create_brand_for_user(self.owner_a, 'Personel A')
        self.brand_b = create_brand_for_user(self.owner_b, 'Personel B')
        self.person_a = ServicePersonnel.objects.create(name='Ali', brand=self.brand_a)
        self.person_b = ServicePersonnel.objects.create(name='Veli', brand=self.brand_b)

    def _login(self, user, brand):
        login_with_brand(self.client, user, brand)

    def test_personnel_update_404_other_brand(self):
        self._login(self.owner_a, self.brand_a)
        resp = self.client.post(
            '/muhasebe/personel/',
            data={
                'update_personnel': '1',
                'id': self.person_b.pk,
                'name': 'Hack',
                'is_active': 'on',
            },
        )
        self.assertEqual(resp.status_code, 404)
        self.person_b.refresh_from_db()
        self.assertEqual(self.person_b.name, 'Veli')

    def test_personnel_delete_404_other_brand(self):
        self._login(self.owner_a, self.brand_a)
        resp = self.client.post(
            '/muhasebe/personel/',
            data={'delete_personnel': '1', 'id': self.person_b.pk},
        )
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(ServicePersonnel.objects.filter(pk=self.person_b.pk).exists())


class ChatIsolationTests(TenantIsolationBase):
    def setUp(self):
        super().setUp()
        role = _role_with_perms('chat-a', 'Chat', ('access.chat', 'access.contact'))
        self.owner_a = User.objects.create_user(username='chat_a', password='test1234', role=role)
        self.owner_b = User.objects.create_user(username='chat_b', password='test1234', role=role)
        self.member_a = User.objects.create_user(username='member_a', password='test1234', role=role)
        slugs = lean_kobi_slugs()
        set_user_modules(self.owner_a, slugs)
        set_user_modules(self.owner_b, slugs)
        set_user_modules(self.member_a, slugs)
        self.brand_a = create_brand_for_user(self.owner_a, 'Chat A')
        self.brand_b = create_brand_for_user(self.owner_b, 'Chat B')
        from core_settings.models import BrandMembership

        BrandMembership.objects.create(user=self.member_a, brand=self.brand_a, role=BrandMembership.ROLE_MEMBER)

    def _login(self, user, brand):
        login_with_brand(self.client, user, brand)

    def test_chat_users_api_same_brand_only(self):
        self._login(self.owner_a, self.brand_a)
        data = self.client.get('/chat/api/users/').json()
        ids = {u['id'] for u in data['users']}
        self.assertIn(self.member_a.pk, ids)
        self.assertNotIn(self.owner_b.pk, ids)

    def test_chat_direct_403_other_brand_user(self):
        self._login(self.owner_a, self.brand_a)
        resp = self.client.post(
            '/chat/api/direct/',
            data=json.dumps({'user_id': self.owner_b.pk}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_chat_direct_ok_same_brand(self):
        self._login(self.owner_a, self.brand_a)
        resp = self.client.post(
            '/chat/api/direct/',
            data=json.dumps({'user_id': self.member_a.pk}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])


class FirmTagIsolationTests(TenantIsolationBase):
    def setUp(self):
        super().setUp()
        role = _role_with_perms('tag-a', 'Tags', ('contact.firms', 'access.contact'))
        self.owner_a = User.objects.create_user(username='tag_a', password='test1234', role=role)
        self.owner_b = User.objects.create_user(username='tag_b', password='test1234', role=role)
        slugs = lean_kobi_slugs()
        set_user_modules(self.owner_a, slugs)
        set_user_modules(self.owner_b, slugs)
        self.brand_a = create_brand_for_user(self.owner_a, 'Tag A')
        self.brand_b = create_brand_for_user(self.owner_b, 'Tag B')
        self.tag_a = FirmTag.objects.create(name='VIP', brand=self.brand_a)
        self.tag_b = FirmTag.objects.create(name='VIP', brand=self.brand_b)

    def _login(self, user, brand):
        login_with_brand(self.client, user, brand)

    def test_tags_api_lists_only_active_brand(self):
        self._login(self.owner_a, self.brand_a)
        data = self.client.get('/contact/firmalar/etiketler/').json()
        ids = {t['id'] for t in data['tags']}
        self.assertIn(self.tag_a.pk, ids)
        self.assertNotIn(self.tag_b.pk, ids)

    def test_tag_delete_404_other_brand(self):
        self._login(self.owner_a, self.brand_a)
        resp = self.client.delete(f'/contact/firmalar/etiketler/{self.tag_b.pk}/')
        self.assertIn(resp.status_code, (403, 404))
        self.assertTrue(FirmTag.objects.filter(pk=self.tag_b.pk).exists())


class NullableBrandRegressionTests(TenantIsolationBase):
    def test_customer_requires_brand_on_create(self):
        from django.db import IntegrityError
        from customers.models import Customer

        with self.assertRaises(IntegrityError):
            Customer.objects.create(name='Markasız')

    def test_firm_requires_brand_on_create(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            MapsScrapedFirm.objects.create(name='Markasız firma')

    def test_personnel_requires_brand_on_create(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            ServicePersonnel.objects.create(name='Markasız personel')
