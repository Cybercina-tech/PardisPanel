"""
DRF API views for finalization flows.
"""
import logging
from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from celery.exceptions import TimeoutError as CeleryTimeoutError

from accounts.permissions import IsSuperAdminOrManagement
from category.models import Category, PriceType
from change_price.prefetch_helpers import prefetch_price_histories_latest
from special_price.models import SpecialPriceType, SpecialPriceHistory
from special_price.prefetch_helpers import prefetch_special_price_histories_latest
from telegram_app.models import TelegramChannel
from telegram_app.serializers import TelegramChannelSerializer
from price_publisher.services.banner_formats import (
    FORMATS as BANNER_FORMATS,
    STANDARD as BANNER_STANDARD,
    apply_format,
    is_valid_format,
)
from price_publisher.services.publisher import PricePublicationError, PricePublisherService
from price_publisher.tasks import publish_category_prices_task, publish_special_price_task
from setting.utils import log_finalize_event, log_telegram_event


from .services import ExternalAPIService
from .models import Finalization, FinalizedPriceHistory, SpecialPriceFinalization
from .views import sort_gbp_price_types
from .serializers import (
    FinalizeCategoryRequestSerializer,
    FinalizeSpecialPriceRequestSerializer,
    FinalizeAllRequestSerializer,
)

logger = logging.getLogger(__name__)

OTHER_CURRENCIES_MARK = "سایر"


TOMAN_CODES = {"IRR", "IRT"}


def _is_usdt_toman(price_type):
    codes = {
        getattr(price_type.source_currency, "code", "").upper(),
        getattr(price_type.target_currency, "code", "").upper(),
    }
    return "USDT" in codes and bool(codes & TOMAN_CODES)


def _finalize_price_types(category, price_types):
    """Price types of ``category`` that take part in finalize and its banner, in board order.

    The Other-currencies banner has no USDT/Toman rows, so those are left out of it.
    """
    name = category.name or ""
    lower = name.lower()
    if "پوند" in name or "pound" in lower or "gbp" in lower:
        return sort_gbp_price_types(price_types)
    if OTHER_CURRENCIES_MARK in name:
        return [pt for pt in price_types if not _is_usdt_toman(pt)]
    return price_types


def _push_external_rates(price_items):
    """Send finalized GBP/USDT rates to the public rates API (Pardis contract).

    Never raises: a failing third-party site must not block finalizing. Returns
    True only when at least one rate was sent and none failed.
    """
    try:
        results = ExternalAPIService.send_finalized_prices(price_items)
    except Exception:
        logger.exception("External rates sync crashed")
        return False
    sent, failed = len(results.get("sent", [])), len(results.get("failed", []))
    if failed:
        logger.warning("External rates sync: %s sent, %s failed", sent, failed)
    return sent > 0 and failed == 0


def _push_external_special_rate(special_price_type, special_price_history):
    try:
        return ExternalAPIService.send_finalized_special_prices(
            [(special_price_type, special_price_history)]
        )
    except Exception:
        logger.exception("External special rate sync crashed")
        return None


# Omit from SELECT so older DBs without these columns still load the finalize dashboard.
# Round-robin still works after migrate (column then exists); until then values default in memory.
_DASHBOARD_CATEGORY_DEFER = ("last_used_template",)
_DASHBOARD_SPECIAL_TYPE_DEFER = ("last_used_template",)


def _wait_for_publication_task(async_result):
    timeout_seconds = max(1, int(getattr(settings, "FINALIZE_TASK_WAIT_TIMEOUT", 75)))
    try:
        payload = async_result.get(timeout=timeout_seconds)
        if isinstance(payload, dict):
            return payload
        return {
            "success": False,
            "response": f"Invalid task response: {type(payload).__name__}",
            "caption": None,
            "publish_path": "unknown",
            "render_fallback_reason": "invalid_task_response",
        }
    except CeleryTimeoutError:
        logger.exception("Publication task timeout task_id=%s", async_result.id)
        return {
            "success": False,
            "response": f"Publication timed out after {timeout_seconds}s",
            "caption": None,
            "publish_path": "worker_timeout",
            "render_fallback_reason": "task_timeout",
        }
    except Exception as exc:
        logger.exception("Publication task failed task_id=%s", async_result.id)
        return {
            "success": False,
            "response": str(exc),
            "caption": None,
            "publish_path": "worker_error",
            "render_fallback_reason": "task_error",
        }


def _get_publication_destinations():
    """Return list of publication destinations with enabled flag for frontend."""
    return [{"id": "telegram", "label": "Telegram Channel", "enabled": True}]


def _finalized_state(category):
    """Everything ever finalized for a category.

    A finalization only stores the prices that were new at that moment, so the
    latest one alone forgets rows finalized earlier and they would reappear as
    pending. Returns ``(history_ids, {price_type_id: most recently finalized history})``.
    """
    rows = (
        FinalizedPriceHistory.objects.filter(finalization__category=category)
        .select_related("price_history")
        .order_by("finalization__finalized_at", "id")
    )
    history_ids = set()
    by_price_type = {}
    for row in rows:
        ph = row.price_history
        if ph is None:
            continue
        history_ids.add(ph.id)
        by_price_type[ph.price_type_id] = ph
    return history_ids, by_price_type


def _build_finalize_dashboard_data():
    """Build dashboard data: categories with pending prices and pending special prices."""
    # Separate summary query avoids edge cases after iterating the prefetched queryset.
    category_summaries = list(
        Category.objects.order_by("name").values("id", "name", "slug", "description")
    )
    categories = (
        Category.objects.defer(*_DASHBOARD_CATEGORY_DEFER)
        .prefetch_related(
            Prefetch(
                "price_types",
                queryset=PriceType.objects.all()
                .select_related("source_currency", "target_currency")
                .prefetch_related(prefetch_price_histories_latest())
                .order_by("order", "id"),
            )
        )
        .order_by("name")
    )

    pending_by_category = []
    for category in categories:
        finalized_history_ids, finalized_price_map = _finalized_state(category)

        price_types = list(category.price_types.all())
        price_types = _finalize_price_types(category, price_types)

        category_pending = []
        for price_type in price_types:
            latest_price = price_type.price_histories.first()
            if latest_price and latest_price.id not in finalized_history_ids:
                item = {
                    "price_type_id": price_type.id,
                    "price_type_name": price_type.name,
                    "price_history_id": latest_price.id,
                    "price": str(latest_price.price),
                    "created_at": latest_price.created_at.isoformat(),
                    "has_older_finalized": len(finalized_history_ids) > 0,
                }
                if price_type.id in finalized_price_map:
                    prev_ph = finalized_price_map[price_type.id]
                    item["previous_price"] = str(prev_ph.price)
                else:
                    item["previous_price"] = None
                category_pending.append(item)

        if category_pending:
            pending_by_category.append(
                {
                    "category_id": category.id,
                    "category_name": category.name,
                    "category_slug": category.slug,
                    "pending_prices": category_pending,
                }
            )

    special_price_types = (
        SpecialPriceType.objects.defer(*_DASHBOARD_SPECIAL_TYPE_DEFER)
        .prefetch_related(prefetch_special_price_histories_latest())
        .select_related("source_currency", "target_currency")
        .order_by("name")
    )

    pending_special_prices = []
    for special_price_type in special_price_types:
        latest_price = special_price_type.special_price_histories.first()
        if latest_price:
            is_finalized = SpecialPriceFinalization.objects.filter(
                special_price_history=latest_price
            ).exists()
            if not is_finalized:
                prev_finalization = (
                    SpecialPriceFinalization.objects.filter(
                        special_price_history__special_price_type=special_price_type
                    )
                    .order_by("-finalized_at")
                    .select_related("special_price_history")
                    .first()
                )
                previous_price = None
                if prev_finalization and prev_finalization.special_price_history_id:
                    try:
                        previous_price = str(
                            prev_finalization.special_price_history.price
                        )
                    except Exception:
                        logger.warning(
                            "Skipping previous special price (special_price_finalization_id=%s)",
                            getattr(prev_finalization, "pk", None),
                        )
                        previous_price = None
                pending_special_prices.append(
                    {
                        "special_price_type_id": special_price_type.id,
                        "special_price_type_name": special_price_type.name,
                        "price_history_id": latest_price.id,
                        "price": str(latest_price.price),
                        "is_double_price": bool(special_price_type.is_double_price),
                        "cash_price": (
                            str(latest_price.cash_price) if latest_price.cash_price is not None else None
                        ),
                        "account_price": (
                            str(latest_price.account_price) if latest_price.account_price is not None else None
                        ),
                        "created_at": latest_price.created_at.isoformat(),
                        "previous_price": previous_price,
                    }
                )

    # The publish step picks a channel from this payload, and the whole screen is
    # gated on `has_telegram_channel`; without them the dashboard renders its
    # "no channels" empty state even when channels exist.
    channels = TelegramChannelSerializer(
        TelegramChannel.objects.filter(is_active=True, bot__is_active=True)
        .select_related("bot")
        .order_by("name"),
        many=True,
    ).data

    return {
        "categories": category_summaries,
        "pending_by_category": pending_by_category,
        "has_pending": len(pending_by_category) > 0,
        "pending_special_prices": pending_special_prices,
        "has_pending_special": len(pending_special_prices) > 0,
        "publication_destinations": _get_publication_destinations(),
        "channels": channels,
        "has_telegram_channel": len(channels) > 0,
    }


class FinalizeDashboardAPIView(APIView):
    """GET /api/finalize/dashboard/ - categories with pending prices. Read-only: any authenticated user (incl. Employee)."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "finalize"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request):
        try:
            data = _build_finalize_dashboard_data()
            return Response(data)
        except Exception as exc:
            logger.exception("FinalizeDashboardAPIView.get failed")
            try:
                destinations = _get_publication_destinations()
            except Exception:
                destinations = [{"id": "telegram", "label": "Telegram Channel", "enabled": True}]
            if isinstance(exc, OperationalError):
                detail = (
                    "Database schema mismatch (often fixed by: python manage.py migrate). "
                    "See server logs for the exact SQL error."
                )
            else:
                detail = (
                    "Finalize dashboard could not be loaded. Check server logs or run migrations."
                )
            payload = {
                "categories": [],
                "pending_by_category": [],
                "has_pending": False,
                "pending_special_prices": [],
                "has_pending_special": False,
                "publication_destinations": destinations,
                "channels": [],
                "has_telegram_channel": False,
                "degraded": True,
                "detail": detail,
            }
            if settings.DEBUG:
                payload["debug_exception"] = repr(exc)
            return Response(payload, status=status.HTTP_200_OK)


class FinalizeCategoryAPIView(APIView):
    """POST /api/finalize/category/<id>/ - finalize a category."""

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]
    throttle_scope = "finalize"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request, category_id):
        category = get_object_or_404(
            Category.objects.defer(*_DASHBOARD_CATEGORY_DEFER), id=category_id
        )
        channels = TelegramChannel.objects.filter(is_active=True).select_related("bot")

        serializer = FinalizeCategoryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel_id = serializer.validated_data["channel_id"]
        notes = serializer.validated_data.get("notes", "")

        channel = get_object_or_404(TelegramChannel, id=channel_id, is_active=True)

        finalized_history_ids, finalized_price_map = _finalized_state(category)

        price_types = PriceType.objects.filter(category=category).select_related(
            "source_currency", "target_currency"
        )
        price_types = _finalize_price_types(category, price_types)

        price_items = []
        pending_prices = []

        for price_type in price_types:
            latest_price = price_type.price_histories.first()
            if not latest_price:
                continue

            if latest_price.id not in finalized_history_ids:
                price_items.append((price_type, latest_price))
                pending_prices.append({"price_type": price_type, "price_history": latest_price})
            else:
                if price_type.id in finalized_price_map:
                    finalized_price = finalized_price_map[price_type.id]
                    price_items.append((price_type, finalized_price))
                else:
                    price_items.append((price_type, latest_price))

        if not price_items:
            return Response(
                {"detail": f'No prices found for category "{category.name}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        notes_text = notes.strip() if notes else None

        api_sent_successfully = _push_external_rates(price_items)

        publish_async = publish_category_prices_task.apply_async(
            kwargs={
                "category_id": category.id,
                "channel_id": channel.id,
                "notes": notes_text,
                "price_history_ids": [price_history.id for _, price_history in price_items],
                "user_id": request.user.id,
            }
        )
        publication = _wait_for_publication_task(publish_async)
        message_sent = bool(publication.get("success"))
        image_caption = publication.get("caption")
        template_id = publication.get("template_id")
        publication_response = publication.get("response", "")
        publish_path = publication.get("publish_path", "unknown")
        render_fallback_reason = publication.get("render_fallback_reason")

        if render_fallback_reason == "template_missing_or_invalid":
            return Response(
                {
                    "detail": "Publish blocked: category template is missing or invalid.",
                    "telegram_response": publication_response,
                    "publish_path": publish_path,
                    "render_fallback_reason": render_fallback_reason,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        strict = getattr(settings, "FINALIZE_STRICT_TELEGRAM", False)
        if strict and not message_sent:
            return Response(
                {
                    "detail": "Telegram publication failed. Finalization was not saved (strict mode).",
                    "telegram_response": publication_response,
                    "publish_path": publish_path,
                    "render_fallback_reason": render_fallback_reason,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            finalization = Finalization.objects.create(
                category=category,
                channel=channel if message_sent else None,
                finalized_by=request.user,
                message_sent=message_sent,
                image_caption=image_caption if message_sent else None,
                telegram_response=publication_response or None,
                notes=notes,
            )
            for item in pending_prices:
                FinalizedPriceHistory.objects.create(
                    finalization=finalization,
                    price_history=item["price_history"],
                )

        total_prices_count = len(price_items)
        new_prices_count = len(pending_prices)
        log_finalize_event(
            level="INFO" if message_sent else "WARNING",
            message=f"Category finalized: {category.name}",
            details={
                "event": "finalize_category",
                "category_id": category.id,
                "category_name": category.name,
                "finalization_id": finalization.id,
                "total_prices": total_prices_count,
                "new_prices": new_prices_count,
                "message_sent": message_sent,
                "publish_path": publish_path,
                "render_fallback_reason": render_fallback_reason,
            },
            user=request.user,
        )
        if message_sent:
            log_telegram_event(
                level="INFO",
                message="Category prices published to Telegram",
                details={
                    "event": "finalize_category_telegram_publish",
                    "category_id": category.id,
                    "category_name": category.name,
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                },
                user=request.user,
            )

        return Response(
            {
                "success": True,
                "finalization_id": finalization.id,
                "message_sent": message_sent,
                "total_prices": total_prices_count,
                "new_prices": new_prices_count,
                "api_sent_successfully": api_sent_successfully,
                "api_sync_queued": True,
                "telegram_response": publication_response,
                "template_id": template_id,
                "publish_path": publish_path,
                "render_fallback_reason": render_fallback_reason,
            },
            status=status.HTTP_201_CREATED,
        )


def _banner_response(png_bytes, fmt, base_name):
    suffix = "" if fmt == BANNER_STANDARD else f"-{fmt}"
    response = HttpResponse(apply_format(png_bytes, fmt), content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="{base_name}{suffix}.png"'
    response["Cache-Control"] = "no-store"
    return response


def _requested_banner_format(request):
    """Returns ``(format, error_response)``; exactly one of them is None.

    The query param is ``size``: DRF reserves ``?format=`` for renderer selection
    and would 404 on ``story``.
    """
    fmt = request.query_params.get("size", BANNER_STANDARD)
    if is_valid_format(fmt):
        return fmt, None
    return None, Response(
        {"detail": f"Unknown size. Use one of: {', '.join(BANNER_FORMATS)}."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _latest_category_price_items(category):
    """``(price_type, latest history)`` pairs, in the order the board expects."""
    price_types = PriceType.objects.filter(category=category).select_related(
        "source_currency", "target_currency"
    )
    price_types = _finalize_price_types(category, price_types)
    items = []
    for price_type in price_types:
        latest = price_type.price_histories.first()
        if latest:
            items.append((price_type, latest))
    return items


class FinalizeBannersListAPIView(APIView):
    """GET /api/finalize/banners/ - what can be downloaded as a banner (names only)."""

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]
    throttle_scope = "finalize"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request):
        categories = []
        for category in (
            Category.objects.defer(*_DASHBOARD_CATEGORY_DEFER)
            .prefetch_related(
                Prefetch(
                    "price_types",
                    queryset=PriceType.objects.all().prefetch_related(
                        prefetch_price_histories_latest()
                    ),
                )
            )
            .order_by("name")
        ):
            if any(pt.price_histories.first() for pt in category.price_types.all()):
                categories.append({"id": category.id, "name": category.name})

        specials = []
        for special_type in (
            SpecialPriceType.objects.defer(*_DASHBOARD_SPECIAL_TYPE_DEFER)
            .prefetch_related(prefetch_special_price_histories_latest())
            .order_by("name")
        ):
            latest = special_type.special_price_histories.first()
            if latest:
                specials.append(
                    {
                        "id": special_type.id,
                        "history_id": latest.id,
                        "name": special_type.name,
                    }
                )

        return Response(
            {
                "formats": list(BANNER_FORMATS),
                "categories": categories,
                "special_prices": specials,
            }
        )


class FinalizeCategoryBannerAPIView(APIView):
    """GET /api/finalize/category/<id>/banner/?size=standard|story|post.

    Renders the category board from each price type's latest price. Sends nothing
    to any channel and records no finalization.
    """

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]
    throttle_scope = "finalize"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request, category_id):
        fmt, error = _requested_banner_format(request)
        if error:
            return error
        category = get_object_or_404(
            Category.objects.defer(*_DASHBOARD_CATEGORY_DEFER), id=category_id
        )
        price_items = _latest_category_price_items(category)
        if not price_items:
            return Response(
                {"detail": f'No prices found for category "{category.name}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = PricePublisherService(acting_user=request.user).publish_category_prices(
                category=category,
                price_items=price_items,
                channel=None,
            )
        except PricePublicationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        if not result.image_bytes:
            return Response(
                {"detail": "Banner could not be rendered."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return _banner_response(result.image_bytes, fmt, f"category-{category.slug or category.pk}")


class FinalizeSpecialPriceBannerAPIView(APIView):
    """GET /api/finalize/special-price/<id>/banner/?size=standard|story|post.

    Renders exactly what finalize would publish but sends nothing to any channel
    and records no finalization, so it works before, after, or instead of finalize.
    """

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]
    throttle_scope = "finalize"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request, special_price_history_id):
        fmt, error = _requested_banner_format(request)
        if error:
            return error
        history = get_object_or_404(
            SpecialPriceHistory.objects.select_related("special_price_type").defer(
                "special_price_type__last_used_template"
            ),
            id=special_price_history_id,
        )
        special_type = history.special_price_type
        try:
            result = PricePublisherService(acting_user=request.user).publish_special_price(
                special_price_type=special_type,
                price_history=history,
                channel=None,
            )
        except PricePublicationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        if not result.image_bytes:
            return Response(
                {"detail": "Banner could not be rendered."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return _banner_response(
            result.image_bytes, fmt, f"special-{special_type.slug or special_type.pk}-{history.pk}"
        )


class FinalizeSpecialPriceAPIView(APIView):
    """POST /api/finalize/special-price/<id>/ - finalize a special price (id is special_price_history_id)."""

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]
    throttle_scope = "finalize"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request, special_price_history_id):
        special_price_history = get_object_or_404(
            SpecialPriceHistory.objects.select_related("special_price_type").defer(
                "special_price_type__last_used_template"
            ),
            id=special_price_history_id,
        )
        special_price_type = special_price_history.special_price_type

        existing = SpecialPriceFinalization.objects.filter(
            special_price_history=special_price_history
        ).first()
        if existing:
            return Response(
                {"detail": "This special price is already finalized."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FinalizeSpecialPriceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel_id = serializer.validated_data["channel_id"]
        notes = serializer.validated_data.get("notes", "")

        channel = get_object_or_404(TelegramChannel, id=channel_id, is_active=True)
        notes_text = notes.strip() if notes else None

        publish_async = publish_special_price_task.apply_async(
            kwargs={
                "special_price_history_id": special_price_history.id,
                "channel_id": channel.id,
                "notes": notes_text,
            }
        )
        publication = _wait_for_publication_task(publish_async)
        message_sent = bool(publication.get("success"))
        image_caption = publication.get("caption")
        template_id = publication.get("template_id")
        publication_response = publication.get("response", "")
        publish_path = publication.get("publish_path", "unknown")
        render_fallback_reason = publication.get("render_fallback_reason")

        strict = getattr(settings, "FINALIZE_STRICT_TELEGRAM", False)
        if strict and not message_sent:
            return Response(
                {
                    "detail": "Telegram publication failed. Finalization was not saved (strict mode).",
                    "telegram_response": publication_response,
                    "publish_path": publish_path,
                    "render_fallback_reason": render_fallback_reason,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            finalization = SpecialPriceFinalization.objects.create(
                special_price_history=special_price_history,
                channel=channel if message_sent else None,
                finalized_by=request.user,
                message_sent=message_sent,
                image_caption=image_caption if message_sent else None,
                telegram_response=publication_response or None,
                notes=notes,
            )
            _push_external_special_rate(special_price_type, special_price_history)

        log_finalize_event(
            level="INFO" if message_sent else "WARNING",
            message=f"Special price finalized: {special_price_type.name}",
            details={
                "event": "finalize_special_price",
                "special_price_type_id": special_price_type.id,
                "special_price_history_id": special_price_history.id,
                "price": str(special_price_history.price),
                "finalization_id": finalization.id,
                "message_sent": message_sent,
                "publish_path": publish_path,
                "render_fallback_reason": render_fallback_reason,
            },
            user=request.user,
        )

        return Response(
            {
                "success": True,
                "finalization_id": finalization.id,
                "message_sent": message_sent,
                "telegram_response": publication_response,
                "template_id": template_id,
                "publish_path": publish_path,
                "render_fallback_reason": render_fallback_reason,
            },
            status=status.HTTP_201_CREATED,
        )


class FinalizeAllAPIView(APIView):
    """POST /api/finalize/all/ - finalize multiple categories and special prices in one request."""

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]
    throttle_scope = "finalize"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        serializer = FinalizeAllRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel_id = serializer.validated_data["channel_id"]
        category_ids = serializer.validated_data.get("category_ids") or []
        special_price_history_ids = serializer.validated_data.get("special_price_history_ids") or []

        if not category_ids and not special_price_history_ids:
            return Response(
                {"detail": "Provide at least one category_ids or special_price_history_ids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        channel = get_object_or_404(TelegramChannel, id=channel_id, is_active=True)
        notes = ""

        results = []

        for cat_id in category_ids:
            try:
                category = get_object_or_404(
                    Category.objects.defer(*_DASHBOARD_CATEGORY_DEFER), id=cat_id
                )
                self._finalize_one_category(request, category, channel, notes)
                results.append({"id": cat_id, "type": "category", "success": True})
            except Exception as exc:
                logger.exception("Finalize all: category %s failed", cat_id)
                results.append({
                    "id": cat_id,
                    "type": "category",
                    "success": False,
                    "error": str(exc) or "Unknown error",
                })

        for sp_id in special_price_history_ids:
            try:
                special_price_history = get_object_or_404(
                    SpecialPriceHistory.objects.select_related("special_price_type").defer(
                        "special_price_type__last_used_template"
                    ),
                    id=sp_id,
                )
                special_price_type = special_price_history.special_price_type
                if SpecialPriceFinalization.objects.filter(
                    special_price_history=special_price_history
                ).exists():
                    results.append({
                        "id": sp_id,
                        "type": "special",
                        "success": False,
                        "error": "Already finalized.",
                    })
                    continue
                notes_text = notes.strip() if notes else None
                publish_async = publish_special_price_task.apply_async(
                    kwargs={
                        "special_price_history_id": special_price_history.id,
                        "channel_id": channel.id,
                        "notes": notes_text,
                        "user_id": request.user.id,
                        "user_id": request.user.id,
                    }
                )
                publication = _wait_for_publication_task(publish_async)
                message_sent = bool(publication.get("success"))
                image_caption = publication.get("caption")
                publication_response = publication.get("response", "")
                publish_path = publication.get("publish_path", "unknown")
                render_fallback_reason = publication.get("render_fallback_reason")
                strict = getattr(settings, "FINALIZE_STRICT_TELEGRAM", False)
                if strict and not message_sent:
                    results.append({
                        "id": sp_id,
                        "type": "special",
                        "success": False,
                        "error": "Telegram publication failed (strict mode).",
                    })
                    continue
                with transaction.atomic():
                    finalization = SpecialPriceFinalization.objects.create(
                        special_price_history=special_price_history,
                        channel=channel if message_sent else None,
                        finalized_by=request.user,
                        message_sent=message_sent,
                        image_caption=image_caption if message_sent else None,
                        telegram_response=publication_response or None,
                        notes=notes,
                    )
                _push_external_special_rate(special_price_type, special_price_history)
                log_finalize_event(
                    level="INFO" if message_sent else "WARNING",
                    message=f"Special price finalized (all): {special_price_type.name}",
                    details={
                        "event": "finalize_special_price_bulk",
                        "special_price_type_id": special_price_type.id,
                        "special_price_history_id": special_price_history.id,
                        "finalization_id": finalization.id,
                        "message_sent": message_sent,
                        "publish_path": publish_path,
                        "render_fallback_reason": render_fallback_reason,
                    },
                    user=request.user,
                )
                results.append({
                    "id": sp_id,
                    "type": "special",
                    "success": True,
                    "message_sent": message_sent,
                    "telegram_response": publication_response,
                    "publish_path": publish_path,
                    "render_fallback_reason": render_fallback_reason,
                })
            except Exception as exc:
                logger.exception("Finalize all: special price %s failed", sp_id)
                results.append({
                    "id": sp_id,
                    "type": "special",
                    "success": False,
                    "error": str(exc) or "Unknown error",
                })

        return Response({"results": results}, status=status.HTTP_200_OK)

    def _finalize_one_category(self, request, category, channel, notes):
        """Run finalization for one category. Raises on failure."""
        finalized_history_ids, finalized_price_map = _finalized_state(category)

        price_types = PriceType.objects.filter(category=category).select_related(
            "source_currency", "target_currency"
        )
        price_types = _finalize_price_types(category, price_types)

        price_items = []
        pending_prices = []

        for price_type in price_types:
            latest_price = price_type.price_histories.first()
            if not latest_price:
                continue
            if latest_price.id not in finalized_history_ids:
                price_items.append((price_type, latest_price))
                pending_prices.append({"price_type": price_type, "price_history": latest_price})
            else:
                if price_type.id in finalized_price_map:
                    price_items.append((price_type, finalized_price_map[price_type.id]))
                else:
                    price_items.append((price_type, latest_price))

        if not price_items:
            raise ValueError(f'No prices found for category "{category.name}".')

        notes_text = notes.strip() if notes else None

        _push_external_rates(price_items)

        publish_async = publish_category_prices_task.apply_async(
            kwargs={
                "category_id": category.id,
                "channel_id": channel.id,
                "notes": notes_text,
                "price_history_ids": [price_history.id for _, price_history in price_items],
                "user_id": request.user.id,
            }
        )
        publication = _wait_for_publication_task(publish_async)
        message_sent = bool(publication.get("success"))
        image_caption = publication.get("caption")
        template_id = publication.get("template_id")
        publication_response = publication.get("response", "")
        publish_path = publication.get("publish_path", "unknown")
        render_fallback_reason = publication.get("render_fallback_reason")

        strict = getattr(settings, "FINALIZE_STRICT_TELEGRAM", False)
        if strict and not message_sent:
            raise ValueError(
                "Telegram publication failed (strict mode). Finalization was not saved."
            )

        with transaction.atomic():
            finalization = Finalization.objects.create(
                category=category,
                channel=channel if message_sent else None,
                finalized_by=request.user,
                message_sent=message_sent,
                image_caption=image_caption if message_sent else None,
                telegram_response=publication_response or None,
                notes=notes,
            )
            for item in pending_prices:
                FinalizedPriceHistory.objects.create(
                    finalization=finalization,
                    price_history=item["price_history"],
                )

        log_finalize_event(
            level="INFO" if message_sent else "WARNING",
            message=f"Category finalized (all): {category.name}",
            details={
                "event": "finalize_category_bulk",
                "category_id": category.id,
                "category_name": category.name,
                "finalization_id": finalization.id,
                "new_prices": len(pending_prices),
                "message_sent": message_sent,
                "publish_path": publish_path,
                "template_id": template_id,
                "render_fallback_reason": render_fallback_reason,
            },
            user=request.user,
        )
