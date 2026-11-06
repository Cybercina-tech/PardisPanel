"""
DRF API views for Telegram app: channels, send message, default settings, bots,
and auto-post configuration.
"""
import json
from django.db.models import Count
from rest_framework import status, serializers as drf_serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework.exceptions import MethodNotAllowed, NotFound, PermissionDenied, ValidationError
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action

from .models import (
    DefaultMessageSettings,
    TelegramBot,
    TelegramChannel,
)
from .ownership import (
    bots_queryset_for_user,
    resolve_bot_for_user,
    user_is_super_admin,
)
from .services.telegram_client import TelegramService
from setting.utils import (
    log_telegram_event,
    read_auto_post_on_update_safe,
    write_auto_post_on_update_safe,
)
from core.exceptions import error_response
from .serializers import (
    DefaultMessageSettingsSerializer,
    SendMessageSerializer,
    TelegramBotDetailSerializer,
    TelegramBotSerializer,
    TelegramChannelSerializer,
)


class TelegramChannelListAPIView(APIView):
    """GET /api/telegram/channels/ - list active channels with their bots."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        channels = (
            TelegramChannel.objects.filter(
                is_active=True,
                bot__is_active=True,
                bot_id__in=bots_queryset_for_user(request.user).values("id"),
            )
            .select_related("bot")
            .order_by("-created_at")
        )
        serializer = TelegramChannelSerializer(channels, many=True)
        return Response(serializer.data)


class SendMessageAPIView(APIView):
    """POST /api/telegram/send-message/ - send a message to a channel."""

    permission_classes = [IsAuthenticated]

    def _build_message_from_payload(self, data):
        """Build message text from banner_key and price fields when provided."""
        banner_key = (data.get("banner_key") or "").strip()
        if not banner_key or banner_key == "none":
            return (data.get("message") or "").strip()

        parts = []
        if banner_key == "buy_gbp_double" or banner_key == "sell_gbp_double":
            cash = data.get("cash_price")
            account = data.get("account_price")
            if cash is not None:
                parts.append(f"Cash: {cash}")
            if account is not None:
                parts.append(f"Account: {account}")
            label = "Buy GBP" if banner_key == "buy_gbp_double" else "Sell GBP"
            if parts:
                parts.insert(0, label)
        else:
            single = data.get("price")
            if single is not None:
                parts.append(f"Price: {single}")
            if banner_key == "generic_single" and parts:
                parts.insert(0, "Price update")

        custom = (data.get("message") or "").strip()
        if custom:
            parts.append(custom)
        return "\n".join(parts) if parts else custom

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        bot = data["bot"]
        channel = data["channel"]
        message = self._build_message_from_payload(data)
        if not message:
            message = (request.data.get("message") or "").strip() or "—"

        if channel.bot_id != bot.id:
            return error_response(
                "Channel does not belong to the selected bot.",
                code="telegram_channel_bot_mismatch",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            client = TelegramService(bot.get_plain_token())
            success, response, _ = client.send_message(channel.chat_id, message)

            if success:
                log_telegram_event(
                    level="INFO",
                    message="Message sent via API",
                    details={
                        "event": "api_send_message",
                        "bot_id": bot.id,
                        "bot_name": bot.name,
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                        "chat_id": str(channel.chat_id),
                        "message_length": len(message),
                    },
                    user=request.user,
                )
                return Response({"success": True, "detail": response})
            return Response(
                {"success": False, "detail": response},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            log_telegram_event(
                level="ERROR",
                message="Exception sending message via API",
                details={
                    "event": "api_send_message_error",
                    "bot_id": bot.id,
                    "channel_id": channel.id,
                    "error": str(e),
                },
                user=request.user,
            )
            return error_response(
                "Could not send Telegram message.",
                code="telegram_send_failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                extra={"success": False, "detail": str(e)},
            )


class DefaultMessageSettingsListAPIView(APIView):
    """GET /api/telegram/default-settings/ - list default settings (optionally by bot)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        bot_id = request.query_params.get("bot")
        qs = DefaultMessageSettings.objects.select_related("bot").filter(
            bot_id__in=bots_queryset_for_user(request.user).values("id")
        ).order_by("-updated_at")
        if bot_id:
            qs = qs.filter(bot_id=bot_id)
        serializer = DefaultMessageSettingsSerializer(qs, many=True)
        return Response(serializer.data)


class DefaultMessageSettingsDetailAPIView(APIView):
    """GET/PUT /api/telegram/default-settings/<id>/ - get or update a default setting."""

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        from django.shortcuts import get_object_or_404

        return get_object_or_404(DefaultMessageSettings, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        serializer = DefaultMessageSettingsSerializer(obj)
        return Response(serializer.data)

    def put(self, request, pk):
        obj = self.get_object(pk)
        serializer = DefaultMessageSettingsSerializer(
            obj, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        default_buttons = request.data.get("default_buttons")
        if default_buttons is not None:
            if isinstance(default_buttons, str):
                try:
                    default_buttons = json.loads(default_buttons)
                except json.JSONDecodeError:
                    return error_response(
                        "Invalid JSON.",
                        code="invalid_json",
                        status_code=status.HTTP_400_BAD_REQUEST,
                        errors={"default_buttons": "Invalid JSON."},
                    )
            serializer.validated_data["default_buttons"] = default_buttons

        serializer.save()
        return Response(serializer.data)


class DefaultMessageSettingsCreateAPIView(APIView):
    """POST /api/telegram/default-settings/ - create default settings for a bot."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = dict(request.data)
        default_buttons = data.get("default_buttons")
        if default_buttons is not None and isinstance(default_buttons, str):
            try:
                data["default_buttons"] = json.loads(default_buttons)
            except json.JSONDecodeError:
                return error_response(
                    "Invalid JSON.",
                    code="invalid_json",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    errors={"default_buttons": "Invalid JSON."},
                )

        serializer = DefaultMessageSettingsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TelegramBotViewSet(ModelViewSet):
    """
    CRUD for Telegram bots.

    List/retrieve operations hide the token; create/update use the detail serializer.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return bots_queryset_for_user(self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TelegramBotDetailSerializer
        return TelegramBotSerializer

    def perform_create(self, serializer):
        # Whoever connects the bot owns it. ``primary_owned_bot`` and the
        # "bot connected" flag on /auth/me both read this FK, so leaving it
        # null for non-management roles made a freshly added bot look absent.
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        """
        POST /api/telegram/bots/<id>/test-connection/

        The thing under test is the *token*, so this always calls getMe. A
        channel is optional extra reach: given an explicit `chat_id`, or with
        one active channel on file, a test message is sent too. A bot with no
        channel yet is the normal first-run state, not a failed connection.
        """
        bot = self.get_object()
        chat_id = request.data.get("chat_id")
        explicit_chat = bool(chat_id)
        if not chat_id:
            channel = bot.channels.filter(is_active=True).first()
            chat_id = channel.chat_id if channel else None

        try:
            token = bot.get_plain_token()
            if not token:
                return error_response(
                    "Bot has no token configured.",
                    code="no_token",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    extra={"success": False},
                )

            client = TelegramService(token)
            ok, info, err = client.get_me()
            if not ok:
                log_telegram_event(
                    level="WARNING",
                    message="Bot test-connection getMe failed",
                    details={
                        "event": "bot_test_connection",
                        "bot_id": bot.id,
                        "bot_name": bot.name,
                        "stage": "get_me",
                        "success": False,
                    },
                    user=request.user,
                )
                return error_response(
                    err or "Telegram rejected this bot token.",
                    code="get_me_failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    extra={"success": False, "detail": err},
                )

            username = (info or {}).get("username") or ""
            identity = f"@{username}" if username else bot.name
            if chat_id is None:
                log_telegram_event(
                    level="INFO",
                    message="Bot test-connection executed",
                    details={
                        "event": "bot_test_connection",
                        "bot_id": bot.id,
                        "bot_name": bot.name,
                        "chat_id": None,
                        "success": True,
                    },
                    user=request.user,
                )
                return Response(
                    {
                        "success": True,
                        "detail": (
                            f"Token is valid ({identity}). No active channel yet, "
                            "so no test message was sent."
                        ),
                        "telegram": info,
                        "channel_tested": False,
                    }
                )

            success, response, _ = client.send_message(
                chat_id, "✅ Test message from Telegram Management Hub"
            )
            log_telegram_event(
                level="INFO",
                message="Bot test-connection executed",
                details={
                    "event": "bot_test_connection",
                    "bot_id": bot.id,
                    "bot_name": bot.name,
                    "chat_id": str(chat_id),
                    "success": success,
                },
                user=request.user,
            )
            if success:
                return Response(
                    {
                        "success": True,
                        "detail": response,
                        "telegram": info,
                        "channel_tested": True,
                    }
                )
            # The token is good; only the channel leg failed. Say which, or the
            # operator re-pastes a token that was never the problem.
            return Response(
                {
                    "success": False,
                    "detail": (
                        f"Token is valid ({identity}), but sending to {chat_id} failed: "
                        f"{response}"
                    ),
                    "telegram": info,
                    "channel_tested": True,
                    "explicit_chat_id": explicit_chat,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            log_telegram_event(
                level="ERROR",
                message="Exception in bot test-connection",
                details={
                    "event": "bot_test_connection_error",
                    "bot_id": bot.id,
                    "error": str(exc),
                },
                user=request.user,
            )
            return error_response(
                "Bot connection test failed.",
                code="telegram_test_connection_failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                extra={"success": False, "detail": str(exc)},
            )


class TelegramChannelViewSet(ModelViewSet):
    """
    Full CRUD for Telegram channels (management).

    The existing TelegramChannelListAPIView continues to serve the simplified
    `/api/telegram/channels/` endpoint used by the finalize flows.
    """

    queryset = TelegramChannel.objects.select_related("bot").all().order_by(
        "-created_at"
    )
    serializer_class = TelegramChannelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            TelegramChannel.objects.filter(
                bot_id__in=bots_queryset_for_user(self.request.user).values("id")
            )
            .select_related("bot")
            .order_by("-created_at")
        )
