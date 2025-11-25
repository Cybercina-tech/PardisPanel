from django.urls import path

from .views import (
    TemplateListView,
    TemplateCreateView,
    TemplateEditView,
    TemplateDeleteView,
    PreviewView,
)

app_name = "template_editor_frontend"

urlpatterns = [
    path("", TemplateListView.as_view(), name="list"),
    path("create/", TemplateCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", TemplateEditView.as_view(), name="edit"),
    path("<int:pk>/delete/", TemplateDeleteView.as_view(), name="delete"),
    path("<int:pk>/preview/", PreviewView.as_view(), name="preview"),
]

