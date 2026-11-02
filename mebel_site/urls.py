from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from catalog.sitemaps import ArticleSitemap, ProjectSitemap, ServiceSitemap, StaticSitemap

admin.site.site_header = "Управление мебельным сайтом"
admin.site.site_title = "Панель управления"
admin.site.index_title = "Содержимое сайта и заявки"

sitemaps = {
    "static": StaticSitemap,
    "services": ServiceSitemap,
    "projects": ProjectSitemap,
    "articles": ArticleSitemap,
}

urlpatterns = [
    path("upravlenie/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("", include("catalog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
