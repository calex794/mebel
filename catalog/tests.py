from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Article, Lead, Project, Service, SiteSettings


class PublicPagesTests(TestCase):
    def test_main_pages(self):
        for name in ["home", "services", "projects", "articles", "contacts", "privacy", "robots", "sitemap"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_draft_is_not_public(self):
        item = Service.objects.create(title="Тест", slug="test", published=False)
        self.assertEqual(self.client.get(item.get_absolute_url()).status_code, 404)
        item.published = True
        item.save()
        self.assertEqual(self.client.get(item.get_absolute_url()).status_code, 200)

    def test_article_visible(self):
        item = Article.objects.create(title="Материалы", slug="materialy", body="Текст", published=True)
        self.assertContains(self.client.get(item.get_absolute_url()), "Материалы")

    def test_submit_lead(self):
        response = self.client.post(reverse("submit_lead"), {
            "name": "Анна", "phone": "+7 927 123-45-67",
            "message": "Шкаф", "consent": "on", "next": "/",
        })
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(Lead.objects.first().message, "Шкаф")

    def test_phone_required(self):
        self.assertEqual(self.client.post(reverse("submit_lead"), {"consent": "on"}).status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_consent_required(self):
        self.assertEqual(self.client.post(reverse("submit_lead"), {"phone": "+7 927 123-45-67"}).status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_honeypot(self):
        self.assertEqual(self.client.post(reverse("submit_lead"), {
            "phone": "+7 927 123-45-67", "consent": "on", "website": "spam"
        }).status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_no_external_redirect(self):
        response = self.client.post(reverse("submit_lead"), {
            "phone": "+7 927 123-45-67", "consent": "on",
            "next": "https://evil.example",
        })
        self.assertRedirects(response, "/")

    def test_admin_requires_login(self):
        response = self.client.get("/upravlenie/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_admin_works_with_account(self):
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "good-password-123")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/upravlenie/").status_code, 200)

    def test_site_settings(self):
        SiteSettings.objects.create(brand="Мастерская")
        self.assertContains(self.client.get("/"), "Мастерская")

    def test_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("submit_lead"), {
            "phone": "+7 927 123-45-67", "consent": "on",
        }).status_code, 403)

    def test_rate_limit(self):
        for _ in range(5):
            self.assertEqual(self.client.post(reverse("submit_lead"), {
                "phone": "+7 927 123-45-67", "consent": "on",
            }).status_code, 302)
        response = self.client.post(reverse("submit_lead"), {
            "phone": "+7 927 123-45-67", "consent": "on",
        })
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Lead.objects.count(), 5)
