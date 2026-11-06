from django.urls import path

from . import api

urlpatterns = [
    path("", api.PriceListAPIView.as_view(), name="api-price-list"),
    path(
        "<int:price_type_id>/",
        api.PriceDetailAPIView.as_view(),
        name="api-price-detail",
    ),
    path(
        "<int:price_type_id>/update/",
        api.PriceUpdateAPIView.as_view(),
        name="api-price-update",
    ),
    path(
        "category/<int:category_id>/bulk-update/",
        api.BulkPriceUpdateAPIView.as_view(),
        name="api-price-bulk-update",
    ),
    path(
        "<int:price_type_id>/history/",
        api.PriceHistoryAPIView.as_view(),
        name="api-price-history",
    ),
]
