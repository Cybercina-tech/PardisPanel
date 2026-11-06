import json
import logging
import math
from collections import defaultdict
from datetime import timedelta, datetime, timezone as dt_timezone

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import DateTimeField, OuterRef, Subquery, Count, Max, Sum, Case, When, IntegerField
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


def _ensure_aware_datetime(dt):
    """Coerce naive datetimes so ``timezone.localtime`` never raises."""
    if dt is None:
        return None
    if timezone.is_naive(dt):
        try:
            return timezone.make_aware(dt, timezone.get_current_timezone())
        except Exception:
            return timezone.make_aware(dt, dt_timezone.utc)
    return dt


class ChartJSONEncoder(DjangoJSONEncoder):
    """Custom JSON encoder that ensures dates are in ISO format for Chart.js"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return timezone.localtime(_ensure_aware_datetime(obj)).isoformat()
        return super().default(obj)

from rest_framework.response import Response
from rest_framework.views import APIView

from category.models import PriceType, Category
from change_price.models import PriceHistory
from special_price.models import SpecialPriceType, SpecialPriceHistory
from finalize.models import Finalization, SpecialPriceFinalization
from telegram_app.models import TelegramChannel

from .serializers import (
    PricingResponseSerializer,
)


def _json_safe_float(value):
    """Return a finite float, or None (avoids ValueError in strict JSON encoders)."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _parse_query_datetime(value):
    """Parse ISO date or datetime from query string; return timezone-aware datetime or None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return _ensure_aware_datetime(value)
    text = str(value).strip()
    dt = parse_datetime(text)
    if dt is not None:
        return _ensure_aware_datetime(dt)
    d = parse_date(text)
    if d is not None:
        naive = datetime.combine(d, datetime.min.time())
        try:
            return timezone.make_aware(naive, timezone.get_current_timezone())
        except Exception:
            return timezone.make_aware(naive, dt_timezone.utc)
    return None


def parse_analytics_query_params(request):
    """
    Build window bounds and optional filters from request.GET.
    Defaults: last 30 days ending at now. Enforces max span (settings.ANALYTICS_MAX_RANGE_DAYS).
    """
    max_days = int(getattr(settings, "ANALYTICS_MAX_RANGE_DAYS", 366))
    now = timezone.now()

    end_raw = request.GET.get("end") if request else None
    start_raw = request.GET.get("start") if request else None

    window_end = _parse_query_datetime(end_raw) if end_raw else now
    if window_end is None:
        window_end = now
    if window_end > now:
        window_end = now

    window_start = _parse_query_datetime(start_raw) if start_raw else None
    if window_start is None:
        window_start = window_end - timedelta(days=30)

    if window_start > window_end:
        window_start = window_end - timedelta(days=30)

    span_days = (window_end - window_start).total_seconds() / 86400.0
    if span_days > max_days:
        window_start = window_end - timedelta(days=max_days)

    stats_week_start = max(window_start, window_end - timedelta(days=7))
    trend_window_start = max(window_start, window_end - timedelta(days=90))

    category_id = None
    if request and request.GET.get("category_id"):
        try:
            category_id = int(request.GET["category_id"])
        except (TypeError, ValueError):
            category_id = None

    price_type_ids = None
    if request and request.GET.get("price_type_ids"):
        raw = request.GET.get("price_type_ids", "")
        ids = []
        for part in raw.replace(" ", "").split(","):
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError:
                continue
        price_type_ids = ids if ids else None

    return {
        "window_start": window_start,
        "window_end": window_end,
        "stats_week_start": stats_week_start,
        "trend_window_start": trend_window_start,
        "category_id": category_id,
        "price_type_ids": price_type_ids,
    }


class AnalyticsDashboardView(TemplateView):
    template_name = "analysis/dashboard.html"

    palette = [
        "#2563eb",
        "#f97316",
        "#22c55e",
        "#a855f7",
        "#ef4444",
        "#14b8a6",
        "#facc15",
        "#6366f1",
        "#ec4899",
        "#0ea5e9",
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Determine the time window for the line charts (server HTML dashboard)
        window_end = timezone.now()
        window_start = window_end - timedelta(days=30)
        stats_week_start = max(window_start, window_end - timedelta(days=7))

        # Regular prices
        price_types = self._get_price_types_with_latest_prices()
        timelines = self._build_timelines(price_types, window_start, window_end)
        latest_cards = self._build_latest_cards(price_types)
        price_statistics = self._calculate_price_statistics(
            price_types, window_start, window_end
        )

        # Special prices
        special_price_types = self._get_special_price_types_with_latest()
        special_timelines = self._build_special_timelines(
            special_price_types, window_start, window_end
        )
        special_cards = self._build_special_cards(special_price_types)

        # Category and summary data
        category_summary = self._build_category_summary(latest_cards)
        top_movers = self._derive_top_movers(latest_cards)
        
        # Finalization statistics
        finalization_stats = self._get_finalization_statistics(
            stats_week_start, window_end
        )
        
        # Overall statistics
        overall_stats = self._get_overall_statistics(
            price_types, special_price_types, stats_week_start, window_end
        )

        context.update(
            {
                "generated_at": timezone.now(),
                "latest_cards": latest_cards,
                "special_cards": special_cards,
                "top_movers": top_movers,
                "price_statistics": price_statistics,
                "finalization_stats": finalization_stats,
                "overall_stats": overall_stats,
                "timeline_data_json": json.dumps(timelines, cls=ChartJSONEncoder),
                "special_timeline_data_json": json.dumps(special_timelines, cls=ChartJSONEncoder),
                "category_summary_json": json.dumps(category_summary, cls=ChartJSONEncoder),
            }
        )

        return context

    def get_analytics_data(self, request=None):
        """
        Build analytics data for API consumption.
        Returns a dict with all dashboard metrics (no JSON stringification).
        Optional ``request`` supplies GET params: start, end, category_id, price_type_ids.
        """
        q = parse_analytics_query_params(request)
        window_start = q["window_start"]
        window_end = q["window_end"]
        stats_week_start = q["stats_week_start"]
        trend_window_start = q["trend_window_start"]
        category_id = q["category_id"]
        price_type_ids = q["price_type_ids"]

        price_types = self._get_price_types_with_latest_prices()
        if category_id is not None:
            price_types = price_types.filter(category_id=category_id)
        if price_type_ids is not None:
            price_types = price_types.filter(id__in=price_type_ids)

        timelines = self._build_timelines(price_types, window_start, window_end)
        latest_cards = self._build_latest_cards(price_types)
        price_statistics = self._calculate_price_statistics(
            price_types, window_start, window_end
        )

        special_price_types = self._get_special_price_types_with_latest()
        special_timelines = self._build_special_timelines(
            special_price_types, window_start, window_end
        )
        special_cards = self._build_special_cards(special_price_types)

        category_summary = self._build_category_summary(latest_cards)
        top_movers = self._derive_top_movers(latest_cards)
        finalization_stats = self._get_finalization_statistics(
            stats_week_start, window_end
        )
        overall_stats = self._get_overall_statistics(
            price_types, special_price_types, stats_week_start, window_end
        )
        try:
            telegram_engagement = self._build_telegram_engagement(
                window_start, window_end
            )
        except Exception:
            logger.exception("Failed to build telegram engagement for analytics dashboard")
            telegram_engagement = {"timeline": [], "channels": []}

        try:
            last_updated_price_trend = self._build_last_updated_price_trend(
                trend_window_start, window_end
            )
        except Exception:
            logger.exception("Failed to build last_updated_price_trend")
            last_updated_price_trend = None

        def _serialize_card(card):
            c = dict(card)
            if c.get("timestamp"):
                ts = _ensure_aware_datetime(c["timestamp"])
                c["timestamp"] = timezone.localtime(ts).isoformat() if ts else None
            for num_key in ("latest_price", "change_value", "change_percent"):
                if num_key in c:
                    c[num_key] = _json_safe_float(c.get(num_key))
            return c

        def _serialize_value(v):
            from decimal import Decimal
            if hasattr(v, "isoformat"):  # datetime
                av = _ensure_aware_datetime(v)
                return timezone.localtime(av).isoformat() if av else None
            if isinstance(v, Decimal):
                return _json_safe_float(v)
            if isinstance(v, float):
                return _json_safe_float(v)
            if isinstance(v, dict):
                return {k: _serialize_value(val) for k, val in v.items()}
            if isinstance(v, list):
                return [_serialize_value(item) for item in v]
            return v

        def _serialize_stats(stats):
            if isinstance(stats, dict):
                return {k: _serialize_value(v) for k, v in stats.items()}
            return _serialize_value(stats)

        return {
            "generated_at": timezone.localtime(timezone.now()).isoformat(),
            "range": {
                "start": timezone.localtime(window_start).isoformat(),
                "end": timezone.localtime(window_end).isoformat(),
            },
            "latest_cards": [_serialize_card(c) for c in latest_cards],
            "special_cards": [_serialize_card(c) for c in special_cards],
            "top_movers": [_serialize_card(c) for c in top_movers],
            "price_statistics": _serialize_stats(price_statistics),
            "finalization_stats": _serialize_stats(finalization_stats),
            "overall_stats": _serialize_stats(overall_stats),
            "timeline_data": timelines,
            "special_timeline_data": special_timelines,
            "category_summary": category_summary,
            "telegram_engagement": telegram_engagement,
            "last_updated_price_trend": last_updated_price_trend,
        }

    def _get_price_types_with_latest_prices(self):
        latest_history = (
            PriceHistory.objects.filter(price_type=OuterRef("pk"))
            .order_by("-created_at")
        )
        previous_history = (
            PriceHistory.objects.filter(price_type=OuterRef("pk"))
            .order_by("-created_at")
        )

        price_types = (
            PriceType.objects.select_related(
                "category", "source_currency", "target_currency"
            )
            .annotate(
                latest_price=Subquery(latest_history.values("price")[:1]),
                latest_timestamp=Subquery(latest_history.values("created_at")[:1]),
                previous_price=Subquery(previous_history.values("price")[1:2]),
            )
            .order_by("category__name", "name")
        )
        return price_types

    def _build_timelines(self, price_types, window_start, window_end):
        relevant_ids = [pt.id for pt in price_types if pt.latest_price is not None]
        
        if not relevant_ids:
            return []

        history_qs = (
            PriceHistory.objects.filter(price_type_id__in=relevant_ids)
            .annotate(
                effective_ts=Coalesce(
                    "event_at",
                    "created_at",
                    output_field=DateTimeField(),
                )
            )
            .filter(effective_ts__gte=window_start, effective_ts__lte=window_end)
            .select_related(
                "price_type",
                "price_type__category",
                "price_type__source_currency",
                "price_type__target_currency",
            )
            .order_by("price_type_id", "effective_ts")
        )

        timeline_map = defaultdict(list)
        for history in history_qs:
            # Convert datetime to ISO string for Chart.js compatibility
            ts = _ensure_aware_datetime(history.effective_ts)
            timestamp = timezone.localtime(ts).isoformat() if ts else ""
            timeline_map[history.price_type_id].append(
                {
                    "x": timestamp,
                    "y": _json_safe_float(history.price) or 0.0,
                }
            )

        datasets = []
        for index, price_type in enumerate(price_types):
            data_points = timeline_map.get(price_type.id)
            if not data_points or len(data_points) == 0:
                continue

            color = self.palette[index % len(self.palette)]
            datasets.append(
                {
                    "label": f"{price_type.source_currency.code}/{price_type.target_currency.code} {price_type.get_trade_type_display()}",
                    "category": price_type.category.name,
                    # Parts of `label`, so the panel can show it in the viewer's language.
                    "pair": f"{price_type.source_currency.code}/{price_type.target_currency.code}",
                    "trade_type": price_type.trade_type,
                    "is_special": False,
                    "data": data_points,
                    "borderColor": color,
                    "backgroundColor": f"{color}33",
                    "tension": 0.35,
                    "fill": False,
                }
            )

        return datasets

    def _build_last_updated_price_trend(self, window_start, window_end):
        """
        Single-series timeline for the regular or special price row that was updated most recently.
        Used by the dashboard Price Trends chart (full history within ``window_start``).
        """
        latest_regular = (
            PriceHistory.objects.select_related(
                "price_type",
                "price_type__category",
                "price_type__source_currency",
                "price_type__target_currency",
            )
            .order_by("-created_at")
            .first()
        )
        latest_special = (
            SpecialPriceHistory.objects.select_related(
                "special_price_type",
                "special_price_type__source_currency",
                "special_price_type__target_currency",
            )
            .order_by("-created_at")
            .first()
        )

        pick_regular = None
        if latest_regular and latest_special:
            pick_regular = latest_regular.created_at >= latest_special.created_at
        elif latest_regular:
            pick_regular = True
        elif latest_special:
            pick_regular = False
        else:
            return None

        if pick_regular:
            pt = latest_regular.price_type
            histories = (
                PriceHistory.objects.filter(price_type_id=pt.id)
                .annotate(
                    effective_ts=Coalesce(
                        "event_at",
                        "created_at",
                        output_field=DateTimeField(),
                    )
                )
                .filter(effective_ts__gte=window_start, effective_ts__lte=window_end)
                .order_by("effective_ts")
            )
            label = (
                f"{pt.name} — {pt.source_currency.code}/{pt.target_currency.code} "
                f"{pt.get_trade_type_display()}"
            )
            data = []
            for h in histories:
                ts = _ensure_aware_datetime(h.effective_ts)
                timestamp = timezone.localtime(ts).isoformat() if ts else ""
                data.append(
                    {
                        "x": timestamp,
                        "y": _json_safe_float(h.price) or 0.0,
                    }
                )
            if not data:
                return None
            return {
                "kind": "regular",
                "price_type_id": pt.id,
                "label": label,
                "data": data,
            }

        spt = latest_special.special_price_type
        histories = (
            SpecialPriceHistory.objects.filter(special_price_type_id=spt.id)
            .annotate(
                effective_ts=Coalesce(
                    "event_at",
                    "created_at",
                    output_field=DateTimeField(),
                )
            )
            .filter(effective_ts__gte=window_start, effective_ts__lte=window_end)
            .order_by("effective_ts")
        )
        label = (
            f"{spt.name} — {spt.source_currency.code}/{spt.target_currency.code} "
            f"{spt.get_trade_type_display()} [Special]"
        )
        data = []
        for h in histories:
            ts = _ensure_aware_datetime(h.effective_ts)
            timestamp = timezone.localtime(ts).isoformat() if ts else ""
            data.append(
                {
                    "x": timestamp,
                    "y": _json_safe_float(h.price) or 0.0,
                }
            )
        if not data:
            return None
        return {
            "kind": "special",
            "special_price_type_id": spt.id,
            "label": label,
            "data": data,
        }

    def _build_latest_cards(self, price_types):
        cards = []

        for price_type in price_types:
            if price_type.latest_price is None:
                continue

            latest_price = float(price_type.latest_price)
            previous_price = (
                float(price_type.previous_price)
                if price_type.previous_price is not None
                else None
            )

            change_value = (
                latest_price - previous_price if previous_price is not None else None
            )
            change_percent = (
                (change_value / previous_price * 100)
                if previous_price not in (None, 0)
                else None
            )
            change_percent = _json_safe_float(change_percent)

            cards.append(
                {
                    "id": price_type.id,
                    "name": price_type.name,
                    "category": price_type.category.name,
                    "pair": f"{price_type.source_currency.code}/{price_type.target_currency.code}",
                    "trade": price_type.get_trade_type_display(),
                    "latest_price": latest_price,
                    "timestamp": price_type.latest_timestamp,
                    "change_value": _json_safe_float(change_value),
                    "change_percent": change_percent,
                }
            )

        return cards

    def _build_category_summary(self, latest_cards):
        summary_map = defaultdict(list)

        for card in latest_cards:
            summary_map[card["category"]].append(card["latest_price"])

        summary = []
        for category, prices in summary_map.items():
            summary.append(
                {
                    "category": category,
                    "count": len(prices),
                    "average_price": sum(prices) / len(prices) if prices else 0,
                    "max_price": max(prices) if prices else 0,
                    "min_price": min(prices) if prices else 0,
                }
            )

        summary.sort(key=lambda item: item["count"], reverse=True)
        return summary

    def _derive_top_movers(self, latest_cards):
        candidates = [
            card for card in latest_cards if card["change_percent"] is not None
        ]
        candidates.sort(key=lambda card: abs(card["change_percent"]), reverse=True)
        return candidates[:5]  # Show top 5 instead of 3
    
    def _get_special_price_types_with_latest(self):
        """Get special price types with their latest prices."""
        latest_history = (
            SpecialPriceHistory.objects.filter(special_price_type=OuterRef("pk"))
            .order_by("-created_at")
        )
        previous_history = (
            SpecialPriceHistory.objects.filter(special_price_type=OuterRef("pk"))
            .order_by("-created_at")
        )

        special_price_types = (
            SpecialPriceType.objects.select_related(
                "source_currency", "target_currency"
            )
            .annotate(
                latest_price=Subquery(latest_history.values("price")[:1]),
                latest_timestamp=Subquery(latest_history.values("created_at")[:1]),
                previous_price=Subquery(previous_history.values("price")[1:2]),
            )
            .order_by("name")
        )
        return special_price_types
    
    def _build_special_timelines(self, special_price_types, window_start, window_end):
        """Build timeline data for special prices."""
        relevant_ids = [spt.id for spt in special_price_types if spt.latest_price is not None]
        
        if not relevant_ids:
            return []

        history_qs = (
            SpecialPriceHistory.objects.filter(special_price_type_id__in=relevant_ids)
            .annotate(
                effective_ts=Coalesce(
                    "event_at",
                    "created_at",
                    output_field=DateTimeField(),
                )
            )
            .filter(effective_ts__gte=window_start, effective_ts__lte=window_end)
            .select_related(
                "special_price_type",
                "special_price_type__source_currency",
                "special_price_type__target_currency",
            )
            .order_by("special_price_type_id", "effective_ts")
        )

        timeline_map = defaultdict(list)
        for history in history_qs:
            # Convert datetime to ISO string for Chart.js compatibility
            ts = _ensure_aware_datetime(history.effective_ts)
            timestamp = timezone.localtime(ts).isoformat() if ts else ""
            timeline_map[history.special_price_type_id].append(
                {
                    "x": timestamp,
                    "y": _json_safe_float(history.price) or 0.0,
                }
            )

        datasets = []
        for index, special_price_type in enumerate(special_price_types):
            data_points = timeline_map.get(special_price_type.id)
            if not data_points or len(data_points) == 0:
                continue

            color = self.palette[(index + 5) % len(self.palette)]  # Different color range
            datasets.append(
                {
                    "label": f"{special_price_type.source_currency.code}/{special_price_type.target_currency.code} {special_price_type.get_trade_type_display()} (Special)",
                    "category": "Special Prices",
                    "pair": f"{special_price_type.source_currency.code}/{special_price_type.target_currency.code}",
                    "trade_type": special_price_type.trade_type,
                    "is_special": True,
                    "data": data_points,
                    "borderColor": color,
                    "backgroundColor": f"{color}33",
                    "tension": 0.35,
                    "fill": False,
                    "borderDash": [5, 5],  # Dashed line for special prices
                }
            )

        return datasets
    
    def _build_special_cards(self, special_price_types):
        """Build card data for special prices."""
        cards = []

        for special_price_type in special_price_types:
            if special_price_type.latest_price is None:
                continue

            latest_price = float(special_price_type.latest_price)
            previous_price = (
                float(special_price_type.previous_price)
                if special_price_type.previous_price is not None
                else None
            )

            change_value = (
                latest_price - previous_price if previous_price is not None else None
            )
            change_percent = (
                (change_value / previous_price * 100)
                if previous_price not in (None, 0)
                else None
            )
            change_percent = _json_safe_float(change_percent)

            cards.append(
                {
                    "id": special_price_type.id,
                    "name": special_price_type.name,
                    "pair": f"{special_price_type.source_currency.code}/{special_price_type.target_currency.code}",
                    "trade": special_price_type.get_trade_type_display(),
                    "latest_price": latest_price,
                    "timestamp": special_price_type.latest_timestamp,
                    "change_value": _json_safe_float(change_value),
                    "change_percent": change_percent,
                    "is_special": True,
                }
            )

        return cards
    
    def _calculate_price_statistics(self, price_types, window_start, window_end):
        """Calculate advanced statistics for prices."""
        stats = {}
        
        for price_type in price_types:
            if price_type.latest_price is None:
                continue
            
            histories = (
                PriceHistory.objects.filter(price_type=price_type)
                .annotate(
                    effective_ts=Coalesce(
                        "event_at",
                        "created_at",
                        output_field=DateTimeField(),
                    )
                )
                .filter(effective_ts__gte=window_start, effective_ts__lte=window_end)
                .order_by("effective_ts")
            )
            
            if histories.count() < 2:
                continue
            
            prices = [float(h.price) for h in histories]
            
            # Calculate statistics manually
            n = len(prices)
            avg_price = sum(prices) / n if n > 0 else 0
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            
            # Calculate standard deviation (volatility)
            if n > 1:
                variance = sum((p - avg_price) ** 2 for p in prices) / (n - 1)
                variance = max(0.0, float(variance))
                volatility = math.sqrt(variance)
            else:
                volatility = 0
            
            price_stats = {
                "price_type_id": price_type.id,
                "price_type_name": price_type.name,
                "category": price_type.category.name,
                "current_price": float(price_type.latest_price),
                "average": avg_price,
                "min": min_price,
                "max": max_price,
                "volatility": volatility,
                "price_range": max_price - min_price,
                "data_points": n,
            }
            
            # Calculate trend (simple linear regression slope)
            if n > 1:
                x = list(range(n))
                x_mean = sum(x) / n
                y_mean = avg_price
                
                numerator = sum((x[i] - x_mean) * (prices[i] - y_mean) for i in range(n))
                denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
                
                slope = numerator / denominator if denominator != 0 else 0
                price_stats["trend_slope"] = slope
                price_stats["trend_direction"] = "up" if slope > 0.01 else ("down" if slope < -0.01 else "flat")
            else:
                price_stats["trend_slope"] = 0
                price_stats["trend_direction"] = "flat"
            
            stats[price_type.id] = price_stats
        
        return stats
    
    def _get_finalization_statistics(self, week_start, window_end):
        """Get statistics about finalizations."""
        total_finalizations = Finalization.objects.count()
        week_finalizations = Finalization.objects.filter(
            finalized_at__gte=week_start,
            finalized_at__lte=window_end,
        ).count()
        
        successful_telegram = Finalization.objects.filter(message_sent=True).count()
        failed_telegram = Finalization.objects.filter(message_sent=False).count()
        
        special_finalizations = SpecialPriceFinalization.objects.count()
        week_special = SpecialPriceFinalization.objects.filter(
            finalized_at__gte=week_start,
            finalized_at__lte=window_end,
        ).count()
        
        # Get most active categories
        category_stats = (
            Finalization.objects.values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        # Get most active channels
        channel_stats = (
            Finalization.objects.filter(channel__isnull=False)
            .values('channel__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        return {
            "total_finalizations": total_finalizations,
            "week_finalizations": week_finalizations,
            "successful_telegram": successful_telegram,
            "failed_telegram": failed_telegram,
            "special_finalizations": special_finalizations,
            "week_special": week_special,
            "category_stats": list(category_stats),
            "channel_stats": list(channel_stats),
        }
    
    def _get_overall_statistics(
        self, price_types, special_price_types, week_start, window_end
    ):
        """Get overall system statistics."""
        total_price_updates = PriceHistory.objects.count()
        week_price_updates = PriceHistory.objects.filter(
            created_at__gte=week_start,
            created_at__lte=window_end,
        ).count()
        
        total_special_updates = SpecialPriceHistory.objects.count()
        week_special_updates = SpecialPriceHistory.objects.filter(
            created_at__gte=week_start,
            created_at__lte=window_end,
        ).count()
        
        active_categories = Category.objects.count()
        active_price_types = PriceType.objects.count()
        active_special_types = SpecialPriceType.objects.count()
        
        active_channels = TelegramChannel.objects.filter(is_active=True).count()
        
        return {
            "total_price_updates": total_price_updates,
            "week_price_updates": week_price_updates,
            "total_special_updates": total_special_updates,
            "week_special_updates": week_special_updates,
            "active_categories": active_categories,
            "active_price_types": active_price_types,
            "active_special_types": active_special_types,
            "active_channels": active_channels,
        }

    def _build_telegram_engagement(self, window_start, window_end):
        """
        Build engagement statistics for Telegram publications.

        Returns a dict with:
        - ``timeline``: chart-ready datasets (same shape as price timelines)
        - ``channels``: per-channel aggregates (total, success, failed, success_rate, last_post_at)
        """

        def _day_bucket_iso(day):
            """ISO timestamp for chart x-axis; avoids make_aware edge cases."""
            try:
                naive_mid = datetime.combine(day, datetime.min.time())
                aware = timezone.make_aware(
                    naive_mid, timezone.get_current_timezone()
                )
                return timezone.localtime(aware).isoformat()
            except Exception:
                return day.isoformat()

        # ── Timeline: DB-level aggregation per day (no Python iteration over rows) ──
        window_filter = {"finalized_at__gte": window_start, "finalized_at__lte": window_end}

        final_by_day = (
            Finalization.objects.filter(**window_filter)
            .annotate(day=TruncDate("finalized_at"))
            .values("day")
            .annotate(
                success=Sum(Case(When(message_sent=True, then=1), default=0, output_field=IntegerField())),
                failed=Sum(Case(When(message_sent=False, then=1), default=0, output_field=IntegerField())),
            )
        )

        special_by_day = (
            SpecialPriceFinalization.objects.filter(**window_filter)
            .annotate(day=TruncDate("finalized_at"))
            .values("day")
            .annotate(
                success=Sum(Case(When(message_sent=True, then=1), default=0, output_field=IntegerField())),
                failed=Sum(Case(When(message_sent=False, then=1), default=0, output_field=IntegerField())),
            )
        )

        day_buckets = defaultdict(lambda: {"success": 0, "failed": 0})
        for row in final_by_day:
            d = row["day"]
            if d is None:
                continue
            day_buckets[d]["success"] += row["success"] or 0
            day_buckets[d]["failed"] += row["failed"] or 0
        for row in special_by_day:
            d = row["day"]
            if d is None:
                continue
            day_buckets[d]["success"] += row["success"] or 0
            day_buckets[d]["failed"] += row["failed"] or 0

        success_points = []
        failed_points = []
        for day in sorted(day_buckets.keys()):
            iso = _day_bucket_iso(day)
            bucket = day_buckets[day]
            if bucket["success"]:
                success_points.append({"x": iso, "y": bucket["success"]})
            if bucket["failed"]:
                failed_points.append({"x": iso, "y": bucket["failed"]})

        timeline = []
        if success_points:
            timeline.append(
                {
                    "label": "Successful posts",
                    "data": success_points,
                    "borderColor": "#22c55e",
                    "backgroundColor": "#22c55e33",
                    "tension": 0.35,
                    "fill": False,
                }
            )
        if failed_points:
            timeline.append(
                {
                    "label": "Failed posts",
                    "data": failed_points,
                    "borderColor": "#ef4444",
                    "backgroundColor": "#ef444433",
                    "tension": 0.35,
                    "fill": False,
                }
            )

        # ── Channels: DB-level aggregation (no Python iteration over all rows) ──
        final_channel_rows = (
            Finalization.objects.filter(channel__isnull=False)
            .values("channel_id", "channel__name")
            .annotate(
                total=Count("id"),
                success=Sum(Case(When(message_sent=True, then=1), default=0, output_field=IntegerField())),
                failed=Sum(Case(When(message_sent=False, then=1), default=0, output_field=IntegerField())),
                last_post_at=Max("finalized_at"),
            )
        )

        special_channel_rows = (
            SpecialPriceFinalization.objects.filter(channel__isnull=False)
            .values("channel_id", "channel__name")
            .annotate(
                total=Count("id"),
                success=Sum(Case(When(message_sent=True, then=1), default=0, output_field=IntegerField())),
                failed=Sum(Case(When(message_sent=False, then=1), default=0, output_field=IntegerField())),
                last_post_at=Max("finalized_at"),
            )
        )

        channel_stats = {}
        for row in final_channel_rows:
            ch_id = row["channel_id"]
            entry = channel_stats.setdefault(
                ch_id,
                {
                    "channel_id": ch_id,
                    "channel_name": (row.get("channel__name") or ""),
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "last_post_at": None,
                },
            )
            entry["total"] += row["total"] or 0
            entry["success"] += row["success"] or 0
            entry["failed"] += row["failed"] or 0
            rlast = row["last_post_at"]
            if rlast and (not entry["last_post_at"] or rlast > entry["last_post_at"]):
                entry["last_post_at"] = rlast

        for row in special_channel_rows:
            ch_id = row["channel_id"]
            entry = channel_stats.setdefault(
                ch_id,
                {
                    "channel_id": ch_id,
                    "channel_name": (row.get("channel__name") or ""),
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "last_post_at": None,
                },
            )
            entry["total"] += row["total"] or 0
            entry["success"] += row["success"] or 0
            entry["failed"] += row["failed"] or 0
            rlast = row["last_post_at"]
            if rlast and (not entry["last_post_at"] or rlast > entry["last_post_at"]):
                entry["last_post_at"] = rlast

        channels = []
        for entry in channel_stats.values():
            total = entry["total"] or 1
            success_rate = _json_safe_float(entry["success"] / total) or 0.0
            last_ts = entry["last_post_at"]
            channels.append(
                {
                    "channel_id": entry["channel_id"],
                    "channel_name": entry["channel_name"],
                    "total": entry["total"],
                    "success": entry["success"],
                    "failed": entry["failed"],
                    "success_rate": success_rate,
                    "last_post_at": timezone.localtime(
                        _ensure_aware_datetime(last_ts)
                    ).isoformat()
                    if last_ts
                    else None,
                }
            )

        channels.sort(key=lambda c: c["total"], reverse=True)

        return {
            "timeline": timeline,
            "channels": channels,
        }


class PricingDataAPIView(APIView):
    """
    Read-only API endpoint that exposes pricing data as JSON.

    Response structure (high level):
    {
        "generated_at": "<ISO8601 datetime>",
        "categories": [
            {
                "id": 1,
                "name": "Cash",
                "slug": "cash",
                "description": "...",
                "items": [
                    {
                        "id": 10,
                        "name": "USD / IRR Buy",
                        "pair": "USD/IRR",
                        "trade_type": "Buy",
                        "latest_price": 123.45,
                        "latest_price_timestamp": "..."
                    },
                    ...
                ]
            },
            {
                "id": null,
                "name": "Special Prices",
                "slug": "special-prices",
                "description": "Special prices with updates in the last 6 hours.",
                "items": [
                    {
                        "id": 5,
                        "name": "Special Pound",
                        "pair": "GBP/IRR",
                        "trade_type": "Buy",
                        "latest_special_price": 50000.0,
                        "latest_special_price_timestamp": "..."
                    },
                    ...
                ]
            }
        ]
    }

    Key behaviours:
    - The endpoint is GET-only and read-only.
    - All categories are always returned, even if they currently have no items.
    - Items that come from special prices are only included if their
      special_price has been updated in the last 6 hours.

    Security:
    - No authentication/permission classes are enforced here to keep the
      endpoint simple and read-only.
    - Project can enable authentication, permissions, and throttling below
      according to deployment needs.
    """

    # Optional security placeholders — project can uncomment/configure as needed.
    authentication_classes = []  # e.g. [SessionAuthentication, TokenAuthentication]
    permission_classes = []  # e.g. [IsAuthenticated]

    # Example throttling configuration (disabled by default):
    # from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
    #
    # class ReadOnlyAnonThrottle(AnonRateThrottle):
    #     scope = "readonly_anon"
    #
    # class ReadOnlyUserThrottle(UserRateThrottle):
    #     scope = "readonly_user"
    #
    # throttle_classes = [ReadOnlyAnonThrottle, ReadOnlyUserThrottle]

    # Note: CORS should be configured globally via middleware/settings
    # (e.g. django-cors-headers). This view is CORS-agnostic by design.

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests and return a JSON payload with categories and pricing.
        """
        now = timezone.now()
        cutoff = now - timedelta(hours=6)

        category_items = self._build_category_items()
        special_items = self._build_special_price_items(cutoff=cutoff)

        # Build list of all real categories
        categories_payload = []
        for category in Category.objects.all().order_by("name"):
            categories_payload.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "description": category.description,
                    "items": category_items.get(category.id, []),
                }
            )

        # Add synthetic "Special Prices" category.
        # This keeps the response consistent: all "items that have special_price"
        # are surfaced together and filtered to the last 6 hours.
        categories_payload.append(
            {
                "id": None,
                "name": "Special Prices",
                "slug": "special-prices",
                "description": "Special price types with updates in the last 6 hours.",
                "items": special_items,
            }
        )

        payload = {
            "generated_at": now,
            "categories": categories_payload,
        }

        serializer = PricingResponseSerializer(payload)
        return Response(serializer.data)

    def _build_category_items(self):
        """
        Build a mapping of category_id -> list[price item dict].

        - Uses `PriceType` and its latest `PriceHistory` to build
          category items.
        - Categories are *not* filtered by recency; consumers can do that
          on the client if needed.
        """
        latest_history = (
            PriceHistory.objects.filter(price_type=OuterRef("pk"))
            .order_by("-created_at")
        )

        price_types = (
            PriceType.objects.select_related(
                "category", "source_currency", "target_currency"
            )
            .annotate(
                latest_price=Subquery(latest_history.values("price")[:1]),
                latest_timestamp=Subquery(latest_history.values("created_at")[:1]),
            )
            .order_by("category__name", "name")
        )

        items_by_category = defaultdict(list)
        
        # Group price types by category for sorting
        price_types_by_category = defaultdict(list)
        for pt in price_types:
            price_types_by_category[pt.category_id].append(pt)
        
        # Sort price types within GBP categories
        for category_id, pts in price_types_by_category.items():
            category = pts[0].category
            category_name_lower = category.name.lower()
            if 'پوند' in category.name or 'pound' in category_name_lower or 'gbp' in category_name_lower:
                # Import sort function
                from finalize.views import sort_gbp_price_types
                price_types_by_category[category_id] = sort_gbp_price_types(pts)
        
        # Flatten back to list maintaining category order
        price_types = []
        for category_id in sorted(price_types_by_category.keys()):
            price_types.extend(price_types_by_category[category_id])

        for pt in price_types:
            # Skip types that have never had a price recorded.
            if pt.latest_price is None:
                continue

            items_by_category[pt.category_id].append(
                {
                    "id": pt.id,
                    "name": pt.name,
                    "pair": f"{pt.source_currency.code}/{pt.target_currency.code}",
                    "trade_type": pt.get_trade_type_display(),
                    "latest_price": pt.latest_price,
                    "latest_price_timestamp": pt.latest_timestamp,
                }
            )

        return items_by_category

    def _build_special_price_items(self, cutoff):
        """
        Build a list of special price items, filtered to the last 6 hours.

        - Uses `SpecialPriceType` and `SpecialPriceHistory`.
        - Only includes items where there is at least one SpecialPriceHistory
          with `created_at >= cutoff`.

        If your project later associates special prices directly with
        categories or price types (e.g. via a ForeignKey), you can adapt
        this function to group them differently while keeping the response
        structure intact.
        """
        latest_special_history = (
            SpecialPriceHistory.objects.filter(
                special_price_type=OuterRef("pk"),
                created_at__gte=cutoff,
            )
            .order_by("-created_at")
        )

        special_price_types = (
            SpecialPriceType.objects.select_related(
                "source_currency", "target_currency"
            )
            .annotate(
                latest_price=Subquery(latest_special_history.values("price")[:1]),
                latest_timestamp=Subquery(
                    latest_special_history.values("created_at")[:1]
                ),
            )
            # Only keep types that actually have a recent special_price
            .filter(latest_price__isnull=False)
            .order_by("name")
        )

        items = []
        for spt in special_price_types:
            items.append(
                {
                    "id": spt.id,
                    "name": spt.name,
                    "pair": f"{spt.source_currency.code}/{spt.target_currency.code}",
                    "trade_type": spt.get_trade_type_display(),
                    "latest_special_price": spt.latest_price,
                    "latest_special_price_timestamp": spt.latest_timestamp,
                }
            )

        return items

