"""Kiracı (marka/bayi) çözümlemesi ve bayi erişim testleri."""

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase, override_settings

from common.brand_access import path_blocked_for_dealer, user_is_dealer_only
from common.brand_scope import create_brand_for_user
from common.tenant import build_brand_public_url, resolve_tenant_from_path, resolve_tenant_from_host
from core_settings.models import BrandMembership, BusinessBrand, SiteSettings

User = get_user_model()


class TenantResolutionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='test1234')
        self.hq = create_brand_for_user(self.owner, 'Merkez Marka')
        self.hq.host_slug = 'marka'
        self.hq.save(update_fields=['host_slug'])
        self.dealer = BusinessBrand.objects.create(
            name='Kadıköy Bayi',
            slug='kadikoy',
            host_slug='kadikoy',
            panel_kind=BusinessBrand.PANEL_DEALER,
            parent_brand=self.hq,
            tenant_routing=BusinessBrand.TENANT_PATH,
            created_by=self.owner,
        )
        BrandMembership.objects.create(
            user=self.owner,
            brand=self.dealer,
            role=BrandMembership.ROLE_OWNER,
        )

    def test_resolve_hq_from_path(self):
        brand, prefix = resolve_tenant_from_path('/marka/giris/')
        self.assertEqual(brand.pk, self.hq.pk)
        self.assertEqual(prefix, '/marka')

    def test_resolve_dealer_from_path(self):
        brand, prefix = resolve_tenant_from_path('/marka/kadikoy/contact/')
        self.assertEqual(brand.pk, self.dealer.pk)
        self.assertEqual(prefix, '/marka/kadikoy')

    @override_settings(DEBUG=True)
    def test_resolve_hq_from_subdomain(self):
        brand = resolve_tenant_from_host('marka.localhost')
        self.assertEqual(brand.pk, self.hq.pk)

    @override_settings(DEBUG=False)
    def test_resolve_hq_from_production_subdomain(self):
        import os
        from unittest.mock import patch

        self.hq.host_slug = 'acme'
        self.hq.save(update_fields=['host_slug'])
        with patch.dict(os.environ, {'COOLOPS_TENANT_BASE_DOMAIN': 'kobihub.com'}, clear=False):
            brand = resolve_tenant_from_host('acme.kobihub.com')
        self.assertIsNotNone(brand)
        self.assertEqual(brand.pk, self.hq.pk)

    @override_settings(DEBUG=False)
    def test_bare_platform_host_ignores_tenant(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {'COOLOPS_TENANT_BASE_DOMAIN': 'kobihub.com'}, clear=False):
            self.assertIsNone(resolve_tenant_from_host('kobihub.com'))
            self.assertIsNone(resolve_tenant_from_host('www.kobihub.com'))

    @override_settings(DEBUG=True)
    def test_build_dealer_path_url(self):
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = '127.0.0.1:8000'
        url = build_brand_public_url(self.dealer, request)
        self.assertIn('/marka/kadikoy/', url)


class DealerAccessTests(TestCase):
    def setUp(self):
        SiteSettings.objects.create(site_name='Tenant Test')
        self.owner = User.objects.create_user(username='hqowner', password='test1234')
        self.dealer_user = User.objects.create_user(username='bayi1', password='test1234')
        self.hq = create_brand_for_user(self.owner, 'HQ')
        self.dealer = BusinessBrand.objects.create(
            name='Bayi Panel',
            slug='bayi1',
            panel_kind=BusinessBrand.PANEL_DEALER,
            parent_brand=self.hq,
            tenant_routing=BusinessBrand.TENANT_PATH,
            created_by=self.owner,
        )
        BrandMembership.objects.create(
            user=self.dealer_user,
            brand=self.dealer,
            role=BrandMembership.ROLE_DEALER,
        )
        self.client = Client()

    def test_dealer_only_detection(self):
        self.assertTrue(user_is_dealer_only(self.dealer_user))
        self.assertFalse(user_is_dealer_only(self.owner))

    def test_dealer_blocked_from_platform_panel(self):
        self.client.force_login(self.dealer_user)
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, '/panel/')

    def test_platform_login_rejects_dealer_only_user(self):
        response = self.client.post('/giris/', {
            'username': 'bayi1',
            'password': 'test1234',
        })
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, '/panel/')

    def test_path_blocked_helper(self):
        self.assertTrue(path_blocked_for_dealer('/panel/'))
        self.assertTrue(path_blocked_for_dealer('/panel/abonelik/'))
        self.assertFalse(path_blocked_for_dealer('/contact/'))
