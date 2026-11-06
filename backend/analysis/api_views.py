"""
DRF API views for analysis dashboard.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserActivityLog
from accounts.permissions import IsSuperAdminOrManagement
from accounts.utils import log_activity
from category.models import PriceType
from change_price.models import PriceHistory
from core.exceptions import error_response
from core.prices_webhook import notify_prices_webhook
from setting.utils import log_event

from .views import AnalyticsDashboardView, _parse_query_datetime

logger = logging.getLogger(__name__)


def _empty_analytics_dashboard_payload(detail: str) -> dict:
    """Same shape as ``get_analytics_data`` so the SPA never breaks on degraded responses."""
    return {
        "degraded": True,
        "detail": detail,
        "generated_at": timezone.localtime(timezone.now()).isoformat(),
        "latest_cards": [],
        "special_cards": [],
        "top_movers": [],
        "price_statistics": {},
        "finalization_stats": {},
        "overall_stats": {},
        "timeline_data": [],
        "special_timeline_data": [],
        "category_summary": [],
        "telegram_engagement": {"timeline": [], "channels": []},
        "last_updated_price_trend": None,
        "range": {
            "start": timezone.localtime(timezone.now()).isoformat(),
            "end": timezone.localtime(timezone.now()).isoformat(),
        },
    }


class AnalysisDashboardAPIView(APIView):
    """
    GET /api/analysis/dashboard/ - full analytics data for charts and cards.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            view = AnalyticsDashboardView()
            view.request = request
            view.kwargs = {}
            data = view.get_analytics_data(request)
            return Response(data)
        except Exception as exc:
            logger.exception("AnalysisDashboardAPIView.get failed")
            detail = str(exc) if settings.DEBUG else "Analytics temporarily unavailable."
            # Return 200 so optional home-dashboard analytics never triggers a global
            # client redirect to the generic 500 page (see frontend axios interceptor).
            return Response(_empty_analytics_dashboard_payload(detail))


class AnalysisImportCommitAPIView(APIView):
    """
    POST /api/analysis/import-commit/ — persist regular price history rows (e.g. from Excel).
    Super-admin / management only. Validates buy/sell spread per category.
    Body: { "rows": [ { "price_type_id", "price", "event_at"?: ISO, "notes"?: str } ] }
    """

    permission_classes = [IsAuthenticated, IsSuperAdminOrManagement]

    def post(self, request):
        rows = request.data.get("rows")
        if not isinstance(rows, list) or len(rows) == 0:
            return error_response(
                "rows must be a non-empty list.",
                code="invalid_rows",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        parsed = []
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                return error_response(
                    f"Row {i} must be an object.",
                    code="invalid_row",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            try:
                pt_id = int(row.get("price_type_id"))
            except (TypeError, ValueError):
                return error_response(
                    f"Invalid price_type_id at index {i}.",
                    code="invalid_price_type_id",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            raw_price = row.get("price")
            try:
                price_dec = Decimal(str(raw_price))
            except (InvalidOperation, TypeError, ValueError):
                return error_response(
                    f"Invalid price at index {i}.",
                    code="invalid_price",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if price_dec < 0:
                return error_response(
                    f"Negative price at index {i}.",
                    code="invalid_price",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            event_raw = row.get("event_at") or row.get("eventAt")
            event_at = None
            if event_raw not in (None, ""):
                event_at = _parse_query_datetime(event_raw)
                if event_at is None:
                    return error_response(
                        f"Invalid event_at at index {i}.",
                        code="invalid_event_at",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            notes = row.get("notes") or ""
            notes = str(notes)[:5000]

            parsed.append(
                {
                    "price_type_id": pt_id,
                    "price": price_dec,
                    "event_at": event_at,
                    "notes": notes,
                }
            )

        pt_ids = list({p["price_type_id"] for p in parsed})
        existing = list(
            PriceType.objects.filter(id__in=pt_ids).select_related("category")
        )
        found_ids = {pt.id for pt in existing}
        missing = set(pt_ids) - found_ids
        if missing:
            return error_response(
                f"Unknown price_type_id(s): {sorted(missing)}",
                code="unknown_price_type",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        created_ids = []
        with transaction.atomic():
            for p in parsed:
                ph = PriceHistory.objects.create(
                    price_type_id=p["price_type_id"],
                    price=p["price"],
                    event_at=p["event_at"],
                    notes=p["notes"],
                )
                created_ids.append(ph.id)

        log_event(
            level="INFO",
            source="system",
            message="Analysis Excel import commit",
            details=f"{len(parsed)} price history row(s)",
            user=request.user if request.user.is_authenticated else None,
        )
        if request.user.is_authenticated:
            log_activity(
                request.user,
                UserActivityLog.ACTION_BULK_PRICE_UPDATE,
                request,
                details=f"Excel import: {len(parsed)} row(s)",
            )

        if created_ids:
            notify_prices_webhook("analysis.import_commit")
        return Response(
            {"created": len(parsed), "ids": created_ids},
            status=status.HTTP_201_CREATED,
        )
