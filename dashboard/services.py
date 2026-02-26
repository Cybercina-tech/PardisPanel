"""
Dashboard business logic: home and dashboard2 context building.
Keeps views thin and logic testable.
"""
from datetime import timedelta
from django.db.models import Prefetch, Count
from django.utils import timezone

from category.models import Category, PriceType
from change_price.models import PriceHistory
from telegram_app.models import TelegramBot, TelegramChannel
from special_price.models import SpecialPriceType, SpecialPriceHistory

from core.sorting import sort_categories


def get_home_context():
    """Build context for dashboard/dashboard.html (home)."""
    categories = Category.objects.prefetch_related(
        "price_types",
        "price_types__price_histories",
    ).all()
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)

    highest_price_obj = (
        PriceHistory.objects.select_related("price_type")
        .order_by("-price")
        .first()
    )
    highest_price = float(highest_price_obj.price) if highest_price_obj else 0
    highest_price_label = (
        highest_price_obj.price_type.name if highest_price_obj else "N/A"
    )

    price_changes = []
    price_types = PriceType.objects.prefetch_related("price_histories").all()
    for price_type in price_types:
        latest = price_type.price_histories.first()
        if not latest:
            continue
        old = (
            price_type.price_histories.filter(
                created_at__lte=twenty_four_hours_ago
            )
            .order_by("-created_at")
            .first()
        )
        if (
            old
            and latest.created_at > twenty_four_hours_ago
            and float(old.price) > 0
        ):
            current_price = float(latest.price)
            old_price = float(old.price)
            change_percent = (
                (current_price - old_price) / old_price
            ) * 100
            price_changes.append({
                "name": price_type.name,
                "current": current_price,
                "old": old_price,
                "change_percent": change_percent,
                "change_amount": current_price - old_price,
            })

    avg_24h_change = (
        sum(p["change_percent"] for p in price_changes) / len(price_changes)
        if price_changes
        else 0
    )
    biggest_change = (
        max(price_changes, key=lambda x: abs(x["change_percent"]))
        if price_changes
        else None
    )

    special_price_types = SpecialPriceType.objects.prefetch_related(
        Prefetch(
            "special_price_histories",
            queryset=SpecialPriceHistory.objects.order_by("-created_at"),
        )
    ).select_related("source_currency", "target_currency").all()

    latest_update = (
        PriceHistory.objects.select_related("price_type")
        .order_by("-created_at")
        .first()
    )

    return {
        "categories": sort_categories(categories),
        "special_price_types": special_price_types,
        "highest_price": highest_price,
        "highest_price_label": highest_price_label,
        "avg_24h_change": avg_24h_change,
        "biggest_change": biggest_change,
        "total_bots": TelegramBot.objects.count(),
        "active_bots": TelegramBot.objects.filter(is_active=True).count(),
        "total_channels": TelegramChannel.objects.count(),
        "active_channels": TelegramChannel.objects.filter(
            is_active=True
        ).count(),
        "total_price_types": PriceType.objects.count(),
        "total_price_updates": PriceHistory.objects.count(),
        "latest_update_time": (
            latest_update.created_at if latest_update else None
        ),
        "recent_updates": PriceHistory.objects.filter(
            created_at__gte=twenty_four_hours_ago
        ).count(),
    }


def get_dashboard2_context():
    """Build context for dashboard/dashboard2.html (charts and enhanced metrics)."""
    categories = Category.objects.prefetch_related(
        "price_types",
        "price_types__price_histories",
    ).all()
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)

    highest_price_obj = (
        PriceHistory.objects.select_related("price_type")
        .order_by("-price")
        .first()
    )
    highest_price = float(highest_price_obj.price) if highest_price_obj else 0
    highest_price_label = (
        highest_price_obj.price_type.name if highest_price_obj else "N/A"
    )

    price_changes = []
    price_types = PriceType.objects.prefetch_related("price_histories").all()
    for price_type in price_types:
        latest = price_type.price_histories.first()
        if not latest:
            continue
        old = (
            price_type.price_histories.filter(
                created_at__lte=twenty_four_hours_ago
            )
            .order_by("-created_at")
            .first()
        )
        if (
            old
            and latest.created_at > twenty_four_hours_ago
            and float(old.price) > 0
        ):
            current_price = float(latest.price)
            old_price = float(old.price)
            change_percent = (
                (current_price - old_price) / old_price
            ) * 100
            price_changes.append({
                "name": price_type.name,
                "current": current_price,
                "old": old_price,
                "change_percent": change_percent,
                "change_amount": current_price - old_price,
                "category": (
                    price_type.category.name
                    if price_type.category
                    else "Uncategorized"
                ),
            })

    avg_24h_change = (
        sum(p["change_percent"] for p in price_changes) / len(price_changes)
        if price_changes
        else 0
    )
    biggest_change = (
        max(price_changes, key=lambda x: abs(x["change_percent"]))
        if price_changes
        else None
    )

    special_price_types = SpecialPriceType.objects.prefetch_related(
        Prefetch(
            "special_price_histories",
            queryset=SpecialPriceHistory.objects.order_by("-created_at"),
        )
    ).select_related("source_currency", "target_currency").all()

    latest_update = (
        PriceHistory.objects.select_related("price_type")
        .order_by("-created_at")
        .first()
    )
    recent_updates = PriceHistory.objects.filter(
        created_at__gte=twenty_four_hours_ago
    ).count()

    top_price_types = (
        PriceType.objects.annotate(
            latest_price_count=Count("price_histories")
        )
        .filter(price_histories__created_at__gte=twenty_four_hours_ago)
        .distinct()[:10]
    )
    chart_data_24h = []
    for price_type in top_price_types:
        histories = (
            price_type.price_histories.filter(
                created_at__gte=twenty_four_hours_ago
            )
            .order_by("created_at")[:50]
        )
        if histories.count() > 0:
            chart_data_24h.append({
                "label": price_type.name,
                "data": [
                    {"x": h.created_at.isoformat(), "y": float(h.price)}
                    for h in histories
                ],
            })

    category_avg_prices = []
    for category in categories:
        pts = list(category.price_types.all())
        latest_prices = []
        for pt in pts:
            latest = pt.price_histories.first()
            if latest:
                latest_prices.append(float(latest.price))
        if latest_prices:
            category_avg_prices.append({
                "name": category.name,
                "avg_price": sum(latest_prices) / len(latest_prices),
                "count": len(latest_prices),
            })

    recent_updates_list = (
        PriceHistory.objects.select_related(
            "price_type", "price_type__category"
        )
        .order_by("-created_at")[:10]
    )
    recent_updates_data = [
        {
            "price_type": u.price_type.name,
            "category": (
                u.price_type.category.name
                if u.price_type.category
                else "Uncategorized"
            ),
            "price": float(u.price),
            "created_at": u.created_at.isoformat(),
            "time_ago": (
                str(now - u.created_at).split(".")[0]
                if u.created_at
                else ""
            ),
        }
        for u in recent_updates_list
    ]

    all_latest_prices = [
        float(pt.price_histories.first().price)
        for pt in PriceType.objects.prefetch_related("price_histories").all()
        if pt.price_histories.exists()
    ]

    update_frequency = []
    for day in range(7):
        day_start = now - timedelta(days=day + 1)
        day_end = now - timedelta(days=day)
        count = PriceHistory.objects.filter(
            created_at__gte=day_start,
            created_at__lt=day_end,
        ).count()
        update_frequency.append({
            "date": day_start.date().isoformat(),
            "count": count,
        })
    update_frequency.reverse()

    return {
        "categories": sort_categories(categories),
        "special_price_types": special_price_types,
        "highest_price": highest_price,
        "highest_price_label": highest_price_label,
        "avg_24h_change": avg_24h_change,
        "biggest_change": biggest_change,
        "total_bots": TelegramBot.objects.count(),
        "active_bots": TelegramBot.objects.filter(is_active=True).count(),
        "total_channels": TelegramChannel.objects.count(),
        "active_channels": TelegramChannel.objects.filter(
            is_active=True
        ).count(),
        "total_price_types": PriceType.objects.count(),
        "total_price_updates": PriceHistory.objects.count(),
        "latest_update_time": (
            latest_update.created_at if latest_update else None
        ),
        "recent_updates": recent_updates,
        "price_changes": price_changes,
        "chart_data_24h_json": chart_data_24h,
        "category_avg_prices_json": category_avg_prices,
        "recent_updates_json": recent_updates_data,
        "update_frequency_json": update_frequency,
        "price_distribution_json": all_latest_prices,
    }
