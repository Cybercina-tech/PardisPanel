import logging

from django.conf import settings
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSuperAdminOrManagement
from core.exceptions import error_response
from core.prices_webhook import notify_prices_webhook
from category.models import Category, PriceType
from setting.utils import log_event
from accounts.utils import log_activity
from accounts.models import UserActivityLog
from .models import PriceHistory
from .prefetch_helpers import prefetch_price_histories_latest
from .serializers import (
    BulkPriceUpdateSerializer,
    PriceHistorySerializer,
    PriceUpdateSerializer,
    PriceTypeWithLatestPriceSerializer,
)

logger = logging.getLogger(__name__)


class PriceListAPIView(APIView):
    """All price types with their latest prices. Read-only: any authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        price_types = (
            PriceType.objects.select_related(
                "category", "source_currency", "target_currency"
            )
            .prefetch_related(prefetch_price_histories_latest())
            .all()
        )

        data = []
        for pt in price_types:
            latest = pt.price_histories.first()
            data.append({
                "id": pt.id,
                "name": pt.name,
                "slug": pt.slug,
                "category_id": pt.category_id,
                "category_name": pt.category.name,
                "source_currency": pt.source_currency.code,
                "target_currency": pt.target_currency.code,
                "trade_type": pt.trade_type,
                "latest_price": latest.price if latest else None,
                "latest_price_at": latest.created_at if latest else None,
            })

        serializer = PriceTypeWithLatestPriceSerializer(data, many=True)
        return Response(serializer.data)


class PriceDetailAPIView(APIView):
    """Single price type by id with same shape as list (for UpdatePriceView). Read-only."""

    permission_classes = [IsAuthenticated]

    def get(self, request, price_type_id):
        try:
            pt = (
                PriceType.objects.select_related(
                    "category", "source_currency", "target_currency"
                )
                .prefetch_related(prefetch_price_histories_latest())
                .get(id=price_type_id)
            )
        except PriceType.DoesNotExist:
            return error_response(
                "Price type not found.",
                code="price_type_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        latest = pt.price_histories.first()
        data = {
            "id": pt.id,
            "name": pt.name,
            "slug": pt.slug,
            "category_id": pt.category_id,
            "category_name": pt.category.name,
            "source_currency": pt.source_currency.code,
            "target_currency": pt.target_currency.code,
            "trade_type": pt.trade_type,
            "latest_price": latest.price if latest else None,
            "latest_price_at": latest.created_at if latest else None,
        }
        serializer = PriceTypeWithLatestPriceSerializer(data)
        return Response(serializer.data)


class PriceUpdateAPIView(APIView):
    """Update a single price type. Management and Super Admin only."""

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]

    def post(self, request, price_type_id):
        try:
            price_type = PriceType.objects.select_related("category").get(id=price_type_id)
        except PriceType.DoesNotExist:
            return error_response(
                "Price type not found.",
                code="price_type_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = PriceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            old_price_obj = (
                PriceHistory.objects.filter(price_type=price_type).defer("event_at").first()
            )
            old_price = old_price_obj.price if old_price_obj else None

            price_history = PriceHistory.objects.create(
                price_type=price_type,
                price=serializer.validated_data["price"],
                notes=serializer.validated_data.get("notes", ""),
            )

            log_event(
                level="INFO",
                source="system",
                message=f"Price updated for {price_type.name} ({price_type.category.name})",
                details=f"Old: {old_price}, New: {price_history.price}",
                user=request.user if request.user.is_authenticated else None,
            )
            if request.user.is_authenticated:
                log_activity(
                    request.user,
                    UserActivityLog.ACTION_PRICE_UPDATE,
                    request,
                    details=f"{price_type.name}: {old_price} -> {price_history.price}",
                )

            notify_prices_webhook("change_price.single")
            return Response(
                PriceHistorySerializer(price_history).data,
                status=status.HTTP_201_CREATED,
            )
        except (OperationalError, ProgrammingError) as exc:
            logger.exception("Single price update database error")
            hint = (
                "Could not save price. Run migrations on the server "
                "(Docker: docker compose exec app python manage.py migrate)."
            )
            if settings.DEBUG:
                hint = f"{hint} Detail: {exc}"
            return error_response(
                hint,
                code="database_error",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class BulkPriceUpdateAPIView(APIView):
    """Bulk-update prices for all price types in a category. Management and Super Admin only."""

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]

    def post(self, request, category_id):
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return error_response(
                "Category not found.",
                code="category_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = BulkPriceUpdateSerializer(data=request.data, context={"category": category})
        serializer.is_valid(raise_exception=True)
        prices_map = serializer.validated_data["prices"]
        notes = serializer.validated_data.get("notes", "")

        price_types = PriceType.objects.filter(category=category)
        created = []

        try:
            with transaction.atomic():
                for pt in price_types:
                    key = str(pt.id)
                    if key not in prices_map:
                        continue
                    ph = PriceHistory.objects.create(
                        price_type=pt,
                        price=prices_map[key],
                        notes=notes,
                    )
                    created.append(ph)

            log_event(
                level="INFO",
                source="system",
                message=f"Category prices updated: {category.name}",
                details=f"Updated {len(created)} price(s). Notes: {notes or 'None'}",
                user=request.user if request.user.is_authenticated else None,
            )
            if request.user.is_authenticated:
                log_activity(
                    request.user,
                    UserActivityLog.ACTION_BULK_PRICE_UPDATE,
                    request,
                    details=f"{category.name}: {len(created)} price(s)",
                )

            if created:
                notify_prices_webhook("change_price.bulk")
            return Response(
                PriceHistorySerializer(created, many=True).data,
                status=status.HTTP_201_CREATED,
            )
        except (OperationalError, ProgrammingError) as exc:
            logger.exception("Bulk price update database error")
            hint = (
                "Could not save prices. Run migrations on the server "
                "(Docker: docker compose exec app python manage.py migrate)."
            )
            if settings.DEBUG:
                hint = f"{hint} Detail: {exc}"
            return error_response(
                hint,
                code="database_error",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class PriceHistoryAPIView(ListAPIView):
    """Price history for a specific price type. Read-only: any authenticated user."""

    permission_classes = [IsAuthenticated]
    serializer_class = PriceHistorySerializer
    pagination_class = None

    def get_queryset(self):
        return (
            PriceHistory.objects.filter(price_type_id=self.kwargs["price_type_id"])
            .defer("event_at")
            .order_by("-created_at")
        )
