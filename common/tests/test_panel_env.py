from django.test import SimpleTestCase

from common.panel_env import (
    detect_panel_fqdn,
    detect_panel_origin,
    normalize_panel_service_env,
)


class PanelEnvTests(SimpleTestCase):
    def setUp(self):
        self._env = dict(__import__('os').environ)

    def tearDown(self):
        import os

        os.environ.clear()
        os.environ.update(self._env)

    def _set(self, **kwargs):
        import os

        for key, value in kwargs.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_coolify_service_vars(self):
        self._set(
            SERVICE_FQDN_APP='app-test.sslip.io',
            SERVICE_URL_APP='http://app-test.sslip.io',
            APP_URL='http://stale.example.com',
        )
        fqdn, url = normalize_panel_service_env()
        self.assertEqual(fqdn, 'app-test.sslip.io')
        self.assertEqual(url, 'http://app-test.sslip.io')
        self.assertEqual(detect_panel_fqdn(), 'app-test.sslip.io')

    def test_plesk_kobiops_domain(self):
        self._set(
            KOBIOPS_DOMAIN='ops.ornek.com',
            SERVICE_FQDN_APP=None,
            SERVICE_URL_APP=None,
            APP_URL=None,
        )
        fqdn, url = normalize_panel_service_env()
        self.assertEqual(fqdn, 'ops.ornek.com')
        self.assertEqual(url, 'https://ops.ornek.com')
        self.assertEqual(detect_panel_origin(), 'https://ops.ornek.com')

    def test_1panel_domain_and_public_url(self):
        self._set(
            KOBIOPS_DOMAIN='panel.firma.com',
            KOBIOPS_PUBLIC_URL='https://panel.firma.com',
        )
        fqdn, url = normalize_panel_service_env()
        self.assertEqual(fqdn, 'panel.firma.com')
        self.assertEqual(url, 'https://panel.firma.com')

    def test_dokploy_fqdn_fallback(self):
        self._set(
            DOKPLOY_FQDN='panel.dokploy.test',
            SERVICE_FQDN_APP=None,
        )
        self.assertEqual(detect_panel_fqdn(), 'panel.dokploy.test')
        self.assertEqual(detect_panel_origin(), 'https://panel.dokploy.test')

    def test_dokploy_https_sslip_normalized_to_http(self):
        self._set(
            SERVICE_URL_APP='https://app-test.sslip.io',
            SERVICE_FQDN_APP=None,
        )
        fqdn, url = normalize_panel_service_env()
        self.assertEqual(fqdn, 'app-test.sslip.io')
        self.assertEqual(url, 'http://app-test.sslip.io')

    def test_dokploy_container_id_fqdn_ignored(self):
        self._set(
            SERVICE_FQDN_APP='5bffcfbd178d',
            SERVICE_URL_APP='https://5bffcfbd178d',
            DOKPLOY_FQDN='app-test.sslip.io',
        )
        fqdn, url = normalize_panel_service_env()
        self.assertEqual(fqdn, 'app-test.sslip.io')
        self.assertEqual(url, 'http://app-test.sslip.io')

    def test_plesk_ignores_stale_sslip_service_fqdn(self):
        self._set(
            COOLOPS_PANEL='plesk',
            KOBIOPS_PLESK='1',
            KOBIOPS_DOMAIN='ops.ornek.com',
            SERVICE_FQDN_APP='old-test.sslip.io',
            SERVICE_URL_APP='http://old-test.sslip.io',
            APP_URL='http://old-test.sslip.io',
        )
        fqdn, url = normalize_panel_service_env()
        self.assertEqual(fqdn, 'ops.ornek.com')
        self.assertEqual(url, 'https://ops.ornek.com')
