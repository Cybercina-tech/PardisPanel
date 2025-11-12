from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from .models import Template
from .renderer import render_template
from telegram_app.services.dispatcher import broadcast_rendered_template
from .serializers import ElementSerializer, TemplateSerializer


class TemplateViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Template.objects.prefetch_related("elements").all()
    serializer_class = TemplateSerializer

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        template = self.get_object()
        try:
            render_result = render_template(template)
        except FileNotFoundError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        dispatch_report = broadcast_rendered_template(
            template=template,
            image_path=render_result["path"],
            image_url=render_result["url"],
        )

        return Response(
            {
                "rendered_image": render_result["url"],
                "dispatch": dispatch_report,
            },
            status=status.HTTP_200_OK,
        )


class ElementViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ElementSerializer

    def get_template(self) -> Template:
        template_id = self.kwargs.get("template_pk")
        try:
            return Template.objects.get(pk=template_id)
        except Template.DoesNotExist as exc:
            raise NotFound(detail="Template not found.") from exc

    def get_queryset(self):
        template = self.get_template()
        return template.elements.all()

    def perform_create(self, serializer):
        template = self.get_template()
        serializer.save(template=template)


class TemplateEditorView(TemplateView):
    template_name = "template_editor/template_editor.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template_obj = get_object_or_404(Template, pk=self.kwargs["pk"])
        api_url = reverse("template_editor:template_detail", args=[template_obj.pk])
        context.update(
            {
                "template_obj": template_obj,
                "api_url": api_url,
                "background_url": template_obj.background.url
                if template_obj.background
                else "",
            }
        )
        return context

