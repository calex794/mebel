"""Consent publication, attribution, version changes, and fail-closed behavior."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .models import Lead, PrivacyPolicy


def draft(version="v1", **changes):
    data = {
        "version": version,
        "operator_name": "Проверочный оператор",
        "operator_status": "person",
        "operator_address": "Проверочный адрес",
        "operator_contact": "privacy@example.org",
        "purposes": "Обратная связь по заявке",
        "data_categories": "Телефон, имя, текст обращения",
        "data_subjects": "Посетители",
        "processing_actions": "Получение, запись, хранение",
        "legal_basis": "Согласие",
        "retention_period": "Указанный оператором срок",
        "deletion_procedure": "Удаление по завершении срока",
        "withdrawal_procedure": "Обращение на указанный адрес",
        "security_measures": "Ограничение доступа",
        "consent_text": "Даю согласие на обработку данных для связи.",
    }
    data.update(changes)
    return PrivacyPolicy.objects.create(**data)


class PrivacyConsentTests(TestCase):
    def setUp(self):
        cache.clear()

    def submit(self, **changes):
        payload = {
            "phone": "+7 927 123-45-67", "consent": "on",
            "consent_version": "v1", "next": "/",
        }
        payload.update(changes)
        return self.client.post(reverse("submit_lead"), payload)

    def test_no_approved_document_blocks_both_forms_and_post(self):
        page = self.client.get("/")
        self.assertNotContains(page, 'name="phone"')
        self.assertContains(page, "Приём заявок пока недоступен")
        self.assertContains(self.client.get("/privacy/"), "Документ ещё не опубликован")
        self.assertEqual(self.submit().status_code, 503)
        self.assertEqual(Lead.objects.count(), 0)

    def test_unpublished_draft_blocks_submissions(self):
        draft()
        self.assertEqual(self.submit().status_code, 503)
        self.assertEqual(Lead.objects.count(), 0)

    def test_incomplete_document_cannot_be_published(self):
        item = draft(operator_contact="")
        item.is_active = True
        with self.assertRaises(ValidationError):
            item.save()
        item.refresh_from_db()
        self.assertFalse(item.is_active)

    def test_consent_record_and_public_page_are_exact_revision(self):
        item = draft(is_active=True)
        page = self.client.get("/")
        self.assertContains(page, 'name="consent_version" value="v1"', count=2)
        self.assertContains(page, "Даю согласие на обработку данных", count=2)
        self.assertContains(self.client.get("/privacy/?version=v1"), "Обратная связь по заявке")
        self.assertEqual(self.submit().status_code, 302)
        lead = Lead.objects.get()
        self.assertEqual(lead.consent_version, "v1")
        self.assertEqual(lead.consent_policy, item)
        self.assertIsNotNone(lead.consent_at)

    def test_missing_or_wrong_version_is_rejected(self):
        draft(is_active=True)
        for value in ("", "forged"):
            with self.subTest(version=value):
                self.assertEqual(self.submit(consent_version=value).status_code, 409 if value else 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_unchecked_consent_is_rejected(self):
        draft(is_active=True)
        self.assertEqual(self.submit(consent="").status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_rotation_retains_original_consent_and_archive(self):
        old = draft(is_active=True)
        self.assertEqual(self.submit().status_code, 302)
        new = draft("v2", consent_text="Новая редакция согласия.")
        admin = get_user_model().objects.create_superuser("owner", "owner@example.org", "safe-long-password")
        self.client.force_login(admin)
        response = self.client.post(
            reverse("admin:catalog_privacypolicy_changelist"),
            {"action": "activate_policy", "_selected_action": [str(new.pk)]},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        new.refresh_from_db()
        old.refresh_from_db()
        self.assertTrue(new.is_active)
        self.assertFalse(old.is_active)
        self.assertEqual(self.client.get("/privacy/?version=v1").status_code, 200)
        self.assertContains(self.client.get("/privacy/?version=v1"), "архивная")
        self.assertContains(self.client.get("/privacy/"), "Новая редакция согласия.")
        self.assertEqual(self.submit().status_code, 409)
        self.assertEqual(self.submit(consent_version="v2").status_code, 302)
        self.assertEqual(list(Lead.objects.order_by("id").values_list("consent_version", flat=True)), ["v1", "v2"])
        self.assertEqual(Lead.objects.first().consent_policy, new)

    def test_archived_document_is_read_only_and_protected(self):
        item = draft(is_active=True)
        self.assertEqual(self.submit().status_code, 302)
        item.consent_text = "Изменённое согласие"
        with self.assertRaises(ValidationError):
            item.save()
        item.refresh_from_db()
        with self.assertRaises(ProtectedError):
            item.delete()

    def test_unpublished_document_is_not_exposed(self):
        draft("private", operator_name="Не публиковать")
        self.assertEqual(self.client.get("/privacy/?version=private").status_code, 404)

    def test_admin_does_not_allow_editing_or_deleting_published_policy(self):
        item = draft(is_active=True)
        admin = get_user_model().objects.create_superuser("owner", "owner@example.org", "safe-long-password")
        self.client.force_login(admin)
        page = self.client.get(reverse("admin:catalog_privacypolicy_change", args=[item.pk]))
        self.assertContains(page, "readonly")
        self.assertNotContains(page, 'name="consent_text"')
        delete_page = self.client.get(reverse("admin:catalog_privacypolicy_delete", args=[item.pk]))
        self.assertIn(delete_page.status_code, (302, 403))

    def test_legacy_leads_remain_without_a_made_up_version(self):
        from django.utils import timezone
        legacy = Lead.objects.create(phone="+7 900 000-00-00", consent_at=timezone.now())
        self.assertEqual(legacy.consent_version, "")
        self.assertIsNone(legacy.consent_policy)
