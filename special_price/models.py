from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from category.models import Currency


class SpecialPriceType(models.Model):
    """
    Special Price Type model - no category required.
    Example: "Special Price: Pound"
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, blank=True, unique=True)
    # Currency pair and trade direction
    source_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='special_price_types_source')
    target_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='special_price_types_target')
    TRADE_CHOICES = (
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    )
    trade_type = models.CharField(max_length=10, choices=TRADE_CHOICES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Special Price Type"
        verbose_name_plural = "Special Price Types"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'special-price-type'
            slug = base_slug
            counter = 1
            while SpecialPriceType.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SpecialPriceHistory(models.Model):
    special_price_type = models.ForeignKey(SpecialPriceType, on_delete=models.CASCADE, related_name='special_price_histories')
    price = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Special Price History"
        verbose_name_plural = "Special Price Histories"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.special_price_type.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
