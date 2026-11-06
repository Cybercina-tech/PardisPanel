from rest_framework import serializers

from accounts.relations import ScopedPrimaryKeyRelatedField

from .models import (
    DefaultMessageSettings,
    TelegramBot,
    TelegramChannel,
)
from .services.telegram_token import is_valid_botfather_token


class TelegramBotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramBot
        fields = [
            "id",
            "name",
            "display_name",
            "notes",
            "is_active",
            "restrict_to_known_channels",
            "log_all_messages",
            "default_exchange_ttl_minutes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TelegramBotDetailSerializer(serializers.ModelSerializer):
    """Full serializer for create/update - includes token."""

    class Meta:
        model = TelegramBot
        fields = [
            "id",
            "name",
            "token",
            "display_name",
            "notes",
            "is_active",
            "restrict_to_known_channels",
            "log_all_messages",
            "default_exchange_ttl_minutes",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "token": {"write_only": True, "required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None and not (attrs.get("token") or "").strip():
            raise serializers.ValidationError({"token": "Bot token is required."})
        return attrs

    def validate_token(self, value):
        token = (value or "").strip()
        if not token:
            return value
        # A malformed token is stored happily and then fails silently forever:
        # getMe never succeeds and the bot answers nothing. Catch it at entry.
        if not is_valid_botfather_token(token):
            raise serializers.ValidationError(
                "That does not look like a BotFather token. Expected the form "
                "123456789:AA... exactly as @BotFather sent it."
            )
        others = TelegramBot.objects.all()
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        for other in others:
            if (other.get_plain_token() or "").strip() == token:
                raise serializers.ValidationError(
                    f"This token is already used by bot id={other.pk} ({other.name}). "
                    "Each Telegram bot needs its own token from @BotFather."
                )
        return value

    def update(self, instance, validated_data):
        token = validated_data.pop("token", None)
        if token:
            validated_data["token"] = token
        return super().update(instance, validated_data)


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
            "bot_admin_verified",
            "last_member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["bot_admin_verified", "last_member_count"]


class SendMessageSerializer(serializers.Serializer):
    bot_id = ScopedPrimaryKeyRelatedField(
        queryset=lambda: TelegramBot.objects.filter(is_active=True), write_only=True
    )
    channel_id = ScopedPrimaryKeyRelatedField(
        # Channels scope through their bot, which is the account-owning root.
        queryset=lambda: TelegramChannel.objects.filter(
            is_active=True, bot__is_active=True, bot__in=TelegramBot.objects.all()
        ),
        write_only=True,
    )
    message = serializers.CharField(
        max_length=4096, trim_whitespace=False, required=False, allow_blank=True
    )
    banner_key = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    cash_price = serializers.DecimalField(
        max_digits=20, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    account_price = serializers.DecimalField(
        max_digits=20, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    price = serializers.DecimalField(
        max_digits=20, decimal_places=2, min_value=0, required=False, allow_null=True
    )

    def validate_message(self, value):
        if value is None:
            return ""
        return value or ""

    def validate(self, attrs):
        channel = attrs["channel_id"]
        bot = attrs["bot_id"]
        if channel.bot_id != bot.id:
            raise serializers.ValidationError(
                {"channel_id": "Channel does not belong to the selected bot."}
            )
        attrs["bot"] = bot
        attrs["channel"] = channel
        message = (attrs.get("message") or "").strip()
        banner_key = (attrs.get("banner_key") or "").strip()
        cash = attrs.get("cash_price")
        account = attrs.get("account_price")
        single = attrs.get("price")
        has_banner = banner_key and banner_key != "none"
        has_double = cash is not None or account is not None
        has_single = single is not None
        if not message and not has_banner and not has_double and not has_single:
            raise serializers.ValidationError(
                {"message": "Provide message text and/or banner/prices."}
            )
        return attrs


class DefaultMessageSettingsSerializer(serializers.ModelSerializer):
    bot_name = serializers.CharField(source="bot.name", read_only=True)

    class Meta:
        model = DefaultMessageSettings
        fields = [
            "id",
            "bot",
            "bot_name",
            "default_caption",
            "default_buttons",
            "active",
            "created_at",
            "updated_at",
        ]
