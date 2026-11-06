"""
DRF API views for price publisher templates (PriceTemplate).
"""
from pathlib import Path

from django.conf import settings
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from accounts.plans import filter_templates_queryset, user_may_use_template
from category.models import Category
from special_price.models import SpecialPriceType

from .models import PriceTemplate
from .serializers import PriceTemplateSerializer


def _assert_plan(request, template):
    if not user_may_use_template(request.user, template, request=request):
        raise PermissionDenied("This template is not included in your plan.")


class PriceTemplateViewSet(ModelViewSet):
    """CRUD for PriceTemplate."""

    permission_classes = [IsAuthenticated]
    serializer_class = PriceTemplateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = PriceTemplate.objects.select_related(
            "category", "special_price_type"
        ).order_by("template_type", "name")
        return filter_templates_queryset(qs, self.request)

    def get_object(self):
        obj = get_object_or_404(
            PriceTemplate.objects.select_related("category", "special_price_type"),
            pk=self.kwargs[self.lookup_field],
        )
        _assert_plan(self.request, obj)
        return obj


class PriceTemplateDashboardAPIView(APIView):
    """
    GET /api/templates/dashboard/ - templates plus categories/special without template,
    and asset catalog for the editor.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        templates = filter_templates_queryset(
            PriceTemplate.objects.select_related(
                "category", "special_price_type"
            ).order_by("template_type", "name"),
            request,
        )

        categories_without_template = (
            Category.objects.order_by("name").filter(price_template__isnull=True)
        )
        special_without_template = (
            SpecialPriceType.objects.order_by("name").filter(price_template__isnull=True)
        )

        static_root = Path(settings.BASE_DIR) / "static"
        image_root = static_root / "img"
        font_root = static_root / "fonts"

        def _collect_assets(subdir: str, patterns: tuple = ("*.png", "*.jpg", "*.jpeg", "*.webp")):
            folder = image_root / subdir
            if not folder.exists():
                return []
            files = []
            for pattern in patterns:
                for file in sorted(folder.glob(pattern)):
                    files.append(f"{subdir}/{file.name}")
            return files

        def _collect_root(patterns: tuple = ("*.png", "*.jpg", "*.jpeg", "*.webp")):
            files = []
            if not image_root.exists():
                return files
            for pattern in patterns:
                for file in sorted(image_root.glob(pattern)):
                    files.append(file.name)
            return files

        asset_catalog = {
            "price_theme": _collect_assets("price_theme"),
            "offer": _collect_assets("offer"),
            "news": _collect_assets("news"),
            "general": _collect_root(),
            "fonts": (
                sorted(
                    (Path("fonts") / font.name).as_posix()
                    for font in font_root.glob("*")
                    if font.is_file()
                )
                if font_root.exists()
                else []
            ),
        }

        return Response({
            "templates": PriceTemplateSerializer(templates, many=True).data,
            "categories_without_template": [
                {"id": c.id, "name": c.name, "slug": c.slug}
                for c in categories_without_template
            ],
            "special_without_template": [
                {"id": s.id, "name": s.name, "slug": s.slug}
                for s in special_without_template
            ],
            "asset_catalog": asset_catalog,
        })
