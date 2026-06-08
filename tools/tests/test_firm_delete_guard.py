from django.contrib.auth import get_user_model
from django.test import TestCase

from common.tests.helpers import default_test_brand
from core_settings.models import SolutionPartner, SolutionPartnerType
from tools.firm_delete_guard import PARTNER_DELETE_MESSAGE, is_partner_protected
from tools.models import MapsScrapedFirm

User = get_user_model()


class FirmDeleteGuardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='firmguard', password='test12345', is_superuser=True)
        self.brand = default_test_brand()
        self.partner_type = SolutionPartnerType.objects.create(name='Teknik', is_active=True)

    def test_is_partner_protected_by_kind(self):
        firm = MapsScrapedFirm.objects.create(
            name='Ortak',
            firm_kind=MapsScrapedFirm.KIND_PARTNER,
            brand=self.brand,
        )
        self.assertTrue(is_partner_protected(firm))

    def test_is_partner_protected_by_solution_partner_link(self):
        partner = SolutionPartner.objects.create(
            name='Bağlı Ortak',
            phone='05321112233',
            partner_type=self.partner_type,
            brand=self.brand,
        )
        firm = MapsScrapedFirm.objects.get(solution_partner=partner)
        self.assertTrue(is_partner_protected(firm))

    def test_selected_delete_blocks_partner_only_selection(self):
        MapsScrapedFirm.objects.create(name='Normal', firm_kind=MapsScrapedFirm.KIND_BUSINESS, brand=self.brand)
        partner_firm = MapsScrapedFirm.objects.create(
            name='Korumalı',
            firm_kind=MapsScrapedFirm.KIND_PARTNER,
            brand=self.brand,
        )

        self.client.force_login(self.user)
        resp = self.client.post(
            '/contact/firmalar/hafiza/temizle/',
            data={'mode': 'selected', 'firm_ids': [partner_firm.id]},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data['ok'])
        self.assertIn('Çözüm ortağı', data['error'])
        self.assertTrue(MapsScrapedFirm.objects.filter(pk=partner_firm.id).exists())

    def test_selected_delete_allows_normal_firm(self):
        normal = MapsScrapedFirm.objects.create(name='Silinebilir', firm_kind=MapsScrapedFirm.KIND_BUSINESS, brand=self.brand)

        self.client.force_login(self.user)
        resp = self.client.post(
            '/contact/firmalar/hafiza/temizle/',
            data={'mode': 'selected', 'firm_ids': [normal.id]},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])
        self.assertFalse(MapsScrapedFirm.objects.filter(pk=normal.id).exists())

    def test_clear_all_keeps_partners(self):
        MapsScrapedFirm.objects.create(name='Normal', firm_kind=MapsScrapedFirm.KIND_BUSINESS, brand=self.brand)
        partner = MapsScrapedFirm.objects.create(name='Ortak', firm_kind=MapsScrapedFirm.KIND_PARTNER, brand=self.brand)

        self.client.force_login(self.user)
        resp = self.client.post(
            '/contact/firmalar/hafiza/temizle/',
            data={'mode': 'all', 'confirm': 'TEMIZLE'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['blocked'], 1)
        self.assertFalse(MapsScrapedFirm.objects.filter(name='Normal').exists())
        self.assertTrue(MapsScrapedFirm.objects.filter(pk=partner.id).exists())

    def test_serialize_firm_marks_partner_as_delete_protected(self):
        from tools.firm_memory import serialize_firm

        firm = MapsScrapedFirm.objects.create(name='Ortak', firm_kind=MapsScrapedFirm.KIND_PARTNER, brand=self.brand)
        payload = serialize_firm(firm)
        self.assertTrue(payload['delete_protected'])
        self.assertEqual(payload['delete_block_reason'], PARTNER_DELETE_MESSAGE)
