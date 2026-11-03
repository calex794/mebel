"""Проверка ручной очистки персональных данных заявки и следов согласия."""
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Lead, PrivacyPolicy


class LeadErasureTests(TestCase):
    def setUp(self):
        cache.clear()
        self.policy = PrivacyPolicy.objects.create(
            version="v1", operator_name="Тестовый оператор",
            operator_status="person", operator_address="Тестовый адрес",
            operator_contact="privacy@example.org", purposes="Обработка заявки",
            data_categories="Контакты", data_subjects="Посетители",
            processing_actions="Запись", legal_basis="Согласие",
            retention_period="По завершении цели",
            deletion_procedure="Ручная очистка",
            withdrawal_procedure="Обращение к оператору",
            security_measures="Контроль доступа",
            consent_text="Даю согласие на связь.", is_active=True,
        )
        self.lead = Lead.objects.create(
            name="Зинаида", phone="+7 927 123-45-67",
            message="Хочу шкаф", source="/mebel/?token=sensitive",
            consent_at=timezone.now(), consent_version="v1",
            consent_policy=self.policy,
        )
        self.owner = get_user_model().objects.create_superuser(
            "owner", "owner@example.org", "test-secure-password",
        )
        self.admin_url = reverse("admin:catalog_lead_changelist")

    def action(self, name="erase_withdrawn_lead", **data):
        return self.client.post(
            self.admin_url,
            {"action": name, "_selected_action": [str(self.lead.pk)], **data},
            follow=True,
        )

    def withdraw(self):
        self.action("confirm_consent_withdrawal")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "withdrawn")

    def test_only_authorised_admin_can_erase(self):
        response = self.action(
            confirm_erasure=f"СТЕРЕТЬ {self.lead.pk}",
            retention_checked="on", backups_checked="on",
        )
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, f"/upravlenie/login/?next={self.admin_url}")
        self.lead.refresh_from_db()
        self.assertIsNone(self.lead.erased_at)

    def test_no_erasure_before_confirmed_withdrawal(self):
        self.client.force_login(self.owner)
        response = self.action(
            confirm_erasure=f"СТЕРЕТЬ {self.lead.pk}",
            retention_checked="on", backups_checked="on",
        )
        self.assertContains(response, "Сначала зарегистрируйте")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.phone, "+7 927 123-45-67")
        self.assertIsNone(self.lead.erased_at)

    def test_requires_two_step_confirmation_and_acknowledgements(self):
        self.client.force_login(self.owner)
        self.withdraw()
        response = self.action()
        self.assertContains(response, "Подтверждение очистки заявки")
        self.assertContains(response, f"СТЕРЕТЬ {self.lead.pk}")
        self.assertContains(response, "резервные копии")
        self.lead.refresh_from_db()
        self.assertIsNone(self.lead.erased_at)

        response = self.action(
            confirm_erasure=f"СТЕРЕТЬ {self.lead.pk}",
            retention_checked="on",
        )
        self.assertContains(response, "Очистка не выполнена")
        self.lead.refresh_from_db()
        self.assertIsNone(self.lead.erased_at)
        response = self.action(
            confirm_erasure="СТЕРЕТЬ 99999", retention_checked="on",
            backups_checked="on",
        )
        self.assertContains(response, "Очистка не выполнена")
        self.lead.refresh_from_db()
        self.assertIsNone(self.lead.erased_at)

    def test_scrubs_all_lead_content_but_retains_nonidentifying_audit(self):
        self.client.force_login(self.owner)
        self.withdraw()
        withdrawn_at = self.lead.consent_withdrawn_at
        consent_at = self.lead.consent_at
        old_log = LogEntry.objects.create(
            user=self.owner,
            content_type=ContentType.objects.get_for_model(Lead),
            object_id=str(self.lead.pk),
            object_repr=str(self.lead),
            action_flag=CHANGE,
            change_message="Номер +7 927 123-45-67 до очистки",
        )
        response = self.action(
            confirm_erasure=f"СТЕРЕТЬ {self.lead.pk}",
            retention_checked="on", backups_checked="on",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "очищены в основной БД")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.phone, "")
        self.assertEqual(self.lead.name, "")
        self.assertEqual(self.lead.message, "")
        self.assertEqual(self.lead.source, "")
        self.assertEqual(self.lead.status, "withdrawn")
        self.assertEqual(self.lead.consent_version, "v1")
        self.assertEqual(self.lead.consent_policy, self.policy)
        self.assertEqual(self.lead.consent_withdrawn_at, withdrawn_at)
        self.assertEqual(self.lead.consent_at, consent_at)
        self.assertIsNotNone(self.lead.erased_at)
        self.assertNotIn("+7 927", str(self.lead))
        old_log.refresh_from_db()
        self.assertNotIn("+7 927", old_log.object_repr)
        self.assertEqual(old_log.change_message, "")

        first = self.lead.erased_at
        again = self.action(
            confirm_erasure=f"СТЕРЕТЬ {self.lead.pk}",
            retention_checked="on", backups_checked="on",
        )
        self.assertContains(again, "уже очищена")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.erased_at, first)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Lead.objects.filter(pk=self.lead.pk).update(phone="reinserted")

    def test_standard_admin_delete_is_forbidden(self):
        self.client.force_login(self.owner)
        changelist = self.client.get(self.admin_url)
        self.assertNotContains(changelist, 'value="delete_selected"')
        delete_page = self.client.get(
            reverse("admin:catalog_lead_delete", args=[self.lead.pk]),
        )
        self.assertIn(delete_page.status_code, (302, 403))

    def test_cannot_bulk_erase_multiple_leads(self):
        self.client.force_login(self.owner)
        self.withdraw()
        other = Lead.objects.create(
            name="Тест", phone="+7 926 000-00-00",
            consent_at=timezone.now(), consent_policy=self.policy,
            consent_version="v1", status="withdrawn",
            consent_withdrawn_at=timezone.now(),
        )
        response = self.client.post(self.admin_url, {
            "action": "erase_withdrawn_lead",
            "_selected_action": [str(self.lead.pk), str(other.pk)],
            "confirm_erasure": f"СТЕРЕТЬ {self.lead.pk}",
            "retention_checked": "on", "backups_checked": "on",
        }, follow=True)
        self.assertContains(response, "выберите ровно одну заявку")
        self.lead.refresh_from_db()
        other.refresh_from_db()
        self.assertIsNone(self.lead.erased_at)
        self.assertIsNone(other.erased_at)
