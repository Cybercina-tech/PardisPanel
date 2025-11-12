from django.db import models
from django.core.validators import MinValueValidator
from category.models import PriceType


class PriceHistory(models.Model):
    price_type = models.ForeignKey(PriceType, on_delete=models.CASCADE, related_name='price_histories')
    price = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Price History"
        verbose_name_plural = "Price Histories"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.price_type.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"