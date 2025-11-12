from django.db import models


class PriceThemeState(models.Model):
    """
    Tracks the last price theme index used when rendering channel images.

    A single row with key ``price_theme`` is created automatically and updated
    each time a new image is rendered so that themes cycle through sequentially.
    """

    key = models.CharField(max_length=50, unique=True)
    last_index = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Price Theme State"
        verbose_name_plural = "Price Theme States"

    @classmethod
    def get_or_create_theme_state(cls):
        return cls.objects.get_or_create(key="price_theme", defaults={"last_index": 0})

