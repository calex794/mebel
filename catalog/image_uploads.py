"""Validation for photographs submitted through the admin panel."""

from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE = 12 * 1024 * 1024


def validate_image_size(image):
    """Keep accidental full-resolution uploads from overwhelming the site."""
    if image and image.size > MAX_IMAGE_SIZE:
        raise ValidationError("Фотография слишком большая: максимум 12 МБ.")
