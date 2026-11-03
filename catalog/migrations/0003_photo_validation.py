from django.db import migrations, models
import django.core.validators
import catalog.image_uploads


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_landing_clarity_faq")]

    operations = [
        migrations.AlterField(
            model_name="sitesettings", name="hero_image",
            field=models.ImageField(blank=True, upload_to="hero/", validators=[
                django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
                catalog.image_uploads.validate_image_size,
            ], verbose_name="Фото первого экрана"),
        ),
        migrations.AlterField(
            model_name="service", name="image",
            field=models.ImageField(blank=True, upload_to="content/", validators=[
                django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
                catalog.image_uploads.validate_image_size,
            ], verbose_name="Главная фотография"),
        ),
        migrations.AlterField(
            model_name="project", name="image",
            field=models.ImageField(blank=True, upload_to="content/", validators=[
                django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
                catalog.image_uploads.validate_image_size,
            ], verbose_name="Главная фотография"),
        ),
        migrations.AlterField(
            model_name="article", name="image",
            field=models.ImageField(blank=True, upload_to="content/", validators=[
                django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
                catalog.image_uploads.validate_image_size,
            ], verbose_name="Главная фотография"),
        ),
        migrations.AlterField(
            model_name="projectimage", name="image",
            field=models.ImageField(upload_to="projects/", validators=[
                django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
                catalog.image_uploads.validate_image_size,
            ], verbose_name="Фото"),
        ),
    ]
