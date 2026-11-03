from django.db import migrations, models
from django.core.validators import FileExtensionValidator
from catalog.image_uploads import validate_image_size

IMAGE_VALIDATORS = [FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_image_size]


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_landing_clarity_faq")]
    operations = [
        migrations.AlterField(
            model_name=name, name=field,
            field=models.ImageField(verbose_name=label, upload_to=directory, blank=blank, validators=IMAGE_VALIDATORS),
        )
        for name, field, label, directory, blank in [
            ("sitesettings", "hero_image", "Фото первого экрана", "hero/", True),
            ("service", "image", "Главная фотография", "content/", True),
            ("project", "image", "Главная фотография", "content/", True),
            ("article", "image", "Главная фотография", "content/", True),
            ("projectimage", "image", "Фото", "projects/", False),
        ]
    ]
