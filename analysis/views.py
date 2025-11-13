import json
from collections import defaultdict
from datetime import timedelta

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django.views.generic import TemplateView

from category.models import PriceType
from change_price.models import PriceHistory


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

        # Determine the time window for the line charts
        window_start = timezone.now() - timedelta(days=30)

        price_types = self._get_price_types_with_latest_prices()
        timelines = self._build_timelines(price_types, window_start)
        latest_cards = self._build_latest_cards(price_types)

        category_summary = self._build_category_summary(latest_cards)
        top_movers = self._derive_top_movers(latest_cards)

        context.update(
            {
                "generated_at": timezone.now(),
                "latest_cards": latest_cards,
                "top_movers": top_movers,
                "timeline_data_json": json.dumps(timelines, cls=DjangoJSONEncoder),
                "category_summary_json": json.dumps(category_summary, cls=DjangoJSONEncoder),
            }
        )

        return context

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

    def _build_timelines(self, price_types, window_start):
        relevant_ids = [pt.id for pt in price_types if pt.latest_price is not None]

        history_qs = (
            PriceHistory.objects.filter(price_type_id__in=relevant_ids, created_at__gte=window_start)
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
            timeline_map[history.price_type_id].append(
                {
                    "x": history.created_at,
                    "y": float(history.price),
                }
            )

        datasets = []
        for index, price_type in enumerate(price_types):
            data_points = timeline_map.get(price_type.id)
            if not data_points:
                continue

            color = self.palette[index % len(self.palette)]
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
        return candidates[:3]
