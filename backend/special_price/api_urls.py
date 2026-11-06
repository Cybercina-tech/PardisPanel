from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register(r"", api.SpecialPriceTypeViewSet, basename="specialpricetype")

urlpatterns = [
    path(
        "<int:pk>/update-price/",
        api.SpecialPriceUpdateAPIView.as_view(),
        name="api-special-price-update",
    ),
    path(
        "<int:pk>/history/",
        api.SpecialPriceHistoryAPIView.as_view(),
        name="api-special-price-history",
    ),
    path("", include(router.urls)),
]
