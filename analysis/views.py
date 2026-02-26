import json
from datetime import timedelta, datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from category.models import Category
from .serializers import PricingResponseSerializer
from . import services as analysis_services


class ChartJSONEncoder(DjangoJSONEncoder):
    """Custom JSON encoder that ensures dates are in ISO format for Chart.js"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return timezone.localtime(obj).isoformat()
        return super().default(obj)


class AnalyticsDashboardView(TemplateView):
    template_name = "analysis/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        window_start = timezone.now() - timedelta(days=30)
        week_start = timezone.now() - timedelta(days=7)
        palette = analysis_services.ANALYTICS_PALETTE

        price_types = analysis_services.get_price_types_with_latest_prices()
        timelines = analysis_services.build_timelines(
            price_types, window_start, palette=palette
        )
        latest_cards = analysis_services.build_latest_cards(price_types)
        price_statistics = analysis_services.calculate_price_statistics(
            price_types, window_start
        )

        special_price_types = (
            analysis_services.get_special_price_types_with_latest()
        )
        special_timelines = analysis_services.build_special_timelines(
            special_price_types, window_start, palette=palette
        )
        special_cards = analysis_services.build_special_cards(
            special_price_types
        )

        category_summary = analysis_services.build_category_summary(
            latest_cards
        )
        top_movers = analysis_services.derive_top_movers(latest_cards)
        finalization_stats = analysis_services.get_finalization_statistics(
            week_start
        )
        overall_stats = analysis_services.get_overall_statistics(
            price_types, special_price_types, week_start
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
                "timeline_data_json": json.dumps(
                    timelines, cls=ChartJSONEncoder
                ),
                "special_timeline_data_json": json.dumps(
                    special_timelines, cls=ChartJSONEncoder
                ),
                "category_summary_json": json.dumps(
                    category_summary, cls=ChartJSONEncoder
                ),
            }
        )
        return context


class PricingDataAPIView(APIView):
    """
    Read-only API endpoint that exposes pricing data as JSON.
    All categories are always returned. Special price items are
    filtered to updates in the last 6 hours.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        now = timezone.now()
        cutoff = now - timedelta(hours=6)
        category_items = analysis_services.build_category_items()
        special_items = analysis_services.build_special_price_items(
            cutoff=cutoff
        )

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
