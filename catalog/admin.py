from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect

from .models import Article, Lead, Project, ProjectImage, Service, SiteSettings


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
    prepopulated_fields = {"slug": ("title",)}
    save_on_top = True


@admin.register(Service)
class ServiceAdmin(ContentAdmin):
    pass


class ProjectPhotoInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(ContentAdmin):
    inlines = [ProjectPhotoInline]


@admin.register(Article)
class ArticleAdmin(ContentAdmin):
    pass


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
