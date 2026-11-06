from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import api

urlpatterns = [
    path("currencies/", api.CurrencyListAPIView.as_view(), name="api-currencies"),
]

router = DefaultRouter()
router.register(r"", api.CategoryViewSet, basename="category")

price_type_router = DefaultRouter()
price_type_router.register(r"", api.PriceTypeViewSet, basename="pricetype")

urlpatterns += [
    # The category router must come first: its detail patterns use [^/.]+ so they can never
    # swallow "<id>/price-types/…", but the nested price-type router's detail pattern would
    # otherwise capture "<id>/price-types/reorder/" as pk="reorder" and answer 405.
    path("", include(router.urls)),
    path(
        "<int:category_pk>/price-types/",
        include((price_type_router.urls, "price-types")),
    ),
]
