"""Key-only administrator login and session revocation safety tests."""
import hashlib

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse


KEY = "mk_" + "A" * 43
WRONG_KEY = "mk_" + "B" * 43
DIGEST = hashlib.sha256(KEY.encode("utf-8")).hexdigest()
NEXT_DIGEST = hashlib.sha256(("mk_" + "C" * 43).encode("utf-8")).hexdigest()


@override_settings(
    MEBEL_ADMIN_KEY_SHA256=DIGEST,
    MEBEL_ADMIN_KEY_USER="keyadmin",
    MEBEL_ADMIN_KEY_REQUIRED=True,
)
class AdminKeyLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_superuser(
            "keyadmin", "keyadmin@example.invalid", "unused-strong-password"
        )
        self.url = reverse("admin_key_login")

    def test_separate_page_has_one_secret_field_and_private_headers(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="access_key"')
        self.assertContains(response, 'type="password"')
        self.assertNotContains(response, KEY)
        self.assertNotContains(response, DIGEST)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["Referrer-Policy"], "no-referrer")

    def test_login_opens_django_admin_without_disclosing_key(self):
        response = self.client.post(self.url, {"access_key": KEY})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin:index"))
        session = self.client.session
        self.assertEqual(session["mebel_admin_key_hash"], DIGEST)
        self.assertNotIn(KEY, str(dict(session.items())))
        self.assertLessEqual(session.get_expiry_age(), 8 * 60 * 60)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_invalid_key_does_not_create_a_session(self):
        response = self.client.post(self.url, {"access_key": WRONG_KEY})
        self.assertEqual(response.status_code, 401)
        self.assertContains(response, "Неверный ключ", status_code=401)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_key_does_not_authorize_an_unknown_superuser(self):
        with override_settings(MEBEL_ADMIN_KEY_USER="unknown"):
            response = self.client.post(self.url, {"access_key": KEY})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_key_rotation_revokes_existing_admin_session(self):
        self.client.post(self.url, {"access_key": KEY})
        with override_settings(MEBEL_ADMIN_KEY_SHA256=NEXT_DIGEST):
            response = self.client.get(reverse("admin:index"))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, self.url)
            self.assertNotIn("_auth_user_id", self.client.session)

    def test_old_password_session_is_not_admin_access(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_original_admin_password_login_is_closed(self):
        response = self.client.get("/upravlenie/login/")
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        response = self.client.post(
            "/upravlenie/login/",
            {"username": "keyadmin", "password": "unused-strong-password"},
        )
        self.assertEqual(response.status_code, 405)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_key_login_shares_ip_throttle(self):
        for _ in range(10):
            self.assertEqual(self.client.post(self.url, {"access_key": WRONG_KEY}).status_code, 401)
        self.assertEqual(
            self.client.post(self.url, {"access_key": KEY}).status_code, 429
        )

    @override_settings(TRUST_PROXY_X_REAL_IP=False)
    def test_spoofed_ip_cannot_bypass_key_throttle(self):
        for i in range(10):
            response = self.client.post(
                self.url, {"access_key": WRONG_KEY},
                HTTP_X_REAL_IP=f"203.0.113.{i}",
            )
            self.assertEqual(response.status_code, 401)
        self.assertEqual(
            self.client.post(
                self.url, {"access_key": KEY},
                HTTP_X_REAL_IP="198.51.100.9",
            ).status_code,
            429,
        )

    def test_csrf_is_required_for_key_submission(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.url, {"access_key": KEY}).status_code, 403)
        client.get(self.url)
        csrf_token = client.cookies["csrftoken"].value
        response = client.post(
            self.url,
            {"access_key": KEY, "csrfmiddlewaretoken": csrf_token},
        )
        self.assertEqual(response.status_code, 302)

    def test_admin_is_unavailable_without_configured_key_in_production(self):
        with override_settings(MEBEL_ADMIN_KEY_SHA256="", MEBEL_ADMIN_KEY_REQUIRED=True):
            self.assertEqual(self.client.get("/upravlenie/login/").status_code, 503)
            self.assertEqual(self.client.get(reverse("admin:index")).status_code, 503)

    def test_admin_logout_invalidates_key_session(self):
        self.client.post(self.url, {"access_key": KEY})
        self.client.post(reverse("admin:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
