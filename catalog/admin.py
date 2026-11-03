from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.html import format_html

from .slugs import latin_slug

from .models import Article, FAQ, Lead, PrivacyPolicy, Project, ProjectImage, Service, SiteSettings


class ContentForm(forms.ModelForm):
    slug = forms.SlugField(label="Адрес страницы", required=False, max_length=180,
                           help_text="Оставьте пустым: адрес создастся автоматически из названия.")

    def clean_slug(self):
        value = self.cleaned_data.get("slug") or (
            self.instance.slug if self.instance.pk else ""
        )
        if value:
            return value
        base = latin_slug(self.cleaned_data.get("title", ""))
        candidate, number = base, 2
        manager = self._meta.model.objects
        while manager.filter(slug=candidate).exclude(pk=self.instance.pk).exists():
            suffix = f"-{number}"
            candidate = base[:180 - len(suffix)] + suffix
            number += 1
        return candidate


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Основное", {"fields": ("brand", "hero_title", "hero_text", "hero_image", "about")}),
        ("Контакты", {"fields": ("phone", "address", "schedule", "contact_email", "telegram", "whatsapp")}),
        ("Поиск", {"fields": ("seo_title", "seo_description")}),
    ]

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class ContentAdmin(admin.ModelAdmin):
    list_display = ("title", "published", "order", "updated_at")
    list_filter = ("published",)
    list_editable = ("published", "order")
    search_fields = ("title", "summary")
    form = ContentForm
    save_on_top = True


@admin.register(Service)
class ServiceAdmin(ContentAdmin):
    pass


class ProjectPhotoInline(admin.TabularInline):
    model = ProjectImage
    extra = 1
    readonly_fields = ("preview",)
    fields = ("image", "preview", "caption", "order")

    @admin.display(description="Предпросмотр")
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="Фотография проекта" style="max-width:180px;max-height:120px;object-fit:contain">',
            obj.image.url,
        )


@admin.register(Project)
class ProjectAdmin(ContentAdmin):
    inlines = [ProjectPhotoInline]


@admin.register(Article)
class ArticleAdmin(ContentAdmin):
    pass


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "published", "order")
    list_filter = ("published",)
    list_editable = ("published", "order")
    search_fields = ("question", "answer")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "phone", "name", "status", "source",
        "consent_version", "consent_withdrawn_at",
    )
    list_filter = ("status", "created_at", "consent_withdrawn_at")
    search_fields = ("phone", "name", "message")
    readonly_fields = (
        "name", "phone", "message", "source", "consent_at",
        "consent_version", "consent_policy", "consent_withdrawn_at",
        "created_at",
    )
    fields = (
        "name", "phone", "message", "source", "status", "consent_at",
        "consent_version", "consent_policy", "consent_withdrawn_at",
        "created_at",
    )
    actions = ("confirm_consent_withdrawal",)

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.consent_withdrawn_at is not None:
            fields.append("status")
        return fields

    @admin.action(description="Подтвердить отзыв согласия (после проверки обращения)")
    def confirm_consent_withdrawal(self, request, queryset):
        # Идентификация заявителя проводится оператором вне сайта.
        # Повторное действие не изменяет первоначальную дату регистрации.
        updated = queryset.filter(consent_withdrawn_at__isnull=True).update(
            consent_withdrawn_at=timezone.now(),
            status="withdrawn",
        )
        self.message_user(
            request,
            f"Подтверждённый отзыв зарегистрирован для {updated} заявок. "
            "Не связывайтесь по отозванному согласию. "
            "Проверка оснований хранения и удаление данных выполняются отдельно.",
        )


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ("version", "operator_name", "is_active", "published_at")
    list_filter = ("is_active",)
    search_fields = ("version", "operator_name")
    readonly_fields = ("is_active", "published_at", "created_at")
    actions = ("activate_policy", "disable_policy")
    fieldsets = [
        ("Версия и публикация", {"fields": ("version", "is_active", "published_at", "created_at")}),
        ("Оператор", {"fields": (
            "operator_name", "operator_status", "operator_identifier",
            "operator_address", "operator_contact",
        )}),
        ("Обработка данных", {"fields": (
            "purposes", "data_categories", "data_subjects", "processing_actions",
            "legal_basis", "retention_period", "deletion_procedure",
            "withdrawal_procedure", "security_measures", "third_parties",
        )}),
        ("Тексты", {"fields": ("additional_text", "consent_text")}),
    ]

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.published_at:
            fields.extend(PrivacyPolicy.EDITABLE_FIELDS)
        return fields

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and not (obj and obj.published_at)

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Групповое удаление обходит проверку конкретной опубликованной редакции.
        actions.pop("delete_selected", None)
        return actions

    @admin.action(description="Опубликовать выбранную редакцию (одну)")
    def activate_policy(self, request, queryset):
        selected = list(queryset[:2])
        if len(selected) != 1:
            self.message_user(request, "Выберите ровно одну редакцию.", messages.ERROR)
            return
        policy = selected[0]
        try:
            with transaction.atomic():
                list(PrivacyPolicy.objects.select_for_update().filter(is_active=True))
                PrivacyPolicy.objects.filter(is_active=True).exclude(pk=policy.pk).update(is_active=False)
                policy.is_active = True
                policy.save()
        except (ValidationError, IntegrityError) as exc:
            self.message_user(request, f"Редакция не опубликована: {exc}", messages.ERROR)
            return
        self.message_user(request, f"Редакция {policy.version} используется для новых заявок.")

    @admin.action(description="Остановить приём заявок по выбранной редакции (одной)")
    def disable_policy(self, request, queryset):
        selected = list(queryset[:2])
        if len(selected) != 1:
            self.message_user(request, "Выберите ровно одну редакцию.", messages.ERROR)
            return
        PrivacyPolicy.objects.filter(pk=selected[0].pk, is_active=True).update(is_active=False)
        self.message_user(request, "Редакция отключена. Без действующей редакции заявки не принимаются.")
