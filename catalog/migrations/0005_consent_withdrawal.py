from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_versioned_privacy_policy")]

    operations = [
        migrations.AddField(
            model_name="lead",
            name="consent_withdrawn_at",
            field=models.DateTimeField(
                blank=True,
                editable=False,
                help_text=(
                    "Отметку вносит сотрудник после проверки обращения. "
                    "Не означает автоматического удаления данных."
                ),
                null=True,
                verbose_name="Зарегистрирован подтверждённый отзыв согласия",
            ),
        ),
        migrations.AlterField(
            model_name="lead",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "Новая"),
                    ("contacted", "Связались"),
                    ("done", "Закрыта"),
                    ("withdrawn", "Согласие отозвано"),
                ],
                default="new",
                max_length=20,
                verbose_name="Состояние",
            ),
        ),
        migrations.AddConstraint(
            model_name="lead",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(consent_withdrawn_at__isnull=True)
                    | models.Q(status="withdrawn")
                ),
                name="catalog_withdrawn_lead_closed",
            ),
        ),
    ]
