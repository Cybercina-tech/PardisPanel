from django.urls import path

from . import api_views

urlpatterns = [
    path("dashboard/", api_views.FinalizeDashboardAPIView.as_view(), name="api-finalize-dashboard"),
    path("all/", api_views.FinalizeAllAPIView.as_view(), name="api-finalize-all"),
    path("banners/", api_views.FinalizeBannersListAPIView.as_view(), name="api-finalize-banners"),
    path(
        "category/<int:category_id>/banner/",
        api_views.FinalizeCategoryBannerAPIView.as_view(),
        name="api-finalize-category-banner",
    ),
    path(
        "category/<int:category_id>/",
        api_views.FinalizeCategoryAPIView.as_view(),
        name="api-finalize-category",
    ),
    path(
        "special-price/<int:special_price_history_id>/banner/",
        api_views.FinalizeSpecialPriceBannerAPIView.as_view(),
        name="api-finalize-special-price-banner",
    ),
    path(
        "special-price/<int:special_price_history_id>/",
        api_views.FinalizeSpecialPriceAPIView.as_view(),
        name="api-finalize-special-price",
    ),
]
