"""
Analysis business logic: dashboard analytics and pricing API data.
Moved out of views to keep views thin and testable.
"""
import math
from collections import defaultdict
from datetime import timedelta

from django.db.models import OuterRef, Subquery, Count
from django.utils import timezone

from category.models import PriceType, Category
from change_price.models import PriceHistory
from special_price.models import SpecialPriceType, SpecialPriceHistory
from finalize.models import Finalization, SpecialPriceFinalization
from telegram_app.models import TelegramChannel

from core.sorting import sort_gbp_price_types


ANALYTICS_PALETTE = [
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


def get_price_types_with_latest_prices():
    latest_history = (
        PriceHistory.objects.filter(price_type=OuterRef("pk"))
        .order_by("-created_at")
    )
    previous_history = (
        PriceHistory.objects.filter(price_type=OuterRef("pk"))
        .order_by("-created_at")
    )
    return (
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


def build_timelines(price_types, window_start, palette=None):
    palette = palette or ANALYTICS_PALETTE
    relevant_ids = [pt.id for pt in price_types if pt.latest_price is not None]
    if not relevant_ids:
        return []

    history_qs = (
        PriceHistory.objects.filter(
            price_type_id__in=relevant_ids, created_at__gte=window_start
        )
        .select_related(
            "price_type",
            "price_type__category",
            "price_type__source_currency",
            "price_type__target_currency",
        )
        .order_by("price_type_id", "created_at")
    )

    timeline_map = defaultdict(list)
    for history in history_qs:
        timestamp = timezone.localtime(history.created_at).isoformat()
        timeline_map[history.price_type_id].append(
            {"x": timestamp, "y": float(history.price)}
        )

    datasets = []
    for index, price_type in enumerate(price_types):
        data_points = timeline_map.get(price_type.id)
        if not data_points:
            continue
        color = palette[index % len(palette)]
        datasets.append(
            {
                "label": f"{price_type.source_currency.code}/{price_type.target_currency.code} {price_type.get_trade_type_display()}",
                "category": price_type.category.name,
                "data": data_points,
                "borderColor": color,
                "backgroundColor": f"{color}33",
                "tension": 0.35,
                "fill": False,
            }
        )
    return datasets


def build_latest_cards(price_types):
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
        cards.append(
            {
                "id": price_type.id,
                "name": price_type.name,
                "category": price_type.category.name,
                "pair": f"{price_type.source_currency.code}/{price_type.target_currency.code}",
                "trade": price_type.get_trade_type_display(),
                "latest_price": latest_price,
                "timestamp": price_type.latest_timestamp,
                "change_value": change_value,
                "change_percent": change_percent,
            }
        )
    return cards


def build_category_summary(latest_cards):
    summary_map = defaultdict(list)
    for card in latest_cards:
        summary_map[card["category"]].append(card["latest_price"])
    summary = [
        {
            "category": category,
            "count": len(prices),
            "average_price": sum(prices) / len(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
            "min_price": min(prices) if prices else 0,
        }
        for category, prices in summary_map.items()
    ]
    summary.sort(key=lambda item: item["count"], reverse=True)
    return summary


def derive_top_movers(latest_cards, limit=5):
    candidates = [
        card for card in latest_cards if card["change_percent"] is not None
    ]
    candidates.sort(key=lambda card: abs(card["change_percent"]), reverse=True)
    return candidates[:limit]


def get_special_price_types_with_latest():
    latest_history = (
        SpecialPriceHistory.objects.filter(special_price_type=OuterRef("pk"))
        .order_by("-created_at")
    )
    previous_history = (
        SpecialPriceHistory.objects.filter(special_price_type=OuterRef("pk"))
        .order_by("-created_at")
    )
    return (
        SpecialPriceType.objects.select_related(
            "source_currency", "target_currency"
        )
        .annotate(
            latest_price=Subquery(latest_history.values("price")[:1]),
            latest_timestamp=Subquery(latest_history.values("created_at")[:1]),
            previous_price=Subquery(previous_history.values("price")[1:2]),
            latest_cash_price=Subquery(latest_history.values("cash_price")[:1]),
            latest_account_price=Subquery(
                latest_history.values("account_price")[:1]
            ),
        )
        .order_by("name")
    )


def build_special_timelines(special_price_types, window_start, palette=None):
    palette = palette or ANALYTICS_PALETTE
    relevant_ids = [
        spt.id for spt in special_price_types if spt.latest_price is not None
    ]
    if not relevant_ids:
        return []

    history_qs = (
        SpecialPriceHistory.objects.filter(
            special_price_type_id__in=relevant_ids,
            created_at__gte=window_start,
        )
        .select_related(
            "special_price_type",
            "special_price_type__source_currency",
            "special_price_type__target_currency",
        )
        .order_by("special_price_type_id", "created_at")
    )

    timeline_map = defaultdict(list)
    for history in history_qs:
        timestamp = timezone.localtime(history.created_at).isoformat()
        timeline_map[history.special_price_type_id].append(
            {"x": timestamp, "y": float(history.price)}
        )

    datasets = []
    for index, special_price_type in enumerate(special_price_types):
        data_points = timeline_map.get(special_price_type.id)
        if not data_points:
            continue
        color = palette[(index + 5) % len(palette)]
        datasets.append(
            {
                "label": f"{special_price_type.source_currency.code}/{special_price_type.target_currency.code} {special_price_type.get_trade_type_display()} (Special)",
                "category": "Special Prices",
                "data": data_points,
                "borderColor": color,
                "backgroundColor": f"{color}33",
                "tension": 0.35,
                "fill": False,
                "borderDash": [5, 5],
            }
        )
    return datasets


def build_special_cards(special_price_types):
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
        cards.append(
            {
                "id": special_price_type.id,
                "name": special_price_type.name,
                "pair": f"{special_price_type.source_currency.code}/{special_price_type.target_currency.code}",
                "trade": special_price_type.get_trade_type_display(),
                "latest_price": latest_price,
                "timestamp": special_price_type.latest_timestamp,
                "change_value": change_value,
                "change_percent": change_percent,
                "is_special": True,
            }
        )
    return cards


def calculate_price_statistics(price_types, window_start):
    stats = {}
    for price_type in price_types:
        if price_type.latest_price is None:
            continue
        histories = PriceHistory.objects.filter(
            price_type=price_type, created_at__gte=window_start
        ).order_by("created_at")
        if histories.count() < 2:
            continue
        prices = [float(h.price) for h in histories]
        n = len(prices)
        avg_price = sum(prices) / n if n > 0 else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        volatility = (
            math.sqrt(
                sum((p - avg_price) ** 2 for p in prices) / (n - 1)
            )
            if n > 1
            else 0
        )
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
        if n > 1:
            x = list(range(n))
            x_mean = sum(x) / n
            y_mean = avg_price
            numerator = sum(
                (x[i] - x_mean) * (prices[i] - y_mean) for i in range(n)
            )
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
            slope = numerator / denominator if denominator != 0 else 0
            price_stats["trend_slope"] = slope
            price_stats["trend_direction"] = (
                "up"
                if slope > 0.01
                else ("down" if slope < -0.01 else "flat")
            )
        else:
            price_stats["trend_slope"] = 0
            price_stats["trend_direction"] = "flat"
        stats[price_type.id] = price_stats
    return stats


def get_finalization_statistics(week_start):
    total_finalizations = Finalization.objects.count()
    week_finalizations = Finalization.objects.filter(
        finalized_at__gte=week_start
    ).count()
    successful_telegram = Finalization.objects.filter(
        message_sent=True
    ).count()
    failed_telegram = Finalization.objects.filter(message_sent=False).count()
    special_finalizations = SpecialPriceFinalization.objects.count()
    week_special = SpecialPriceFinalization.objects.filter(
        finalized_at__gte=week_start
    ).count()
    category_stats = (
        Finalization.objects.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )
    channel_stats = (
        Finalization.objects.filter(channel__isnull=False)
        .values("channel__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
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


def get_overall_statistics(price_types, special_price_types, week_start):
    total_price_updates = PriceHistory.objects.count()
    week_price_updates = PriceHistory.objects.filter(
        created_at__gte=week_start
    ).count()
    total_special_updates = SpecialPriceHistory.objects.count()
    week_special_updates = SpecialPriceHistory.objects.filter(
        created_at__gte=week_start
    ).count()
    return {
        "total_price_updates": total_price_updates,
        "week_price_updates": week_price_updates,
        "total_special_updates": total_special_updates,
        "week_special_updates": week_special_updates,
        "active_categories": Category.objects.count(),
        "active_price_types": PriceType.objects.count(),
        "active_special_types": SpecialPriceType.objects.count(),
        "active_channels": TelegramChannel.objects.filter(
            is_active=True
        ).count(),
    }


def build_category_items():
    """Build category_id -> list of price item dicts for the pricing API."""
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
            latest_timestamp=Subquery(
                latest_history.values("created_at")[:1]
            ),
        )
        .order_by("category__name", "name")
    )
    price_types_by_category = defaultdict(list)
    for pt in price_types:
        price_types_by_category[pt.category_id].append(pt)
    for category_id, pts in price_types_by_category.items():
        category = pts[0].category
        name_lower = (category.name or "").lower()
        if (
            "پوند" in (category.name or "")
            or "pound" in name_lower
            or "gbp" in name_lower
        ):
            price_types_by_category[category_id] = sort_gbp_price_types(pts)
    items_by_category = defaultdict(list)
    for category_id in sorted(price_types_by_category.keys()):
        for pt in price_types_by_category[category_id]:
            if pt.latest_price is None:
                continue
            items_by_category[category_id].append(
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


def build_special_price_items(cutoff):
    """Build list of special price items updated after cutoff."""
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
            latest_price=Subquery(
                latest_special_history.values("price")[:1]
            ),
            latest_timestamp=Subquery(
                latest_special_history.values("created_at")[:1]
            ),
            latest_cash_price=Subquery(
                latest_special_history.values("cash_price")[:1]
            ),
            latest_account_price=Subquery(
                latest_special_history.values("account_price")[:1]
            ),
        )
        .filter(latest_price__isnull=False)
        .order_by("name")
    )
    return [
        {
            "id": spt.id,
            "name": spt.name,
            "pair": f"{spt.source_currency.code}/{spt.target_currency.code}",
            "trade_type": spt.get_trade_type_display(),
            "latest_special_price": spt.latest_price,
            "latest_special_price_timestamp": spt.latest_timestamp,
            "is_double_price": getattr(spt, "is_double_price", False),
            "cash_price": getattr(spt, "latest_cash_price", None),
            "account_price": getattr(spt, "latest_account_price", None),
        }
        for spt in special_price_types
    ]
