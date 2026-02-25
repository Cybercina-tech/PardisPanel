from django.urls import path
from . import views

app_name = "instagram_banner"

urlpatterns = [
    path("", views.generator_page, name="generator"),
    path("preview/<int:category_id>/<str:format_type>/", views.preview_image, name="preview"),
    path("download/<int:category_id>/<str:format_type>/", views.download_image, name="download"),
]
