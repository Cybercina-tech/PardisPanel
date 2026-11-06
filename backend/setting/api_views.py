"""
DRF API views for settings: site settings, bots, channels, logs.
"""
import logging
import os
import shutil
from pathlib import Path

from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from accounts.permissions import IsProgrammer, IsSuperAdmin, IsSuperAdminOrManagement
from accounts.scoping import account_for_user
from core.exceptions import error_response
from telegram_app.models import TelegramBot, TelegramChannel

from .models import SiteSettings, Log, SupportChannel
from .serializers import (
    SiteSettingsSerializer,
    SupportChannelSerializer,
    TelegramBotSerializer,
    TelegramChannelSerializer,
    LogSerializer,
    UploadPolicySerializer,
)

logger = logging.getLogger(__name__)

DEFAULT_UPLOAD_STORAGE_LIMIT_GB = 10


def _upload_settings_fallback():
    limit_gb = int(os.environ.get("UPLOAD_STORAGE_LIMIT_GB", DEFAULT_UPLOAD_STORAGE_LIMIT_GB))
    total_bytes = max(limit_gb, 1) * (1024 ** 3)
    return {
        "max_file_size_mb": 5,
        "allowed_formats": ["PNG", "JPG"],
        "storage": {
            "used_bytes": 0,
            "total_bytes": total_bytes,
            "used_percent": 0,
            "used_human": _human_gb(0),
            "total_human": f"{limit_gb} GB",
        },
    }


def _public_site_settings_fallback():
    """Shape must match SiteSettingsSerializer (used when DB schema is behind migrations)."""
    return {
        "site_name": "Sarafi Pardis",
        "tagline": "Premium Exchange Panel",
        "logo": None,
        "favicon": None,
        "support_phone": "",
        "support_phone_2": "",
        "support_phone_3": "",
        "base_currency_code": "USD",
        "support_email": "",
        "address": "",
        "office_map_url": "",
        "business_hours": "دوشنبه تا شنبه: 9:30 صبح تا ۱۷\nیکشنبه ها: تعطیل",
        "telegram_link": "",
        "instagram_link": "",
        "twitter_link": "",
        "linkedin_link": "",
        "auto_post_on_update": False,
        "use_template_editor_for_boards": False,
        "use_playwright_for_template_render": False,
        "ui_font_filename_rtl": "",
        "ui_font_filename_ltr": "",
        "prices_webhook_url": "",
        "telegram_webhook_base_url": "",
        "support_channels": [],
        "google_client_id": "",
        "signup_enabled": True,
    }


class SiteSettingsAPIView(APIView):
    """GET: public branding (login/landing). PUT: the workspace owner.

    Widened from IsSuperAdmin to IsSuperAdminOrManagement: a self-serve signup
    owns its install with role=management and must be able to set its own
    branding, fonts and webhook. Bots, channels and the activity log below stay
    IsSuperAdmin — they are global, not per-workspace.
    """

    permission_classes = [AllowAny]
    throttle_scope = "settings"
    throttle_classes = [ScopedRateThrottle]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsSuperAdminOrManagement()]

    def get(self, request):
        try:
            settings_obj = SiteSettings.load()
            serializer = SiteSettingsSerializer(settings_obj, context={"request": request})
            return Response(serializer.data)
        except (OperationalError, ProgrammingError) as exc:
            logger.warning(
                "SiteSettings GET: database schema error (run migrations). Returning fallback. %s",
                exc,
            )
            return Response(_public_site_settings_fallback())

    def put(self, request):
        # Resolve the desk from the writer rather than trusting the ambient
        # context: branding belongs to one account (and, through it, to the
        # operators that account owns) and must never be written anywhere else.
        # An account-less caller — staff, the owner console — has no desk to
        # brand, and used to reach a save that violated the NOT NULL on
        # `account` and returned a 500.
        account_id = account_for_user(request.user)
        if account_id is None:
            return error_response(
                "This account has no workspace to brand.",
                code="no_account",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        settings_obj = SiteSettings.load(account=account_id)
        serializer = SiteSettingsSerializer(
            settings_obj,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SupportChannelViewSet(ModelViewSet):
    """CRUD for the contacts every "need help?" surface renders.

    Owner-only: these are the program owner's own numbers and handles, shared
    by every desk on the install, not per-customer settings.
    """

    permission_classes = [IsAuthenticated, IsProgrammer]
    throttle_scope = "settings"
    throttle_classes = [ScopedRateThrottle]
    serializer_class = SupportChannelSerializer
    pagination_class = None

    def get_queryset(self):
        return SupportChannel.objects.all()


class TelegramBotViewSet(ModelViewSet):
    """CRUD for Telegram bots."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    throttle_scope = "settings"
    throttle_classes = [ScopedRateThrottle]
    serializer_class = TelegramBotSerializer

    def get_queryset(self):
        return TelegramBot.objects.all().order_by("-created_at")


class TelegramChannelViewSet(ModelViewSet):
    """CRUD for Telegram channels."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    throttle_scope = "settings"
    throttle_classes = [ScopedRateThrottle]
    serializer_class = TelegramChannelSerializer

    def get_queryset(self):
        return TelegramChannel.objects.select_related("bot").all().order_by("-created_at")


class LogListAPIView(APIView):
    """GET /api/settings/logs/ - paginated logs with filters.

    ``Log`` is account-scoped, so a management user reading this sees its own
    desk's rows and nobody else's — which is why owning a workspace is enough.
    """

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]
    throttle_scope = "settings"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request):
        from rest_framework.pagination import PageNumberPagination

        level = request.query_params.get("level", "")
        source = request.query_params.get("source", "")
        search = request.query_params.get("search", "")

        qs = Log.objects.select_related("user").all()

        if level:
            qs = qs.filter(level=level)
        if source:
            qs = qs.filter(source=source)
        if search:
            qs = qs.filter(
                Q(message__icontains=search) | Q(details__icontains=search)
            )

        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = LogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = LogSerializer(qs, many=True)
        return Response(serializer.data)


def _safe_iter_files(base_path: Path):
    if not base_path.exists() or not base_path.is_dir():
        return
    for p in base_path.rglob("*"):
        if p.is_file():
            yield p


def _dir_size_bytes(base_path: Path) -> int:
    total = 0
    for fp in _safe_iter_files(base_path):
        try:
            total += fp.stat().st_size
        except OSError:
            continue
    return total


def _candidate_temp_dirs() -> list[Path]:
    media_root = Path(settings.MEDIA_ROOT)
    base_dir = Path(settings.BASE_DIR)
    return [
        media_root / "template_editor" / "uploads",
        media_root / "tmp",
        media_root / "temp",
        base_dir / "data" / "tmp",
        base_dir / "data" / "temp",
    ]


def _human_gb(bytes_value: int) -> str:
    gb = bytes_value / (1024 ** 3)
    return f"{gb:.2f} GB"


class UploadSettingsAPIView(APIView):
    """
    GET: upload policy + temp/cache storage usage.
    PUT: update upload policy (workspace owner).
    """

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]
    throttle_scope = "settings"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request):
        try:
            settings_obj = SiteSettings.load()
            used_bytes = sum(_dir_size_bytes(p) for p in _candidate_temp_dirs())
            limit_gb = int(os.environ.get("UPLOAD_STORAGE_LIMIT_GB", DEFAULT_UPLOAD_STORAGE_LIMIT_GB))
            total_bytes = max(limit_gb, 1) * (1024 ** 3)
            used_percent = min(100, round((used_bytes / total_bytes) * 100, 2)) if total_bytes > 0 else 0
            return Response({
                "max_file_size_mb": settings_obj.upload_max_file_size_mb or 5,
                "allowed_formats": settings_obj.upload_allowed_formats or ["PNG", "JPG"],
                "storage": {
                    "used_bytes": used_bytes,
                    "total_bytes": total_bytes,
                    "used_percent": used_percent,
                    "used_human": _human_gb(used_bytes),
                    "total_human": f"{limit_gb} GB",
                },
            })
        except (OperationalError, ProgrammingError) as exc:
            logger.warning(
                "UploadSettings GET: database schema error (run migrations). Returning fallback. %s",
                exc,
            )
            return Response(_upload_settings_fallback())

    def put(self, request):
        serializer = UploadPolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            settings_obj = SiteSettings.load()
            settings_obj.upload_max_file_size_mb = serializer.validated_data["max_file_size_mb"]
            settings_obj.upload_allowed_formats = serializer.validated_data["allowed_formats"]
            settings_obj.save(update_fields=["upload_max_file_size_mb", "upload_allowed_formats"])
            return self.get(request)
        except (OperationalError, ProgrammingError) as exc:
            logger.warning(
                "UploadSettings PUT: database schema error (run migrations). %s",
                exc,
            )
            fallback = _upload_settings_fallback()
            fallback["message"] = "Upload settings are temporarily read-only until migrations are applied."
            return Response(fallback, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class UploadClearTempAPIView(APIView):
    """POST: clear temporary upload files + Django cache."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    throttle_scope = "settings"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        deleted_files = 0
        freed_bytes = 0
        for temp_dir in _candidate_temp_dirs():
            if not temp_dir.exists() or not temp_dir.is_dir():
                continue
            for fp in _safe_iter_files(temp_dir):
                try:
                    size = fp.stat().st_size
                    fp.unlink(missing_ok=True)
                    deleted_files += 1
                    freed_bytes += size
                except OSError:
                    continue
            for subdir in sorted(temp_dir.rglob("*"), reverse=True):
                if subdir.is_dir():
                    try:
                        subdir.rmdir()
                    except OSError:
                        continue
        cache.clear()
        logger.info("Upload cleanup executed by user=%s deleted_files=%s freed_bytes=%s",
                    getattr(request.user, "username", None), deleted_files, freed_bytes)
        return Response({
            "deleted_files": deleted_files,
            "freed_bytes": freed_bytes,
            "freed_human": _human_gb(freed_bytes),
        }, status=status.HTTP_200_OK)
