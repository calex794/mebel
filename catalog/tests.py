from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .models import Article, Lead, PrivacyPolicy, Project, Service, SiteSettings


class PublicPagesTests(TestCase):
    def setUp(self):
        cache.clear()
        PrivacyPolicy.objects.create(
            version="v1", operator_name="Испытательный оператор",
            operator_status="company", operator_address="Тестовый адрес",
            operator_contact="test@example.org", purposes="Ответ на обращение",
            data_categories="Телефон", data_subjects="Посетители сайта",
            processing_actions="Запись и использование",
            legal_basis="Согласие", retention_period="До прекращения цели",
            deletion_procedure="По установленному порядку",
            withdrawal_procedure="Письменное обращение",
            security_measures="Ограничение доступа",
            consent_text="Согласие на связь по заявке",
            is_active=True,
        )

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

    def test_home_has_clear_category_and_regions(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Корпусная мебель на заказ по вашим размерам")
        self.assertContains(response, "Стерлитамак, Салават, Ишимбай")
        self.assertContains(response, 'id="hero-phone"')

    def test_empty_content_sections_are_hidden(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertNotIn('id="works-heading"', html)
        self.assertNotIn('id="services-heading"', html)
        self.assertNotIn('id="articles-heading"', html)
        self.assertNotIn("Здесь появятся фотографии выполненных проектов", html)

    def test_published_work_and_service_present(self):
        Service.objects.create(title="Кухни на заказ", slug="kuhni", published=True)
        Project.objects.create(title="Шкаф в прихожую", slug="shkaf", published=True)
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn('id="works-heading"', html)
        self.assertIn('id="services-heading"', html)
        self.assertLess(html.index('id="works-heading"'), html.index('id="services-heading"'))
        self.assertIn("Кухни на заказ", html)
        self.assertIn("Шкаф в прихожую", html)

    def test_draft_work_not_in_home(self):
        Project.objects.create(title="Скрытая работа", slug="hidden", published=False)
        self.assertNotContains(self.client.get(reverse("home")), "Скрытая работа")

    def test_about_is_editable_on_main(self):
        SiteSettings.objects.create(about="Собственная история мастерской")
        self.assertContains(self.client.get(reverse("home")), "Собственная история мастерской")

    def test_faq_publication(self):
        from .models import FAQ
        FAQ.objects.create(question="Как выбрать?", answer="По образцам.", published=True, order=1)
        FAQ.objects.create(question="Не показывать", answer="Черновик.", published=False, order=2)
        page = self.client.get(reverse("home"))
        self.assertContains(page, "Как выбрать?")
        self.assertNotContains(page, "Не показывать")

    def test_faq_admin_requires_auth(self):
        from django.urls import reverse
        from .models import FAQ
        FAQ.objects.create(question="Вопрос", answer="Ответ")
        address=reverse("admin:catalog_faq_changelist")
        self.assertEqual(self.client.get(address).status_code, 302)
        user = get_user_model().objects.create_superuser("editor", "editor@example.com", "a-safe-password-456")
        self.client.force_login(user)
        self.assertEqual(self.client.get(address).status_code, 200)

    def test_short_form_is_on_first_screen(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'id="hero-phone"')
        self.assertContains(response, 'name="consent"')
        self.assertContains(response, 'name="phone"', count=2)

    def test_short_form_saves_lead_without_extra_fields(self):
        response = self.client.post(reverse("submit_lead"), {
            "phone": "+7 927 123-45-67",
            "consent": "on", "consent_version": "v1", "next": "/",
        })
        self.assertRedirects(response, "/")
        lead = Lead.objects.get()
        self.assertEqual(lead.name, "")
        self.assertEqual(lead.message, "")
        self.assertEqual(lead.source, "/")

    def test_submit_lead(self):
        response = self.client.post(reverse("submit_lead"), {
            "name": "Анна", "phone": "+7 927 123-45-67",
            "message": "Шкаф", "consent": "on", "consent_version": "v1", "next": "/",
        })
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(Lead.objects.first().message, "Шкаф")

    def test_phone_required(self):
        self.assertEqual(self.client.post(reverse("submit_lead"), {"consent": "on", "consent_version": "v1"}).status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_consent_required(self):
        self.assertEqual(self.client.post(reverse("submit_lead"), {"phone": "+7 927 123-45-67"}).status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_honeypot(self):
        self.assertEqual(self.client.post(reverse("submit_lead"), {
            "phone": "+7 927 123-45-67", "consent": "on", "consent_version": "v1", "website": "spam"
        }).status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_no_external_redirect(self):
        response = self.client.post(reverse("submit_lead"), {
            "phone": "+7 927 123-45-67", "consent": "on", "consent_version": "v1",
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


    def test_search_metadata_is_distinct_for_sections(self):
        expected = {
            "services": "Индивидуальные решения для вашего пространства.",
            "projects": "Примеры мебели, изготовленной по индивидуальным проектам.",
            "articles": "О выборе мебели, материалах и планировании интерьера.",
            "contacts": "Контакты мастерской корпусной мебели на заказ",
        }
        homepage = self.client.get(reverse("home")).content.decode()
        for page, fragment in expected.items():
            with self.subTest(page=page):
                content = self.client.get(reverse(page)).content.decode()
                self.assertIn('<meta name="description" content="', content)
                self.assertIn(fragment, content)
                self.assertNotIn(fragment, homepage)

    def test_canonical_url_ignores_tracking_parameters(self):
        response = self.client.get("/raboty/?utm_source=vk&ref=advertising")
        self.assertContains(
            response,
            '<link rel="canonical" href="http://testserver/raboty/">',
        )
        self.assertNotContains(response, 'href="http://testserver/raboty/?utm_source=')

    def test_without_policy_no_buttons_link_to_disabled_application_form(self):
        PrivacyPolicy.objects.filter(is_active=True).update(is_active=False)
        for page in ("home", "services", "contacts"):
            with self.subTest(page=page):
                body = self.client.get(reverse(page)).content.decode()
                self.assertNotIn('href="#lead-form"', body)
        project = Project.objects.create(
            title="Шкаф без формы", slug="shkaf-bez-formy", published=True
        )
        self.assertNotContains(
            self.client.get(project.get_absolute_url()),
            'href="#lead-form"',
        )

    def test_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("submit_lead"), {
            "phone": "+7 927 123-45-67", "consent": "on", "consent_version": "v1",
        }).status_code, 403)

    def test_rate_limit(self):
        for _ in range(5):
            self.assertEqual(self.client.post(reverse("submit_lead"), {
                "phone": "+7 927 123-45-67", "consent": "on", "consent_version": "v1",
            }).status_code, 302)
        response = self.client.post(reverse("submit_lead"), {
            "phone": "+7 927 123-45-67", "consent": "on", "consent_version": "v1",
        })
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Lead.objects.count(), 5)
