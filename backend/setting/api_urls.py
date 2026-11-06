from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register(r"support-channels", api_views.SupportChannelViewSet, basename="api-support-channel")
router.register(r"bots", api_views.TelegramBotViewSet, basename="api-setting-bot")
router.register(r"channels", api_views.TelegramChannelViewSet, basename="api-setting-channel")

urlpatterns = [
    path("site/", api_views.SiteSettingsAPIView.as_view(), name="api-settings-site"),
    path("logs/", api_views.LogListAPIView.as_view(), name="api-settings-logs"),
    path("uploads/", api_views.UploadSettingsAPIView.as_view(), name="api-settings-uploads"),
    path("uploads/clear-temp/", api_views.UploadClearTempAPIView.as_view(), name="api-settings-uploads-clear-temp"),
    path("", include(router.urls)),
]
