from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("mebel/", views.services, name="services"),
    path("mebel/<slug:slug>/", views.service_detail, name="service_detail"),
    path("raboty/", views.projects, name="projects"),
    path("raboty/<slug:slug>/", views.project_detail, name="project_detail"),
    path("stati/", views.articles, name="articles"),
    path("stati/<slug:slug>/", views.article_detail, name="article_detail"),
    path("kontakty/", views.contacts, name="contacts"),
    path("privacy/", views.privacy, name="privacy"),
    path("zayavka/", views.submit_lead, name="submit_lead"),
    path("robots.txt", views.robots, name="robots"),
],
