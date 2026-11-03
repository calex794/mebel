from django.core.cache import cache
from django.test import TestCase, override_settings


class ProductionSecurityTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_readiness_checks_database(self):
        self.assertEqual(self.client.get("/readyz/").status_code, 200)

    def test_admin_login_throttling(self):
        for _ in range(10):
            response = self.client.post("/upravlenie/login/", {"username": "nobody", "password": "bad"})
            self.assertNotEqual(response.status_code, 429)
        response = self.client.post("/upravlenie/login/", {"username": "nobody", "password": "bad"})
        self.assertEqual(response.status_code, 429)

    @override_settings(TRUST_PROXY_X_REAL_IP=False)
    def test_untrusted_forwarded_ip_cannot_bypass_limit(self):
        for i in range(10):
            response = self.client.post("/upravlenie/login/", {"username": "wrong", "password": "no"}, HTTP_X_REAL_IP=f"1.2.3.{i}")
            self.assertNotEqual(response.status_code, 429)
        response = self.client.post("/upravlenie/login/", {"username": "wrong", "password": "no"}, HTTP_X_REAL_IP="1.2.3.123")
        self.assertEqual(response.status_code, 429)
