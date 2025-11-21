import json
import math
from collections import defaultdict
from datetime import timedelta

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import OuterRef, Subquery, Count
from django.utils import timezone
from django.views.generic import TemplateView

from category.models import PriceType, Category
from change_price.models import PriceHistory
from special_price.models import SpecialPriceType, SpecialPriceHistory
from finalize.models import Finalization, SpecialPriceFinalization
from telegram_app.models import TelegramChannel


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
        week_start = timezone.now() - timedelta(days=7)

        # Regular prices
        price_types = self._get_price_types_with_latest_prices()
        timelines = self._build_timelines(price_types, window_start)
        latest_cards = self._build_latest_cards(price_types)
        price_statistics = self._calculate_price_statistics(price_types, window_start)

        # Special prices
        special_price_types = self._get_special_price_types_with_latest()
        special_timelines = self._build_special_timelines(special_price_types, window_start)
        special_cards = self._build_special_cards(special_price_types)

        # Category and summary data
        category_summary = self._build_category_summary(latest_cards)
        top_movers = self._derive_top_movers(latest_cards)
        
        # Finalization statistics
        finalization_stats = self._get_finalization_statistics(week_start)
        
        # Overall statistics
        overall_stats = self._get_overall_statistics(price_types, special_price_types, week_start)

        context.update(
            {
                "generated_at": timezone.now(),
                "latest_cards": latest_cards,
                "special_cards": special_cards,
                "top_movers": top_movers,
                "price_statistics": price_statistics,
                "finalization_stats": finalization_stats,
                "overall_stats": overall_stats,
                "timeline_data_json": json.dumps(timelines, cls=DjangoJSONEncoder),
                "special_timeline_data_json": json.dumps(special_timelines, cls=DjangoJSONEncoder),
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
    
    def _build_special_timelines(self, special_price_types, window_start):
        """Build timeline data for special prices."""
        relevant_ids = [spt.id for spt in special_price_types if spt.latest_price is not None]

        history_qs = (
            SpecialPriceHistory.objects.filter(
                special_price_type_id__in=relevant_ids, 
                created_at__gte=window_start
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
            timeline_map[history.special_price_type_id].append(
                {
                    "x": history.created_at,
                    "y": float(history.price),
                }
            )

        datasets = []
        for index, special_price_type in enumerate(special_price_types):
            data_points = timeline_map.get(special_price_type.id)
            if not data_points:
                continue

            color = self.palette[(index + 5) % len(self.palette)]  # Different color range
            datasets.append(
                {
                    "label": f"{special_price_type.source_currency.code}/{special_price_type.target_currency.code} {special_price_type.get_trade_type_display()} (Special)",
                    "category": "Special Prices",
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
    
    def _calculate_price_statistics(self, price_types, window_start):
        """Calculate advanced statistics for prices."""
        stats = {}
        
        for price_type in price_types:
            if price_type.latest_price is None:
                continue
            
            histories = PriceHistory.objects.filter(
                price_type=price_type,
                created_at__gte=window_start
            ).order_by('created_at')
            
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
    
    def _get_finalization_statistics(self, week_start):
        """Get statistics about finalizations."""
        total_finalizations = Finalization.objects.count()
        week_finalizations = Finalization.objects.filter(finalized_at__gte=week_start).count()
        
        successful_telegram = Finalization.objects.filter(message_sent=True).count()
        failed_telegram = Finalization.objects.filter(message_sent=False).count()
        
        special_finalizations = SpecialPriceFinalization.objects.count()
        week_special = SpecialPriceFinalization.objects.filter(finalized_at__gte=week_start).count()
        
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
    
    def _get_overall_statistics(self, price_types, special_price_types, week_start):
        """Get overall system statistics."""
        total_price_updates = PriceHistory.objects.count()
        week_price_updates = PriceHistory.objects.filter(created_at__gte=week_start).count()
        
        total_special_updates = SpecialPriceHistory.objects.count()
        week_special_updates = SpecialPriceHistory.objects.filter(created_at__gte=week_start).count()
        
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
