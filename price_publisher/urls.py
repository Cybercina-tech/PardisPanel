from django.urls import path

from price_publisher import views

app_name = "price_publisher"

urlpatterns = [
    path("templates/", views.template_dashboard, name="template_dashboard"),
    path("templates/add/", views.template_create, name="template_create"),
    path("templates/<int:pk>/edit/", views.template_update, name="template_update"),
    path("templates/<int:pk>/delete/", views.template_delete, name="template_delete"),
    path("templates/<int:pk>/editor/", views.template_editor_redirect, name="template_editor"),
    path("templates/editor/", views.template_editor_index, name="template_editor_index"),
]


