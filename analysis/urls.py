from django.urls import path

from .views import AnalyticsDashboardView, PricingDataAPIView

app_name = "analysis"

urlpatterns = [
    # HTML analytics dashboard
    path("", AnalyticsDashboardView.as_view(), name="dashboard"),

    # Read-only JSON API exposing pricing data.
    #
    # Full URL path (including project-level routing):
    #   /analysis/api/pricing/
    #
    # - Returns all categories with their associated pricing items.
    # - Includes a synthetic "Special Prices" category whose items only
    #   appear if their special_price has been updated in the last 6 hours.
    # - Suitable for dashboards, bots, or external integrations needing
    #   a clean JSON representation of current pricing.
    path("api/pricing/", PricingDataAPIView.as_view(), name="pricing-data"),
]

