"""End-to-end editor workflows: no code edits needed to publish site content."""
import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Article, Project, ProjectImage, Service, SiteSettings


def picture(filename="example.jpg"):
    buffer = io.BytesIO()
    Image.new("RGB", (48, 32), "white").save(buffer, format="JPEG")
    return SimpleUploadedFile(filename, buffer.getvalue(), content_type="image/jpeg")


class AdminContentWorkflowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.directory = tempfile.TemporaryDirectory()
        cls.media_override = override_settings(MEDIA_ROOT=cls.directory.name)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        cls.directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            "owner", "owner@example.com", "some-long-random-test-password"
        )
        self.client.force_login(self.user)

    def test_owner_updates_contacts_and_hero_image(self):
        path = reverse("admin:catalog_sitesettings_add")
        response = self.client.post(path, {
            "brand": "Мастерская мебели",
            "hero_title": "Корпусная мебель на заказ",
            "hero_text": "Индивидуальные проекты",
            "hero_image": picture(),
            "phone": "+7 (917) 123-45-67",
            "address": "Стерлитамак",
            "schedule": "",
            "contact_email": "",
            "telegram": "",
            "whatsapp": "",
            "about": "Точное исполнение",
            "seo_title": "Корпусная мебель",
            "seo_description": "По индивидуальным размерам",
            "_save": "Сохранить",
        })
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get("/"), "Мастерская мебели")
        self.assertContains(self.client.get("/"), "Индивидуальные проекты")
        self.assertContains(self.client.get("/kontakty/"), "+7 (917) 123-45-67")
        self.assertContains(self.client.get("/"), ".jpg")
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_service_russian_title_publishes_without_slug(self):
        response = self.client.post(reverse("admin:catalog_service_add"), {
            "title": "Кухни на заказ",
            "slug": "",
            "summary": "По вашим размерам",
            "body": "Проектируем индивидуально",
            "published": "on",
            "order": 1,
            "seo_title": "",
            "seo_description": "",
            "_save": "Сохранить",
        })
        self.assertEqual(response.status_code, 302)
        item = Service.objects.get()
        self.assertEqual(item.slug, "kuhni-na-zakaz")
        self.assertContains(self.client.get(item.get_absolute_url()), item.title)
        self.assertContains(self.client.get("/"), item.title)

    def test_duplicate_titles_get_unique_addresses(self):
        for _ in range(2):
            response = self.client.post(reverse("admin:catalog_service_add"), {
                "title": "Кухни на заказ", "slug": "", "summary": "",
                "body": "", "published": "on", "order": 0,
                "seo_title": "", "seo_description": "",
                "_save": "Сохранить",
            })
            self.assertEqual(response.status_code, 302)
        self.assertEqual(
            set(Service.objects.values_list("slug", flat=True)),
            {"kuhni-na-zakaz", "kuhni-na-zakaz-2"},
        )

    def test_article_can_be_published_and_hidden(self):
        response = self.client.post(reverse("admin:catalog_article_add"), {
            "title": "Выбор столешницы", "slug": "",
            "summary": "Советы по материалам",
            "body": "На что обратить внимание",
            "published": "on", "order": 0,
            "seo_title": "", "seo_description": "",
            "_save": "Сохранить",
        })
        self.assertEqual(response.status_code, 302)
        article = Article.objects.get()
        self.assertEqual(article.slug, "vybor-stoleshnitsy")
        self.assertContains(self.client.get(article.get_absolute_url()), "На что обратить внимание")
        article.published = False
        article.save()
        self.assertEqual(self.client.get(article.get_absolute_url()).status_code, 404)

    def test_project_with_two_gallery_photos(self):
        response = self.client.post(reverse("admin:catalog_project_add"), {
            "title": "Шкаф в спальню", "slug": "",
            "summary": "Индивидуальный шкаф", "body": "Встроенный вариант",
            "published": "on", "order": 0, "seo_title": "", "seo_description": "",
            "photos-TOTAL_FORMS": "2",
            "photos-INITIAL_FORMS": "0",
            "photos-MIN_NUM_FORMS": "0",
            "photos-MAX_NUM_FORMS": "1000",
            "photos-0-image": picture("front.jpg"),
            "photos-0-caption": "Фасады",
            "photos-0-order": 0,
            "photos-1-image": picture("inside.jpg"),
            "photos-1-caption": "Наполнение",
            "photos-1-order": 1,
            "_save": "Сохранить",
        })
        self.assertEqual(response.status_code, 302)
        item = Project.objects.get()
        self.assertEqual(item.slug, "shkaf-v-spalnyu")
        self.assertEqual(ProjectImage.objects.filter(project=item).count(), 2)
        page = self.client.get(item.get_absolute_url())
        self.assertContains(page, "Фасады")
        self.assertContains(page, "Наполнение")

    def test_invalid_image_is_rejected(self):
        response = self.client.post(reverse("admin:catalog_service_add"), {
            "title": "Шкафы", "slug": "",
            "image": SimpleUploadedFile("bad.jpg", b"not an image", content_type="image/jpeg"),
            "summary": "", "body": "", "published": "on", "order": 0,
            "seo_title": "", "seo_description": "", "_save": "Сохранить",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Service.objects.count(), 0)
