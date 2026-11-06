from django.db import models
from django.core.cache import cache
from django.utils import timezone

from accounts.scoping import AccountScopedModel
from accounts.storage import AccountUploadPath


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


class Log(AccountScopedModel):
    """
    Stores application logs from various sources (Telegram, Finalize, etc.)
    """
    
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    SOURCE_CHOICES = [
        ('telegram', 'Telegram'),
        ('finalize', 'Finalize'),
        ('price_publisher', 'Price Publisher'),
        ('template_editor', 'Template Editor'),
        ('external_api', 'External API'),
        ('system', 'System'),
        ('other', 'Other'),
    ]
    
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='system')
    message = models.TextField(verbose_name="Message")
    details = models.TextField(blank=True, null=True, verbose_name="Additional Details")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name="User"
    )
    
    class Meta:
        verbose_name = "Log"
        verbose_name_plural = "Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['level', '-created_at']),
            models.Index(fields=['source', '-created_at']),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.source} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"


class SiteSettings(AccountScopedModel):
    """Branding and contact information, one row per customer account.

    Was a strict singleton pinned to ``pk=1``. With several customers sharing
    one deployment each needs its own branding, so the row is now per account
    and ``load()`` resolves the right one from the request context. Operators a
    desk owns resolve to their owner's account, so a logo change reaches the
    whole team and stops there.

    ``account`` is NOT NULL since ``setting.0016``: there is no install-wide
    row. Somewhere with no desk in context — the login screen, the landing
    page, the owner console — ``load()`` hands back an unsaved default instead,
    so those surfaces render the shipped branding and nothing can accidentally
    save over "everyone".
    """

    site_name = models.CharField(max_length=100, default="Sarafi Pardis")
    tagline = models.CharField(max_length=200, default="Premium Exchange Panel")
    logo = models.ImageField(upload_to=AccountUploadPath("branding"), null=True, blank=True)
    favicon = models.ImageField(upload_to=AccountUploadPath("branding"), null=True, blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    support_email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    office_map_url = models.URLField(
        blank=True,
        help_text="Google Maps or similar URL for office location (used in Telegram captions)",
    )
    business_hours = models.TextField(
        blank=True,
        default="دوشنبه تا شنبه: 9:30 صبح تا ۱۷\nیکشنبه ها: تعطیل",
        help_text="Business hours text (Persian/English) for Telegram captions",
    )
    support_phone_2 = models.CharField(max_length=30, blank=True)
    support_phone_3 = models.CharField(max_length=30, blank=True)
    base_currency_code = models.CharField(max_length=10, default="USD")
    telegram_link = models.URLField(blank=True)
    instagram_link = models.URLField(blank=True)
    twitter_link = models.URLField(blank=True)
    linkedin_link = models.URLField(blank=True)
    auto_post_on_update = models.BooleanField(
        default=False,
        help_text=(
            "If enabled, finalized prices can be auto-posted when updates occur. "
            "A scheduler must read this flag and trigger publishing."
        ),
    )
    use_template_editor_for_boards = models.BooleanField(
        default=False,
        help_text=(
            "If enabled, category/tether/special price boards use template_editor Template "
            "and render_price_template instead of legacy renderers."
        ),
    )
    use_playwright_for_template_render = models.BooleanField(
        default=False,
        help_text=(
            "If enabled, Telegram template boards are rendered via headless Vue screenshot "
            "(Playwright). Falls back to Pillow on error."
        ),
    )
    upload_max_file_size_mb = models.PositiveIntegerField(
        default=5,
        help_text="Maximum upload size in MB for managed uploads.",
    )
    upload_allowed_formats = models.JSONField(
        default=list,
        blank=True,
        help_text="Allowed upload formats list, e.g. ['PNG', 'JPG', 'SVG'].",
    )
    ui_font_filename_rtl = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional .ttf/.otf filename under static/fonts for RTL UI (Persian). Empty = default stack.",
    )
    ui_font_filename_ltr = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional .ttf/.otf filename under static/fonts for LTR UI. Empty = default stack.",
    )
    prices_webhook_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="If set, the panel POSTs a JSON prices snapshot to this URL after each price update.",
    )
    telegram_webhook_base_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text=(
            "Public HTTPS origin for customer-bot webhooks "
            "(e.g. https://panel.example.com). When set, active bots can register "
            "/api/telegram/webhook/<bot_id>/ with Telegram."
        ),
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete("site_settings")

    @classmethod
    def load(cls, account=None):
        """The settings row for ``account``, or for the account in context.

        Pass ``account`` explicitly from anywhere without a request — Celery
        tasks, the publish pipeline, management commands — since the context
        variable is empty there and would otherwise resolve to the install
        default rather than the customer's own branding.
        """
        from accounts.scoping import UNSCOPED, get_current_account_id

        if account is None:
            account_id = get_current_account_id()
            if account_id in (None, UNSCOPED):
                account_id = None
        else:
            account_id = getattr(account, "pk", account)

        if account_id is None:
            # No desk in context — the owner console, a management command, a
            # public page on an install with several customers. There is no row
            # to own these settings, so hand back an unsaved default rather than
            # inventing an account-less one that every scoped query would hide.
            return cls()

        # Do not cache ORM instances: pickled/stale cache entries break after schema
        # changes (e.g. new fields) and can cause 500s on endpoints that read flags
        # like auto_post_on_update. Fresh DB read is cheap for a single row.
        obj, _ = cls.all_objects.get_or_create(account_id=account_id)
        return obj



class SupportChannel(models.Model):
    """A way for customers to reach the people who run this install.

    Deliberately a table rather than more columns on ``SiteSettings``: the
    owner adds and removes numbers, handles and inboxes over time, and every
    surface that offers help — the panel footer, the expired-trial wall, the
    onboarding tour, the error pages, the marketing site — renders whatever is
    active right now without a redeploy.
    """

    KIND_PHONE = "phone"
    KIND_WHATSAPP = "whatsapp"
    KIND_TELEGRAM = "telegram"
    KIND_EMAIL = "email"
    KIND_INSTAGRAM = "instagram"
    KIND_CUSTOM = "custom"

    KIND_CHOICES = (
        (KIND_PHONE, "Phone"),
        (KIND_WHATSAPP, "WhatsApp"),
        (KIND_TELEGRAM, "Telegram"),
        (KIND_EMAIL, "Email"),
        (KIND_INSTAGRAM, "Instagram"),
        (KIND_CUSTOM, "Custom"),
    )

    # Font Awesome class per kind, so the panel and the landing page show the
    # same icon without either hardcoding a mapping.
    DEFAULT_ICONS = {
        KIND_PHONE: "fas fa-phone",
        KIND_WHATSAPP: "fab fa-whatsapp",
        KIND_TELEGRAM: "fab fa-telegram",
        KIND_EMAIL: "fas fa-envelope",
        KIND_INSTAGRAM: "fab fa-instagram",
        KIND_CUSTOM: "fas fa-headset",
    }

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_PHONE)
    label = models.CharField(
        max_length=120,
        help_text="Shown to the customer, e.g. 'Sales' or 'Technical support'",
    )
    value = models.CharField(
        max_length=255,
        help_text="Phone number, @handle, email address or URL",
    )
    icon = models.CharField(
        max_length=64,
        blank=True,
        help_text="Font Awesome class; falls back to the icon for this kind",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Support Channel"
        verbose_name_plural = "Support Channels"

    def __str__(self):
        return f"{self.get_kind_display()}: {self.label}"

    @property
    def display_icon(self):
        return self.icon or self.DEFAULT_ICONS.get(self.kind, "fas fa-headset")

    @property
    def href(self):
        """A clickable target, or empty when the value is not linkable."""
        value = (self.value or "").strip()
        if not value:
            return ""
        if self.kind == self.KIND_PHONE:
            return f"tel:{value.replace(' ', '')}"
        if self.kind == self.KIND_EMAIL:
            return f"mailto:{value}"
        if self.kind == self.KIND_WHATSAPP:
            digits = "".join(ch for ch in value if ch.isdigit())
            return f"https://wa.me/{digits}" if digits else ""
        if self.kind == self.KIND_TELEGRAM:
            if value.startswith("http"):
                return value
            return f"https://t.me/{value.lstrip('@')}"
        if self.kind == self.KIND_INSTAGRAM:
            if value.startswith("http"):
                return value
            return f"https://instagram.com/{value.lstrip('@')}"
        return value if value.startswith("http") else ""
