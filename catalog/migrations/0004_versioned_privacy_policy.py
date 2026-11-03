from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("catalog", "0003_image_validators")]

    operations = [
        migrations.CreateModel(
            name="PrivacyPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.CharField(help_text="Уникальное обозначение, например 2026-11-01. После публикации не изменяется.", max_length=40, unique=True, verbose_name="Редакция")),
                ("operator_name", models.CharField(blank=True, max_length=255, verbose_name="Оператор: ФИО или название")),
                ("operator_status", models.CharField(blank=True, choices=[("person", "Физическое лицо"), ("self_employed", "Самозанятый"), ("sole_trader", "Индивидуальный предприниматель"), ("company", "Юридическое лицо")], max_length=20, verbose_name="Статус оператора")),
                ("operator_identifier", models.CharField(blank=True, max_length=100, verbose_name="ИНН / ОГРН (если применимо)")),
                ("operator_address", models.TextField(blank=True, verbose_name="Адрес оператора")),
                ("operator_contact", models.TextField(blank=True, verbose_name="Контакты для обращений по данным")),
                ("purposes", models.TextField(blank=True, verbose_name="Цели обработки")),
                ("data_categories", models.TextField(blank=True, verbose_name="Перечень обрабатываемых данных")),
                ("data_subjects", models.TextField(blank=True, verbose_name="Категории субъектов данных")),
                ("processing_actions", models.TextField(blank=True, verbose_name="Способы и действия по обработке")),
                ("legal_basis", models.TextField(blank=True, verbose_name="Правовые основания обработки")),
                ("retention_period", models.TextField(blank=True, verbose_name="Сроки обработки и хранения")),
                ("deletion_procedure", models.TextField(blank=True, verbose_name="Порядок прекращения обработки и удаления")),
                ("withdrawal_procedure", models.TextField(blank=True, verbose_name="Порядок отзыва согласия")),
                ("security_measures", models.TextField(blank=True, verbose_name="Меры по защите данных")),
                ("third_parties", models.TextField(blank=True, verbose_name="Получатели и порученная обработка (если есть)")),
                ("additional_text", models.TextField(blank=True, verbose_name="Дополнительный текст политики")),
                ("consent_text", models.TextField(blank=True, help_text="Точная формулировка, которую посетитель явно подтверждает отдельной отметкой.", verbose_name="Текст отдельного согласия рядом с формой")),
                ("is_active", models.BooleanField(default=False, help_text="Меняется через действие «Опубликовать» в списке; не означает юридического одобрения.", verbose_name="Действующая редакция")),
                ("published_at", models.DateTimeField(blank=True, editable=False, null=True, verbose_name="Дата первой публикации")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
            ],
            options={
                "verbose_name": "Политика обработки данных",
                "verbose_name_plural": "Политика обработки данных",
                "ordering": ["-published_at", "-id"],
                "constraints": [models.UniqueConstraint(fields=("is_active",), condition=models.Q(is_active=True), name="catalog_one_active_privacy_policy")],
            },
        ),
        migrations.AddField(
            model_name="lead",
            name="consent_version",
            field=models.CharField(blank=True, default="", max_length=40, verbose_name="Редакция согласия"),
        ),
        migrations.AddField(
            model_name="lead",
            name="consent_policy",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="leads", to="catalog.privacypolicy", verbose_name="Документ согласия"),
        ),
    ]
