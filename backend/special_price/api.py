from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSuperAdminOrManagement
from core.exceptions import error_response
from core.prices_webhook import notify_prices_webhook
from setting.utils import log_event
from accounts.utils import log_activity
from accounts.models import UserActivityLog
from .models import SpecialPriceHistory, SpecialPriceType
from .serializers import (
    SpecialPriceHistorySerializer,
    SpecialPriceTypeSerializer,
    SpecialPriceUpdateSerializer,
)


class SpecialPriceTypeViewSet(viewsets.ModelViewSet):
    serializer_class = SpecialPriceTypeSerializer

    # Built per request: the scoped manager reads the account from context, and a
    # class attribute would freeze an import-time (account-less) queryset.
    def get_queryset(self):
        return SpecialPriceType.objects.prefetch_related(
            "special_price_histories",
            "pairs__histories",
            "pairs__source_currency",
            "pairs__target_currency",
        ).select_related("source_currency", "target_currency").all()


class SpecialPriceUpdateAPIView(APIView):
    """Update the price for a special price type."""

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]

    def post(self, request, pk):
        try:
            spt = SpecialPriceType.objects.get(pk=pk)
        except SpecialPriceType.DoesNotExist:
            return error_response(
                "Special price type not found.",
                code="special_price_type_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = SpecialPriceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pair_id = serializer.validated_data["pair_id"]
        try:
            pair = spt.pairs.get(id=pair_id)
        except Exception:
            return error_response(
                "Selected pair does not belong to this special price.",
                code="special_price_invalid_pair",
                status_code=status.HTTP_400_BAD_REQUEST,
                errors={"pair_id": "Selected pair does not belong to this special price."},
            )

        data = serializer.validated_data
        if spt.is_double_price:
            missing = [k for k in ("cash_price", "account_price") if k not in data]
            if missing:
                return error_response(
                    "Both cash_price and account_price are required for this special price.",
                    code="special_price_double_required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    errors={k: "This field is required." for k in missing},
                )
            price_kwargs = {
                "price": data["cash_price"],  # Pardis keeps cash in `price` for analytics
                "cash_price": data["cash_price"],
                "account_price": data["account_price"],
            }
        else:
            if "price" not in data:
                return error_response(
                    "price is required.",
                    code="special_price_price_required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    errors={"price": "This field is required."},
                )
            price_kwargs = {"price": data["price"]}

        old = SpecialPriceHistory.objects.filter(special_price_type=spt, pair=pair).first()
        old_price = old.price if old else None

        ph = SpecialPriceHistory.objects.create(
            special_price_type=spt,
            pair=pair,
            notes=data.get("notes", ""),
            **price_kwargs,
        )

        log_event(
            level="INFO",
            source="system",
            message=f"Special price updated: {spt.name}",
            details=(
                f"Pair: {pair.source_currency.code}/{pair.target_currency.code}, "
                f"Old: {old_price}, New: {ph.price}"
            ),
            user=request.user if request.user.is_authenticated else None,
        )
        if request.user.is_authenticated:
            log_activity(
                request.user,
                UserActivityLog.ACTION_SPECIAL_PRICE_UPDATE,
                request,
                details=(
                    f"{spt.name} [{pair.source_currency.code}/{pair.target_currency.code}]: "
                    f"{old_price} -> {ph.price}"
                ),
            )

        notify_prices_webhook("special_price.single")
        return Response(
            SpecialPriceHistorySerializer(ph).data,
            status=status.HTTP_201_CREATED,
        )


class SpecialPriceHistoryAPIView(ListAPIView):
    serializer_class = SpecialPriceHistorySerializer
    pagination_class = None

    def get_queryset(self):
        queryset = SpecialPriceHistory.objects.filter(
            special_price_type_id=self.kwargs["pk"]
        )
        pair_id = self.request.query_params.get("pair_id")
        if pair_id:
            queryset = queryset.filter(pair_id=pair_id)
        return queryset.order_by("-created_at")
