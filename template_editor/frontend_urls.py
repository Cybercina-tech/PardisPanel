from django.urls import path

from .views import TemplateEditorView

app_name = "template_editor_frontend"

urlpatterns = [
    path("<int:pk>/", TemplateEditorView.as_view(), name="editor"),
]

