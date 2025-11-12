from django.db import models
from django.utils import timezone
from category.models import Category
from change_price.models import PriceHistory
from special_price.models import SpecialPriceHistory
from telegram_app.models import TelegramChannel


class Finalization(models.Model):
    """Tracks when a category's prices were finalized and published to Telegram."""
    
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='finalizations',
        verbose_name="Category"
    )
    channel = models.ForeignKey(
        TelegramChannel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finalizations',
        verbose_name="Telegram Channel",
        help_text="The channel where prices were published"
    )
    finalized_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Finalized At"
    )
    finalized_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finalizations',
        verbose_name="Finalized By"
    )
    message_sent = models.BooleanField(
        default=False,
        verbose_name="Message Sent",
        help_text="Whether the message was successfully sent to Telegram"
    )
    image_caption = models.TextField(
        blank=True,
        null=True,
        verbose_name="Image Caption",
        help_text="Caption sent alongside the rendered price image."
    )
    telegram_response = models.TextField(
        blank=True,
        null=True,
        verbose_name="Telegram Response",
        help_text="Raw response or error message returned by Telegram."
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes"
    )

    class Meta:
        verbose_name = "Finalization"
        verbose_name_plural = "Finalizations"
        ordering = ['-finalized_at']
        indexes = [
            models.Index(fields=['category', '-finalized_at']),
            models.Index(fields=['finalized_at']),
        ]

    def __str__(self):
        return f"{self.category.name} - {self.finalized_at.strftime('%Y-%m-%d %H:%M')}"


class FinalizedPriceHistory(models.Model):
    """Tracks which price history entries were included in each finalization."""
    
    finalization = models.ForeignKey(
        Finalization,
        on_delete=models.CASCADE,
        related_name='finalized_prices',
        verbose_name="Finalization"
    )
    price_history = models.ForeignKey(
        PriceHistory,
        on_delete=models.CASCADE,
        related_name='finalizations',
        verbose_name="Price History"
    )

    class Meta:
        verbose_name = "Finalized Price History"
        verbose_name_plural = "Finalized Price Histories"
        unique_together = ['finalization', 'price_history']
        indexes = [
            models.Index(fields=['finalization']),
            models.Index(fields=['price_history']),
        ]

    def __str__(self):
        return f"{self.finalization} - {self.price_history}"


class SpecialPriceFinalization(models.Model):
    """Tracks when a special price was finalized and published to Telegram."""
    
    special_price_history = models.ForeignKey(
        SpecialPriceHistory,
        on_delete=models.CASCADE,
        related_name='finalizations',
        verbose_name="Special Price History"
    )
    channel = models.ForeignKey(
        TelegramChannel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='special_price_finalizations',
        verbose_name="Telegram Channel",
        help_text="The channel where price was published"
    )
    finalized_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Finalized At"
    )
    finalized_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='special_price_finalizations',
        verbose_name="Finalized By"
    )
    message_sent = models.BooleanField(
        default=False,
        verbose_name="Message Sent",
        help_text="Whether the message was successfully sent to Telegram"
    )
    image_caption = models.TextField(
        blank=True,
        null=True,
        verbose_name="Image Caption",
        help_text="Caption sent alongside the rendered price image."
    )
    telegram_response = models.TextField(
        blank=True,
        null=True,
        verbose_name="Telegram Response",
        help_text="Raw response or error message returned by Telegram."
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes"
    )

    class Meta:
        verbose_name = "Special Price Finalization"
        verbose_name_plural = "Special Price Finalizations"
        ordering = ['-finalized_at']
        indexes = [
            models.Index(fields=['special_price_history', '-finalized_at']),
            models.Index(fields=['finalized_at']),
        ]

    def __str__(self):
        return f"{self.special_price_history.special_price_type.name} - {self.finalized_at.strftime('%Y-%m-%d %H:%M')}"
