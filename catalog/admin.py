from django.contrib import admin
from django import forms
from django.utils.html import format_html

from .slugs import latin_slug

from .models import Article, FAQ, Lead, Project, ProjectImage, Service, SiteSettings


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
    list_display = ("created_at", "phone", "name", "status", "source")
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    search_fields = ("phone", "name", "message")
    readonly_fields = ("name", "phone", "message", "source", "consent_at", "created_at")
    fields = ("name", "phone", "message", "source", "status", "consent_at", "created_at")

    def has_add_permission(self, request):
        return False
