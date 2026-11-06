from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from category.models import Currency

from accounts.scoping import AccountScopedModel, RelatedScopedManager


class SpecialPriceType(AccountScopedModel):
    """
    Special Price Type model - no category required.
    Example: "Special Price: Pound"
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    # Currency pair and trade direction
    source_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='special_price_types_source')
    target_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='special_price_types_target')
    TRADE_CHOICES = (
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    )
    trade_type = models.CharField(max_length=10, choices=TRADE_CHOICES)
    is_double_price = models.BooleanField(
        default=False,
        help_text="If True, this type uses two prices (Cash and Account) on one banner.",
    )
    description = models.TextField(blank=True, null=True)
    # Optional Font Awesome icon class for UI highlight (e.g. "fas fa-star", "fas fa-shield-alt")
    icon = models.CharField(max_length=64, blank=True, null=True)
    last_used_template = models.ForeignKey(
        "template_editor.Template",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Last template used for Telegram finalize (round-robin among active templates).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Special Price Type"
        verbose_name_plural = "Special Price Types"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["account", "name"], name="uniq_spt_name_per_account"),
            models.UniqueConstraint(fields=["account", "slug"], name="uniq_spt_slug_per_account"),
        ]

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


class SpecialPricePair(models.Model):
    TRADE_CHOICES = (
        ("buy", "Buy"),
        ("sell", "Sell"),
    )

    special_price_type = models.ForeignKey(
        SpecialPriceType,
        on_delete=models.CASCADE,
        related_name="pairs",
    )
    name = models.CharField(max_length=150)
    source_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="special_price_pairs_source",
    )
    target_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="special_price_pairs_target",
    )
    trade_type = models.CharField(max_length=10, choices=TRADE_CHOICES, default="buy")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RelatedScopedManager("special_price_type__account_id")
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Special Price Pair"
        verbose_name_plural = "Special Price Pairs"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["special_price_type", "source_currency", "target_currency", "trade_type"],
                name="uniq_special_price_pair_per_type",
            )
        ]

    def __str__(self):
        return f"{self.special_price_type.name}: {self.name}"


class SpecialPriceHistory(models.Model):
    special_price_type = models.ForeignKey(
        SpecialPriceType,
        on_delete=models.CASCADE,
        related_name="special_price_histories",
    )
    pair = models.ForeignKey(
        SpecialPricePair,
        on_delete=models.CASCADE,
        related_name="histories",
    )
    price = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])
    cash_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Cash price (نقدی); used when special_price_type.is_double_price is True.",
    )
    account_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Account price (حسابی); used when special_price_type.is_double_price is True.",
    )
    event_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

    objects = RelatedScopedManager("special_price_type__account_id")
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Special Price History"
        verbose_name_plural = "Special Price Histories"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.special_price_type.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
