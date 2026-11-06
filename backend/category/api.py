from rest_framework import status, viewsets, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Max
from django.db.models.deletion import ProtectedError

from django.shortcuts import get_object_or_404

from change_price.prefetch_helpers import prefetch_price_histories_latest

from core.exceptions import error_response
from .models import Category, Currency, PriceType

from .serializers import (
    CategorySerializer,
    CategoryExplorerSerializer,
    PriceTypeSerializer,
)


class CurrencyListAPIView(APIView):
    """GET /api/categories/currencies/ - list all currencies for forms."""

    def get(self, request):
        currencies = Currency.objects.all().order_by("code")
        data = [{"id": c.id, "code": c.code, "name": c.name, "symbol": c.symbol or ""} for c in currencies]
        return Response(data)


class CategoryViewSet(viewsets.ModelViewSet):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return error_response(
                "This category cannot be deleted because it is linked to existing orders. "
                "Resolve or remove those orders first.",
                code="category_protected_by_orders",
                status_code=status.HTTP_409_CONFLICT,
            )

    def get_queryset(self):
        qs = Category.objects.select_related("last_used_template")
        if self.action == "list":
            qs = qs.prefetch_related(
                Prefetch(
                    "price_types",
                    queryset=PriceType.objects.select_related(
                        "source_currency", "target_currency"
                    )
                    .prefetch_related(prefetch_price_histories_latest())
                    .order_by("order", "id"),
                ),
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CategoryExplorerSerializer
        return CategorySerializer

    @action(detail=True, methods=["post"], url_path="price-types/reorder")
    def reorder_price_types(self, request, pk=None):
        """POST /api/categories/<id>/price-types/reorder/ with body: { "order": [id1, id2, ...] }"""
        category = self.get_object()
        order_ids = request.data.get("order") or []
        if not isinstance(order_ids, list):
            return error_response(
                "Invalid payload. Expected { \"order\": [id, ...] }.",
                code="invalid_payload",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        # Validate all ids belong to this category
        qs = PriceType.objects.filter(category=category)
        ids_in_category = set(qs.values_list("id", flat=True))
        for i, pt_id in enumerate(order_ids):
            if pt_id not in ids_in_category:
                continue
            qs.filter(pk=pt_id).update(order=i)
        return Response({"status": "ok"})

    @action(detail=True, methods=["post"], url_path="telegram-media")
    def upload_telegram_media(self, request, pk=None):
        """Deprecated: media now comes from Template Editor (last_used_template image)."""
        return error_response(
            "Telegram media upload is deprecated. Media is inherited from Template Editor.",
            code="telegram_media_managed_by_template",
            status_code=status.HTTP_410_GONE,
        )


class PriceTypeViewSet(viewsets.ModelViewSet):
    serializer_class = PriceTypeSerializer

    def get_queryset(self):
        # PriceType owns no account column; it is reachable only through a
        # category the caller's own account owns, which is what the scoped
        # ``Category.objects`` subquery enforces.
        qs = PriceType.objects.select_related(
            "category", "source_currency", "target_currency"
        ).filter(category__in=Category.objects.all())
        category_id = self.kwargs.get("category_pk")
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def perform_create(self, serializer):
        category_id = self.kwargs.get("category_pk")
        if category_id:
            # Ensure nested category exists so we return 404 instead of DB-level FK failures.
            get_object_or_404(Category, pk=category_id)
            next_order = (
                PriceType.objects.filter(category_id=category_id).aggregate(Max("order"))["order__max"]
                or -1
            ) + 1
            try:
                with transaction.atomic():
                    serializer.save(category_id=category_id, order=next_order)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "A price type with this name already exists in this category."
                        ]
                    }
                ) from exc
        else:
            try:
                with transaction.atomic():
                    serializer.save()
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Could not save this price type due to a data conflict."
                        ]
                    }
                ) from exc
