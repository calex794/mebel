from django.db import migrations, models
from django.core.validators import FileExtensionValidator
from catalog.image_uploads import validate_image_size


VALIDATORS = [FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_image_size]


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_landing_clarity_faq")]

    operations = [
        migrations.AlterField(
            model_name="sitesettings", name="hero_image",
            field=models.ImageField("Фото первого экрана", upload_to="hero/", blank=True, validators=VALIDATORS)),
        migrations.AlterField(
            model_name="service", name="image",
            field=models.ImageField("Главная фотография", upload_to="content/", blank=True, validators=VALIDATORS)),
        migrations.AlterField(
            model_name="project", name="image",
            field=models.ImageField("Главная фотография", upload_to="content/", blank=True, validators=VALIDATORS)),
        migrations.AlterField(
            model_name="article", name="image",
            field=models.ImageField("Главная фотография", upload_to="content/", blank=True, validators=VALIDATORS)),
        migrations.AlterField(
            model_name="projectimage", name="image",
            field=models.ImageField("Фото", upload_to="projects/", validators=VALIDATORS)),
    ]
