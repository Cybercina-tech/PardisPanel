from django.core.files.storage import default_storage
from rest_framework import serializers

from accounts.permissions import IsSuperAdmin
from core.utils import validate_uploaded_image, MAX_IMAGE_SIZE
from template_editor.utils import get_available_fonts
from .models import SiteSettings, Log, SupportChannel


class SafeImageField(serializers.ImageField):
    """
    Serialize ImageField URLs only when the underlying file exists in storage.

    Default DRF ImageField calls ``value.url`` before we can null out stale DB paths; some
    storages or absolute-URI building can raise when media was wiped (e.g. Docker volumes).
    """

    def to_representation(self, value):
        if not value:
            return None
        path = getattr(value, "name", None)
        if not path:
            return None
        try:
            if not default_storage.exists(path):
                return None
        except Exception:
            return None
        try:
            url = value.url
        except Exception:
            return None
        request = self.context.get("request", None)
        if request is not None:
            try:
                return request.build_absolute_uri(url)
            except Exception:
                return url
        return url
from telegram_app.models import TelegramBot, TelegramChannel

CANONICAL_BASE_CURRENCIES = {
    "USD", "USDT", "BTC", "ETH", "BNB", "EUR", "GBP", "AUD", "CAD", "CHF", "CNY", "TRY",
    "IRR", "IRT", "AED", "JPY", "RUB", "IQD", "XAU",
}
UPLOAD_FORMAT_CHOICES = {"PNG", "JPG", "SVG", "GIF", "WEBP", "JPEG"}


class SupportChannelSerializer(serializers.ModelSerializer):
    icon = serializers.CharField(source="display_icon", read_only=True)
    href = serializers.CharField(read_only=True)

    class Meta:
        model = SupportChannel
        fields = ["id", "kind", "label", "value", "icon", "href", "is_active", "sort_order"]


class SiteSettingsSerializer(serializers.ModelSerializer):
    logo = SafeImageField(allow_null=True, required=False)
    favicon = SafeImageField(allow_null=True, required=False)
    # Read-only here: the owner console is the only place they are edited, but
    # every public surface reads them from this one endpoint.
    support_channels = serializers.SerializerMethodField()
    # Public by design — it identifies the app to Google, it is not a secret —
    # and empty when the install has no client id, which is how the login page
    # knows whether to render the button at all.
    google_client_id = serializers.SerializerMethodField()
    signup_enabled = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = [
            "site_name",
            "tagline",
            "logo",
            "favicon",
            "support_phone",
            "support_phone_2",
            "support_phone_3",
            "base_currency_code",
            "support_email",
            "address",
            "office_map_url",
            "business_hours",
            "telegram_link",
            "instagram_link",
            "twitter_link",
            "linkedin_link",
            "auto_post_on_update",
            "use_template_editor_for_boards",
            "use_playwright_for_template_render",
            "ui_font_filename_rtl",
            "ui_font_filename_ltr",
            "prices_webhook_url",
            "telegram_webhook_base_url",
            "support_channels",
            "google_client_id",
            "signup_enabled",
        ]

    def get_support_channels(self, obj):
        from .support import support_channel_payload

        return support_channel_payload()

    def get_google_client_id(self, obj):
        from django.conf import settings as django_settings

        return getattr(django_settings, "GOOGLE_OAUTH_CLIENT_ID", "")

    def get_signup_enabled(self, obj):
        from django.conf import settings as django_settings

        return bool(getattr(django_settings, "SIGNUP_ENABLED", True))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        perm = IsSuperAdmin()
        if not (request is not None and perm.has_permission(request, self)):
            data.pop("prices_webhook_url", None)
            data.pop("telegram_webhook_base_url", None)
        return data

    def validate_prices_webhook_url(self, value):
        s = str(value or "").strip()
        return s

    def validate_telegram_webhook_base_url(self, value):
        return str(value or "").strip()

    def validate_base_currency_code(self, value):
        code = str(value or "").upper().strip()
        if code not in CANONICAL_BASE_CURRENCIES:
            raise serializers.ValidationError("Unsupported base currency code.")
        return code

    def validate_logo(self, value):
        if value and hasattr(value, "read"):
            try:
                validate_uploaded_image(value, max_size=MAX_IMAGE_SIZE)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        return value

    def validate_favicon(self, value):
        if value and hasattr(value, "read"):
            try:
                validate_uploaded_image(value, max_size=MAX_IMAGE_SIZE)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        return value

    def _validate_ui_font_filename(self, value):
        s = str(value or "").strip()
        if not s:
            return ""
        allowed = {fn for fn, _ in get_available_fonts()}
        if s not in allowed:
            raise serializers.ValidationError("Font file is not available on the server.")
        return s

    def validate_ui_font_filename_rtl(self, value):
        return self._validate_ui_font_filename(value)

    def validate_ui_font_filename_ltr(self, value):
        return self._validate_ui_font_filename(value)


class TelegramBotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramBot
        fields = ["id", "name", "token", "is_active", "created_at", "updated_at"]


class TelegramChannelSerializer(serializers.ModelSerializer):
    bot_name = serializers.CharField(source="bot.name", read_only=True)

    class Meta:
        model = TelegramChannel
        fields = [
            "id",
            "bot",
            "bot_name",
            "name",
            "chat_id",
            "is_active",
            "created_at",
            "updated_at",
        ]


class LogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = Log
        fields = [
            "id",
            "level",
            "source",
            "message",
            "details",
            "created_at",
            "user",
            "username",
        ]


class UploadPolicySerializer(serializers.Serializer):
    max_file_size_mb = serializers.IntegerField(min_value=1, max_value=50)
    allowed_formats = serializers.ListField(
        child=serializers.CharField(max_length=10),
        allow_empty=False,
    )

    def validate_allowed_formats(self, value):
        normalized = []
        for fmt in value:
            key = str(fmt or "").strip().upper()
            if key == "JPEG":
                key = "JPG"
            if key not in UPLOAD_FORMAT_CHOICES:
                raise serializers.ValidationError(f"Unsupported format: {fmt}")
            if key not in normalized:
                normalized.append(key)
        if not normalized:
            raise serializers.ValidationError("At least one format must be selected.")
        return normalized
