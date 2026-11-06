from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register(r"", api_views.PriceTemplateViewSet, basename="api-price-template")

urlpatterns = [
    path(
        "dashboard/",
        api_views.PriceTemplateDashboardAPIView.as_view(),
        name="api-templates-dashboard",
    ),
    path("", include(router.urls)),
]
