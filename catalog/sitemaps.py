from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Article, Project, Service


class StaticSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return ["home", "services", "projects", "articles", "contacts", "privacy"]

    def location(self, item):
        return reverse(item)


class ContentSitemap(Sitemap):
    changefreq = "monthly"

    def lastmod(self, item):
        return item.updated_at


class ServiceSitemap(ContentSitemap):
    priority = 0.8

    def items(self):
        return Service.objects.filter(published=True)


class ProjectSitemap(ContentSitemap):
    priority = 0.6

    def items(self):
        return Project.objects.filter(published=True)


class ArticleSitemap(ContentSitemap):
    priority = 0.5

    def items(self):
        return Article.objects.filter(published=True)
