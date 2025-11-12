from django.db import models
from django.utils.text import slugify


class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'

    def __str__(self):
        return f"{self.code} ({self.symbol})" if self.symbol else self.code


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "category"
            slug = base_slug
            counter = 1

            # Loop until we find a unique slug
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



class PriceType(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='price_types')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    # Currency pair and trade direction
    source_currency = models.ForeignKey('Currency', on_delete=models.PROTECT, related_name='+')
    target_currency = models.ForeignKey('Currency', on_delete=models.PROTECT, related_name='+')
    TRADE_CHOICES = (
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    )
    trade_type = models.CharField(max_length=10, choices=TRADE_CHOICES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "PriceType"
        verbose_name_plural = "PriceTypes"
        ordering = ['name']
        # Only name should be unique within a category
        constraints = [
            models.UniqueConstraint(fields=['category', 'name'], name='unique_category_pricetype_name'),
        ]

    def save(self, *args, **kwargs):
        # Ensure slug is unique within the same category
        if not self.slug:
            base_slug = slugify(self.name) or 'pricetype'
            slug = base_slug
            counter = 1
            while PriceType.objects.filter(category=self.category, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"
