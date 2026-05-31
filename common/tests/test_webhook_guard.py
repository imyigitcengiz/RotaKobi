from django.test import SimpleTestCase

from common.webhook_guard import WebhookURLError, validate_outbound_webhook_url


class WebhookGuardTests(SimpleTestCase):
    def test_https_public_ok(self):
        url = validate_outbound_webhook_url('https://8.8.8.8/hook')
        self.assertTrue(url.startswith('https://'))

    def test_private_ip_blocked(self):
        with self.assertRaises(WebhookURLError):
            validate_outbound_webhook_url('https://127.0.0.1/hook')

    def test_http_non_local_blocked(self):
        with self.assertRaises(WebhookURLError):
            validate_outbound_webhook_url('http://example.com/hook')
