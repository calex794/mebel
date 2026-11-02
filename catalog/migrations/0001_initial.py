# Initial schema for the furniture lead site.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("brand", models.CharField(default="Мебель на заказ", max_length=140, verbose_name="Название мастерской")),
                ("hero_title", models.CharField(default="Корпусная мебель, созданная именно для вас", max_length=220, verbose_name="Заголовок")),
                ("hero_text", models.TextField(default="По индивидуальным размерам. С вниманием к качеству исполнения и каждой детали.", verbose_name="Подзаголовок")),
                ("hero_image", models.ImageField(blank=True, upload_to="hero/", verbose_name="Фото первого экрана")),
                ("phone", models.CharField(blank=True, max_length=50, verbose_name="Телефон")),
                ("address", models.CharField(blank=True, max_length=255, verbose_name="Адрес")),
                ("schedule", models.CharField(blank=True, max_length=200, verbose_name="Режим работы")),
                ("telegram", models.URLField(blank=True, verbose_name="Ссылка на Telegram")),
                ("whatsapp", models.URLField(blank=True, verbose_name="Ссылка на WhatsApp")),
                ("contact_email", models.EmailField(blank=True, max_length=254, verbose_name="Почта")),
                ("about", models.TextField(blank=True, verbose_name="О мастерской")),
                ("seo_title", models.CharField(default="Корпусная мебель на заказ — Стерлитамак, Салават, Ишимбай", max_length=220, verbose_name="Заголовок для поиска")),
                ("seo_description", models.CharField(default="Изготовление корпусной мебели по индивидуальным размерам в Стерлитамаке, Салавате и Ишимбае. Обсудите ваш проект с мастером.", max_length=320, verbose_name="Описание для поиска")),
            ],
            options={"verbose_name": "Настройки сайта", "verbose_name_plural": "Настройки сайта"},
        ),
        migrations.CreateModel(
            name="Lead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(blank=True, max_length=100, verbose_name="Имя")),
                ("phone", models.CharField(max_length=40, verbose_name="Телефон")),
                ("message", models.TextField(blank=True, verbose_name="Пожелания")),
                ("source", models.CharField(blank=True, max_length=300, verbose_name="Страница заявки")),
                ("status", models.CharField(choices=[("new", "Новая"), ("contacted", "Связались"), ("done", "Закрыта")], default="new", max_length=20, verbose_name="Состояние")),
                ("consent_at", models.DateTimeField(verbose_name="Согласие получено")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата")),
            ],
            options={"verbose_name": "Заявка", "verbose_name_plural": "Заявки", "ordering": ["-created_at"]},
        ),
        *[
            migrations.CreateModel(
                name=name,
                fields=[
                    ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("title", models.CharField(max_length=180, verbose_name="Название")),
                    ("slug", models.SlugField(max_length=180, unique=True, verbose_name="Адрес страницы (латиницей)")),
                    ("summary", models.TextField(blank=True, verbose_name="Краткое описание")),
                    ("image", models.ImageField(blank=True, upload_to="content/", verbose_name="Главная фотография")),
                    ("published", models.BooleanField(default=False, verbose_name="Опубликовано")),
                    ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                    ("seo_title", models.CharField(blank=True, max_length=220, verbose_name="SEO заголовок")),
                    ("seo_description", models.CharField(blank=True, max_length=320, verbose_name="SEO описание")),
                    ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                    ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменено")),
                    ("body", models.TextField(**({"blank": True} if name != "Article" else {}), verbose_name=("Текст статьи" if name == "Article" else ("Описание услуги" if name == "Service" else "Описание проекта")))),
                ],
                options={"verbose_name": singular, "verbose_name_plural": plural, "ordering": ["order", "-created_at"]},
            )
            for name, singular, plural in [
                ("Service", "Услуга", "Услуги"),
                ("Project", "Работа", "Наши работы"),
                ("Article", "Статья", "Статьи"),
            ]
        ],
        migrations.CreateModel(
            name="ProjectImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="projects/", verbose_name="Фото")),
                ("caption", models.CharField(blank=True, max_length=200, verbose_name="Описание фото")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="catalog.project", verbose_name="Работа")),
            ],
            options={"verbose_name": "Фотография работы", "verbose_name_plural": "Фотографии работы", "ordering": ["order", "id"]},
        ),
    ]
