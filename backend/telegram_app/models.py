from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from category.models import Category
from special_price.models import SpecialPriceType
from core.encryption import decrypt_token, encrypt_token

from accounts.scoping import AccountScopedModel, RelatedScopedManager


class TelegramBot(AccountScopedModel):
    """Model representing a Telegram bot."""

    name = models.CharField(
        max_length=100,
        verbose_name="Bot Name",
        help_text="A friendly name for this bot",
    )
    token = models.CharField(
        max_length=500,
        verbose_name="Bot Token",
        help_text="Telegram bot token from @BotFather (encrypted at rest)",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_bots",
        verbose_name="Owner",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Whether this bot is currently active",
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Display Name",
        help_text="Optional friendly display name",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Optional security or usage notes",
    )
    restrict_to_known_channels = models.BooleanField(
        default=False,
        verbose_name="Restrict to known channels",
        help_text="If set, only allow sending to channels registered in this panel",
    )
    log_all_messages = models.BooleanField(
        default=False,
        verbose_name="Log all messages",
        help_text="If set, log all messages sent via this bot",
    )
    default_exchange_ttl_minutes = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        verbose_name="Default exchange TTL (minutes)",
        help_text="TTL applied to new exchange requests from this bot. End-users cannot change it.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
    )

    class Meta:
        verbose_name = "Telegram Bot"
        verbose_name_plural = "Telegram Bots"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def _scope_account_id(self):
        # Stamp the owning desk's account so a bot created from a request-less
        # path (registration task, webhook, test) still lands on the right desk.
        owner = self.owner
        if owner is not None:
            return owner.account_id
        return None

    def get_plain_token(self):
        decrypted = decrypt_token(self.token)
        return decrypted or self.token

    def save(self, *args, **kwargs):
        if self.token and not str(self.token).startswith("gAAAAA"):
            self.token = encrypt_token(self.token)
        super().save(*args, **kwargs)


class TelegramChannel(models.Model):
    """Model representing a Telegram channel."""

    bot = models.ForeignKey(
        TelegramBot,
        on_delete=models.CASCADE,
        related_name="channels",
        verbose_name="Bot",
        help_text="The bot used to send messages to this channel",
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Channel Name",
        help_text="A friendly name for this channel",
    )
    chat_id = models.CharField(
        max_length=50,
        verbose_name="Chat ID",
        help_text="Telegram channel chat ID (e.g., @channelname or -1001234567890)",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Whether this channel is currently active",
    )
    last_member_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Last Member Count",
        help_text="Cached subscriber count from the latest snapshot job.",
    )
    last_member_sampled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Member Sampled At",
    )
    bot_admin_verified = models.BooleanField(
        default=False,
        verbose_name="Bot Admin Verified",
        help_text="Whether the bot was an administrator at the last snapshot.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
    )

    objects = RelatedScopedManager("bot__account_id")
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Telegram Channel"
        verbose_name_plural = "Telegram Channels"
        ordering = ["-created_at"]
        unique_together = ["bot", "chat_id"]

    def __str__(self):
        return f"{self.name} ({self.chat_id})"


class DefaultMessageSettings(models.Model):
    """Defines default caption and buttons per bot for rendered messages."""

    bot = models.ForeignKey(
        TelegramBot,
        on_delete=models.CASCADE,
        related_name="message_settings",
        verbose_name="Bot",
    )
    default_caption = models.TextField(
        blank=True,
        verbose_name="Default Caption",
        help_text="Optional caption appended to generated messages.",
    )
    default_buttons = models.JSONField(
        blank=True,
        default=list,
        verbose_name="Default Buttons",
        help_text="JSON structure describing inline buttons. Example: "
        '[{"text": "View", "url": "https://example.com"}]',
    )
    active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Only one setting can be active per bot.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    objects = RelatedScopedManager("bot__account_id")
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Default Message Setting"
        verbose_name_plural = "Default Message Settings"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["bot"],
                condition=Q(active=True),
                name="unique_active_message_settings_per_bot",
            )
        ]

    def clean(self):
        super().clean()
        if self.active:
            conflict = (
                DefaultMessageSettings.objects.filter(bot=self.bot, active=True)
                .exclude(pk=self.pk)
                .exists()
            )
            if conflict:
                raise ValidationError(
                    {"active": "Another active setting already exists for this bot."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.active:
            (
                DefaultMessageSettings.objects.filter(bot=self.bot, active=True)
                .exclude(pk=self.pk)
                .update(active=False)
            )

    def __str__(self):
        status = "active" if self.active else "inactive"
        return f"{self.bot} ({status})"
