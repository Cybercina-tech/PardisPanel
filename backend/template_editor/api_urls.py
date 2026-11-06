from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register(r"templates", api_views.TemplateViewSet, basename="api-template-editor-template")

urlpatterns = [
    path(
        "media/",
        api_views.TemplateEditorMediaUploadAPIView.as_view(),
        name="api-template-editor-media",
    ),
    path(
        "templates/<int:pk>/config/",
        api_views.TemplateConfigUpdateAPIView.as_view(),
        name="api-template-editor-config",
    ),
    path(
        "templates/<int:pk>/preview/",
        api_views.TemplatePreviewAPIView.as_view(),
        name="api-template-editor-preview",
    ),
    path(
        "variables/",
        api_views.TemplateVariablesAPIView.as_view(),
        name="api-template-editor-variables",
    ),
    path(
        "fonts/",
        api_views.TemplateFontsAPIView.as_view(),
        name="api-template-editor-fonts",
    ),
    path(
        "fonts/file/<str:filename>/",
        api_views.TemplateFontFileServeAPIView.as_view(),
        name="api-template-editor-font-file",
    ),
    path(
        "fonts/<str:filename>/",
        api_views.TemplateFontDeleteAPIView.as_view(),
        name="api-template-editor-font-delete",
    ),
    path(
        "price-bindings-preview/",
        api_views.TemplatePriceBindingsPreviewAPIView.as_view(),
        name="api-template-editor-price-bindings-preview",
    ),
    path(
        "category-price-types/",
        api_views.TemplateCategoryPriceTypesAPIView.as_view(),
        name="api-template-editor-category-price-types",
    ),
    path(
        "headless-render/context/",
        api_views.HeadlessRenderContextAPIView.as_view(),
        name="api-template-editor-headless-render-context",
    ),
    path("", include(router.urls)),
]
