from django.urls import path

from .views import ElementViewSet, TemplateViewSet

app_name = "template_editor"

template_list = TemplateViewSet.as_view({"get": "list", "post": "create"})
template_detail = TemplateViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update"}
)
template_render = TemplateViewSet.as_view({"post": "render"})

element_list = ElementViewSet.as_view({"get": "list", "post": "create"})
element_detail = ElementViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)

urlpatterns = [
    path("templates/", template_list, name="template_list"),
    path("templates/<int:pk>/", template_detail, name="template_detail"),
    path("templates/<int:pk>/render/", template_render, name="template_render"),
    path(
        "templates/<int:template_pk>/elements/",
        element_list,
        name="template_element_list",
    ),
    path(
        "templates/<int:template_pk>/elements/<int:pk>/",
        element_detail,
        name="template_element_detail",
    ),
]

