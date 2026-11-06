from django.urls import path
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register("bots", api_views.TelegramBotViewSet, basename="api-telegram-bots")
router.register(
    "channels/manage",
    api_views.TelegramChannelViewSet,
    basename="api-telegram-channels-manage",
)

urlpatterns = [
    path(
        "channels/",
        api_views.TelegramChannelListAPIView.as_view(),
        name="api-telegram-channels",
    ),
    path(
        "send-message/",
        api_views.SendMessageAPIView.as_view(),
        name="api-telegram-send-message",
    ),
    path(
        "default-settings/",
        api_views.DefaultMessageSettingsListAPIView.as_view(),
        name="api-telegram-default-settings-list",
    ),
    path(
        "default-settings/create/",
        api_views.DefaultMessageSettingsCreateAPIView.as_view(),
        name="api-telegram-default-settings-create",
    ),
    path(
        "default-settings/<int:pk>/",
        api_views.DefaultMessageSettingsDetailAPIView.as_view(),
        name="api-telegram-default-settings-detail",
    ),
] + router.urls
