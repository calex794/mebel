from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0005_consent_withdrawal")]

    operations = [
        migrations.AddField(
            model_name="lead",
            name="erased_at",
            field=models.DateTimeField(
                blank=True,
                editable=False,
                help_text=(
                    "Очищены поля заявки в основной базе. "
                    "Резервные копии обрабатываются отдельно."
                ),
                null=True,
                verbose_name="Дата очистки контактных данных",
            ),
        ),
        migrations.AddConstraint(
            model_name="lead",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(erased_at__isnull=True)
                    | models.Q(
                        status="withdrawn", consent_withdrawn_at__isnull=False,
                        phone="", name="", message="", source="",
                    )
                ),
                name="catalog_erased_lead_has_no_contact_data",
            ),
        ),
    ]
