"""
URL configuration for MrExchangePanel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as django_static_serve

from core.pardis_compat import live_prices_json

from . import views

# Set custom 404 handler
handler404 = views.handler404

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', views.favicon_view, name='favicon'),
    path("api/", include("MrExchangePanel.api_urls")),
    # Public Pardis price feed: URL and JSON are a contract with external sites.
    path('prices/live-json/', live_prices_json, name='live_prices_json'),
    path("template-editor/", include("template_editor.frontend_urls", namespace="template_editor_frontend")),
    path("", include("accounts.urls", namespace="accounts")),
    # SPA catch-all last: serve index.html for all other paths (e.g. /settings).
    # Exclude backend paths so they are not served by the SPA.
    re_path(r'^(?!api/|admin/|media/|static/|prices/live-json/).*$', views.SPAView.as_view(), name='spa'),
]

_static_vue = [
    re_path(
        r"^static/(?P<path>.*)$",
        views.serve_static_with_cache,
        {"document_root": settings.STATIC_ROOT},
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Prefer cache-aware static serve over django.conf.urls.static helper.
    urlpatterns += _static_vue
else:
    # Production-like single-container mode (no nginx): serve collected/static
    # and media files directly from Django.
    urlpatterns += _static_vue + [
        re_path(r"^media/(?P<path>.*)$", django_static_serve, {"document_root": settings.MEDIA_ROOT}),
    ]
