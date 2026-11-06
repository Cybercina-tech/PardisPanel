from django.db import models
from django.core.validators import MinValueValidator

from accounts.scoping import RelatedScopedManager
from category.models import PriceType


class PriceHistory(models.Model):
    price_type = models.ForeignKey(PriceType, on_delete=models.CASCADE, related_name='price_histories')
    price = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])
    # Optional backdated event time (e.g. Excel import). Charts use Coalesce(event_at, created_at).
    event_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

    objects = RelatedScopedManager("price_type__category__account_id")
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Price History"
        verbose_name_plural = "Price Histories"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.price_type.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"