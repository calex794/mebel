from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .image_uploads import validate_image_size

PHOTO_VALIDATORS = [FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_image_size]


class SiteSettings(models.Model):
    brand = models.CharField("Название мастерской", max_length=140, default="Мебель на заказ")
    hero_title = models.CharField("Заголовок", max_length=220, default="Корпусная мебель на заказ по вашим размерам")
    hero_text = models.TextField("Подзаголовок", default="Кухни, шкафы, гардеробные и другая мебель по индивидуальному проекту. Продумываем детали вместе с вами, а материалы и цвета выбираем по настоящим образцам.")
    hero_image = models.ImageField("Фото первого экрана", upload_to="hero/", blank=True, validators=PHOTO_VALIDATORS)
    phone = models.CharField("Телефон", max_length=50, blank=True)
    address = models.CharField("Адрес", max_length=255, blank=True)
    schedule = models.CharField("Режим работы", max_length=200, blank=True)
    telegram = models.URLField("Ссылка на Telegram", blank=True)
    whatsapp = models.URLField("Ссылка на WhatsApp", blank=True)
    contact_email = models.EmailField("Почта", blank=True)
    about = models.TextField("О мастерской", blank=True)
    seo_title = models.CharField("Заголовок для поиска", max_length=220, default="Корпусная мебель на заказ — Стерлитамак, Салават, Ишимбай")
    seo_description = models.CharField("Описание для поиска", max_length=320, default="Изготовление корпусной мебели по индивидуальным размерам в Стерлитамаке, Салавате и Ишимбае. Обсудите ваш проект с мастером.")

    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"

    def __str__(self):
        return "Настройки сайта"


class PublishedModel(models.Model):
    title = models.CharField("Название", max_length=180)
    slug = models.SlugField("Адрес страницы (латиницей)", max_length=180, unique=True)
    summary = models.TextField("Краткое описание", blank=True)
    image = models.ImageField("Главная фотография", upload_to="content/", blank=True, validators=PHOTO_VALIDATORS)
    published = models.BooleanField("Опубликовано", default=False)
    order = models.PositiveIntegerField("Порядок", default=0)
    seo_title = models.CharField("SEO заголовок", max_length=220, blank=True)
    seo_description = models.CharField("SEO описание", max_length=320, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Изменено", auto_now=True)

    class Meta:
        abstract = True
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def meta_title(self):
        return self.seo_title or self.title

    @property
    def meta_description(self):
        return self.seo_description or self.summary[:300]


class Service(PublishedModel):
    body = models.TextField("Описание услуги", blank=True)

    class Meta(PublishedModel.Meta):
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"

    def get_absolute_url(self):
        return reverse("service_detail", args=[self.slug])


class Project(PublishedModel):
    body = models.TextField("Описание проекта", blank=True)

    class Meta(PublishedModel.Meta):
        verbose_name = "Работа"
        verbose_name_plural = "Наши работы"

    def get_absolute_url(self):
        return reverse("project_detail", args=[self.slug])


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="photos", verbose_name="Работа")
    image = models.ImageField("Фото", upload_to="projects/", validators=PHOTO_VALIDATORS)
    caption = models.CharField("Описание фото", max_length=200, blank=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Фотография работы"
        verbose_name_plural = "Фотографии работы"


class Article(PublishedModel):
    body = models.TextField("Текст статьи")

    class Meta(PublishedModel.Meta):
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"

    def get_absolute_url(self):
        return reverse("article_detail", args=[self.slug])


class FAQ(models.Model):
    question = models.CharField("Вопрос", max_length=220)
    answer = models.TextField("Ответ")
    published = models.BooleanField("Опубликовано", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Вопрос и ответ"
        verbose_name_plural = "Частые вопросы"

    def __str__(self):
        return self.question



class PrivacyPolicy(models.Model):
    """Версии политики и отдельного текста согласия; опубликованная версия неизменна."""

    EDITABLE_FIELDS = (
        "version", "operator_name", "operator_status", "operator_identifier",
        "operator_address", "operator_contact", "purposes", "data_categories",
        "data_subjects", "processing_actions", "legal_basis", "retention_period",
        "deletion_procedure", "withdrawal_procedure", "security_measures",
        "third_parties", "additional_text", "consent_text",
    )
    REQUIRED_FIELDS = (
        "operator_name", "operator_status", "operator_address", "operator_contact",
        "purposes", "data_categories", "data_subjects", "processing_actions",
        "legal_basis", "retention_period", "deletion_procedure",
        "withdrawal_procedure", "security_measures", "consent_text",
    )
    OPERATOR_STATUSES = [
        ("person", "Физическое лицо"),
        ("self_employed", "Самозанятый"),
        ("sole_trader", "Индивидуальный предприниматель"),
        ("company", "Юридическое лицо"),
    ]

    version = models.CharField(
        "Редакция", max_length=40, unique=True,
        help_text="Уникальное обозначение, например 2026-11-01. После публикации не изменяется.",
    )
    operator_name = models.CharField("Оператор: ФИО или название", max_length=255, blank=True)
    operator_status = models.CharField(
        "Статус оператора", max_length=20, choices=OPERATOR_STATUSES, blank=True,
    )
    operator_identifier = models.CharField(
        "ИНН / ОГРН (если применимо)", max_length=100, blank=True,
    )
    operator_address = models.TextField("Адрес оператора", blank=True)
    operator_contact = models.TextField("Контакты для обращений по данным", blank=True)
    purposes = models.TextField("Цели обработки", blank=True)
    data_categories = models.TextField("Перечень обрабатываемых данных", blank=True)
    data_subjects = models.TextField("Категории субъектов данных", blank=True)
    processing_actions = models.TextField("Способы и действия по обработке", blank=True)
    legal_basis = models.TextField("Правовые основания обработки", blank=True)
    retention_period = models.TextField("Сроки обработки и хранения", blank=True)
    deletion_procedure = models.TextField("Порядок прекращения обработки и удаления", blank=True)
    withdrawal_procedure = models.TextField("Порядок отзыва согласия", blank=True)
    security_measures = models.TextField("Меры по защите данных", blank=True)
    third_parties = models.TextField("Получатели и порученная обработка (если есть)", blank=True)
    additional_text = models.TextField("Дополнительный текст политики", blank=True)
    consent_text = models.TextField(
        "Текст отдельного согласия рядом с формой", blank=True,
        help_text="Точная формулировка, которую посетитель явно подтверждает отдельной отметкой.",
    )
    is_active = models.BooleanField(
        "Действующая редакция", default=False,
        help_text="Меняется через действие «Опубликовать» в списке; не означает юридического одобрения.",
    )
    published_at = models.DateTimeField("Дата первой публикации", null=True, blank=True, editable=False)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Политика обработки данных"
        verbose_name_plural = "Политика обработки данных"
        ordering = ["-published_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"], condition=models.Q(is_active=True),
                name="catalog_one_active_privacy_policy",
            ),
        ]

    def __str__(self):
        return f"Редакция {self.version}"

    @classmethod
    def current(cls):
        return cls.objects.filter(is_active=True, published_at__isnull=False).first()

    def clean(self):
        super().clean()
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            if original and original.published_at and (
                any(getattr(self, field) != getattr(original, field) for field in self.EDITABLE_FIELDS)
                or self.published_at != original.published_at
            ):
                raise ValidationError("Опубликованную редакцию изменять нельзя. Создайте новую.")
        if self.is_active:
            missing = [
                str(self._meta.get_field(field).verbose_name)
                for field in self.REQUIRED_FIELDS
                if not str(getattr(self, field) or "").strip()
            ]
            if missing:
                raise ValidationError({
                    "is_active": "Перед публикацией заполните: " + ", ".join(missing),
                })

    def save(self, *args, **kwargs):
        if self.is_active and self.published_at is None:
            self.published_at = timezone.now()
        self.full_clean()
        return super().save(*args, **kwargs)


class Lead(models.Model):
    STATUS = [("new", "Новая"), ("contacted", "Связались"), ("done", "Закрыта")]
    name = models.CharField("Имя", max_length=100, blank=True)
    phone = models.CharField("Телефон", max_length=40)
    message = models.TextField("Пожелания", blank=True)
    source = models.CharField("Страница заявки", max_length=300, blank=True)
    status = models.CharField("Состояние", max_length=20, choices=STATUS, default="new")
    consent_at = models.DateTimeField("Согласие получено")
    consent_version = models.CharField("Редакция согласия", max_length=40, blank=True, default="")
    consent_policy = models.ForeignKey(
        PrivacyPolicy, on_delete=models.PROTECT, null=True, blank=True,
        related_name="leads", verbose_name="Документ согласия",
    )
    created_at = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self):
        return f"{self.phone} — {self.get_status_display()}"
