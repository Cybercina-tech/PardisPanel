from django.db import models
from django.utils.text import slugify

from accounts.scoping import AccountScopedModel, RelatedScopedManager


class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'

    def __str__(self):
        return f"{self.code} ({self.symbol})" if self.symbol else self.code


class Category(AccountScopedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    description = models.TextField(blank=True, null=True)
    # Telegram message content for this category
    telegram_message_description = models.TextField(blank=True, null=True)
    telegram_media_url = models.URLField(max_length=500, blank=True)
    inline_buttons = models.JSONField(default=list, blank=True)  # [{"label": "...", "url": "..."}]
    last_used_template = models.ForeignKey(
        "template_editor.Template",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Last template_editor.Template used for round-robin price image publishing.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["account", "name"], name="uniq_category_name_per_account"),
            models.UniqueConstraint(fields=["account", "slug"], name="uniq_category_slug_per_account"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True) or "category"
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
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RelatedScopedManager("category__account_id")
    all_objects = models.Manager()

    class Meta:
        verbose_name = "PriceType"
        verbose_name_plural = "PriceTypes"
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['category', 'name'], name='unique_category_pricetype_name'),
        ]

    def save(self, *args, **kwargs):
        # Ensure slug is unique within the same category
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True) or 'pricetype'
            slug = base_slug
            counter = 1
            while PriceType.objects.filter(category=self.category, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"
